"""
Founder's BI Command Agent Tools — Executive dashboard and business intelligence.

These tools enable founders/executives to query business metrics via natural language:
  1. Sales reports by period, category, location
  2. Inventory status and alerts
  3. Delivery performance metrics
  4. Customer acquisition and retention
  5. Farmer performance and payouts
  6. Anomaly detection for unusual patterns
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F, Q
from apps.agents.engine.tools import ToolRegistry

logger = logging.getLogger(__name__)

# Create the founder/BI tools registry
founder_tools = ToolRegistry()


@founder_tools.register(
    name="get_sales_report",
    description="Get comprehensive sales report with revenue, orders, and trends. Can filter by period (today, yesterday, this_week, this_month, last_month, this_year), category, or delivery slot.",
    parameters={
        "period": "Time period: today, yesterday, this_week, this_month, last_month, this_year, last_7_days, last_30_days (default: this_month)",
        "category": "Filter by product category name (optional)",
        "delivery_slot": "Filter by slot: EXPRESS, SAME_DAY, NEXT_DAY (optional)",
    },
    requires_user=True,
)
def get_sales_report(
    period: str = "this_month",
    category: str = None,
    delivery_slot: str = None,
    user=None
) -> dict:
    """Get sales report with revenue, order count, and trends."""
    from apps.orders.models import Order, OrderItem
    from apps.inventory.models import Category
    
    # Check if user is admin/founder
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        # Calculate date range
        now = timezone.now()
        date_range = _get_date_range(period, now)
        start_date = date_range['start']
        end_date = date_range['end']
        
        # Base queryset
        orders = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date,
            status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']
        )
        
        # Apply filters
        if delivery_slot:
            orders = orders.filter(delivery_slot=delivery_slot.upper())
        
        if category:
            # Filter orders that have items from this category
            orders = orders.filter(
                items__batch__variant__product__category__name__iexact=category.strip()
            ).distinct()
        
        # Calculate metrics
        total_revenue = orders.aggregate(total=Sum('total'))['total'] or 0
        total_orders = orders.count()
        avg_order_value = orders.aggregate(avg=Avg('total'))['avg'] or 0
        
        # Payment method breakdown
        payment_breakdown = orders.values('payment_method').annotate(
            count=Count('id'),
            revenue=Sum('total')
        ).order_by('-revenue')
        
        # Delivery slot breakdown
        slot_breakdown = orders.values('delivery_slot').annotate(
            count=Count('id'),
            revenue=Sum('total')
        ).order_by('-revenue')
        
        # Daily trend (for charts)
        daily_trend = []
        current = start_date
        while current < end_date:
            day_end = min(current + timedelta(days=1), end_date)
            day_orders = orders.filter(created_at__gte=current, created_at__lt=day_end)
            day_revenue = day_orders.aggregate(total=Sum('total'))['total'] or 0
            daily_trend.append({
                'date': current.strftime('%Y-%m-%d'),
                'revenue': float(day_revenue),
                'orders': day_orders.count(),
            })
            current = day_end
        
        # Compare with previous period
        prev_period_range = _get_previous_period(period, now)
        prev_orders = Order.objects.filter(
            created_at__gte=prev_period_range['start'],
            created_at__lt=prev_period_range['end'],
            status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']
        )
        prev_revenue = prev_orders.aggregate(total=Sum('total'))['total'] or 0
        
        growth_pct = 0
        if prev_revenue > 0:
            growth_pct = ((float(total_revenue) - float(prev_revenue)) / float(prev_revenue)) * 100
        
        return {
            "success": True,
            "period": period,
            "date_range": {
                "from": start_date.strftime('%Y-%m-%d'),
                "to": end_date.strftime('%Y-%m-%d'),
            },
            "summary": {
                "total_revenue": f"₹{float(total_revenue):,.2f}",
                "total_orders": total_orders,
                "average_order_value": f"₹{float(avg_order_value):,.2f}",
                "growth_vs_previous_period": f"{growth_pct:+.1f}%",
            },
            "by_payment_method": [
                {
                    "method": item['payment_method'],
                    "orders": item['count'],
                    "revenue": f"₹{float(item['revenue']):,.2f}" if item['revenue'] else "₹0.00",
                }
                for item in payment_breakdown
            ],
            "by_delivery_slot": [
                {
                    "slot": item['delivery_slot'],
                    "orders": item['count'],
                    "revenue": f"₹{float(item['revenue']):,.2f}" if item['revenue'] else "₹0.00",
                }
                for item in slot_breakdown
            ],
            "daily_trend": daily_trend,
        }
        
    except Exception as e:
        logger.error(f"[FounderAgent] get_sales_report error: {e}")
        return {"success": False, "error": str(e)}


@founder_tools.register(
    name="get_inventory_status",
    description="Get inventory status including low stock alerts, expiring batches, and stock value. Can filter by category or farmer.",
    parameters={
        "alert_type": "Filter by: low_stock, expiring, out_of_stock, pending_approval, all (default: all)",
        "category": "Filter by product category name (optional)",
        "farmer_name": "Filter by farmer name (optional)",
    },
    requires_user=True,
)
def get_inventory_status(
    alert_type: str = "all",
    category: str = None,
    farmer_name: str = None,
    user=None
) -> dict:
    """Get inventory status with alerts for low stock, expiring items, etc."""
    from apps.inventory.models import InventoryBatch, Product, Category
    from apps.accounts.models import FarmerProfile
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        batches = InventoryBatch.objects.select_related(
            'variant', 'variant__product', 'variant__product__category', 'farmer', 'farmer__user'
        )
        
        # Apply filters
        if category:
            batches = batches.filter(variant__product__category__name__iexact=category.strip())
        
        if farmer_name:
            batches = batches.filter(
                Q(farmer__user__first_name__icontains=farmer_name) |
                Q(farmer__user__last_name__icontains=farmer_name) |
                Q(farmer__user__username__icontains=farmer_name) |
                Q(farmer__farm_name__icontains=farmer_name)
            )
        
        # Apply alert filters
        if alert_type == "low_stock":
            batches = batches.filter(stock_level__lte=10, stock_level__gt=0)
        elif alert_type == "out_of_stock":
            batches = batches.filter(stock_level=0)
        elif alert_type == "expiring":
            expiry_threshold = timezone.now() + timedelta(days=3)
            batches = batches.filter(expiry_date__lte=expiry_threshold, expiry_date__gt=timezone.now())
        elif alert_type == "pending_approval":
            batches = batches.filter(is_approved=False)
        
        # Calculate total inventory value
        total_value = sum(
            float(b.purchase_price) * float(b.stock_level)
            for b in batches
        )
        
        # Count by status
        low_stock_count = InventoryBatch.objects.filter(stock_level__lte=10, stock_level__gt=0).count()
        out_of_stock_count = InventoryBatch.objects.filter(stock_level=0).count()
        pending_count = InventoryBatch.objects.filter(is_approved=False).count()
        
        # Expiring soon
        expiry_threshold = timezone.now() + timedelta(days=3)
        expiring_count = InventoryBatch.objects.filter(
            expiry_date__lte=expiry_threshold,
            expiry_date__gt=timezone.now()
        ).count()
        
        # Format results
        batch_list = []
        for b in batches[:50]:  # Limit to 50 items
            status = "✅ OK"
            if b.stock_level == 0:
                status = "❌ Out of Stock"
            elif b.stock_level <= 10:
                status = "⚠️ Low Stock"
            elif not b.is_approved:
                status = "⏳ Pending Approval"
            elif b.expiry_date and b.expiry_date <= expiry_threshold:
                status = "🔴 Expiring Soon"
            
            batch_list.append({
                "batch_id": str(b.id),
                "product": b.variant.product.name,
                "variant": b.variant.unit,
                "stock_level": float(b.stock_level),
                "farmer": b.farmer.user.get_full_name() or b.farmer.user.username,
                "purchase_price": f"₹{b.purchase_price}",
                "status": status,
                "is_approved": b.is_approved,
                "harvest_date": b.harvest_date.strftime('%Y-%m-%d'),
            })
        
        return {
            "success": True,
            "summary": {
                "total_inventory_value": f"₹{total_value:,.2f}",
                "total_batches": InventoryBatch.objects.count(),
                "low_stock_alerts": low_stock_count,
                "out_of_stock": out_of_stock_count,
                "pending_approval": pending_count,
                "expiring_soon": expiring_count,
            },
            "filter_applied": alert_type if alert_type != "all" else None,
            "batches": batch_list,
        }
        
    except Exception as e:
        logger.error(f"[FounderAgent] get_inventory_status error: {e}")
        return {"success": False, "error": str(e)}


@founder_tools.register(
    name="get_delivery_metrics",
    description="Get delivery performance metrics including on-time rate, average delivery time, partner performance, and delivery status breakdown.",
    parameters={
        "period": "Time period: today, yesterday, this_week, this_month, last_7_days (default: this_week)",
        "partner_id": "Filter by specific delivery partner user ID (optional)",
    },
    requires_user=True,
)
def get_delivery_metrics(
    period: str = "this_week",
    partner_id: str = None,
    user=None
) -> dict:
    """Get delivery performance metrics."""
    from apps.delivery_partner.models import DeliveryAssignment, DeliveryPartnerProfile
    from apps.orders.models import Order
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        now = timezone.now()
        date_range = _get_date_range(period, now)
        start_date = date_range['start']
        end_date = date_range['end']
        
        # Base queryset
        assignments = DeliveryAssignment.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date
        )
        
        if partner_id:
            assignments = assignments.filter(partner_id=partner_id)
        
        # Status breakdown
        status_breakdown = assignments.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Calculate on-time delivery rate
        delivered = assignments.filter(status='DELIVERED')
        total_delivered = delivered.count()
        
        # Average delivery time (from accepted to delivered)
        avg_delivery_time = None
        if total_delivered > 0:
            delivery_times = []
            for a in delivered:
                if a.accepted_at and a.delivered_at:
                    delta = a.delivered_at - a.accepted_at
                    delivery_times.append(delta.total_seconds() / 60)  # in minutes
            
            if delivery_times:
                avg_delivery_time = sum(delivery_times) / len(delivery_times)
        
        # Partner performance
        partner_stats = []
        if not partner_id:
            top_partners = assignments.values('partner__id', 'partner__first_name', 'partner__username').annotate(
                total=Count('id'),
                delivered_count=Count('id', filter=Q(status='DELIVERED')),
            ).order_by('-total')[:10]
            
            for p in top_partners:
                if p['partner__id']:
                    success_rate = (p['delivered_count'] / p['total'] * 100) if p['total'] > 0 else 0
                    partner_stats.append({
                        "partner_id": p['partner__id'],
                        "name": p['partner__first_name'] or p['partner__username'],
                        "total_assignments": p['total'],
                        "delivered": p['delivered_count'],
                        "success_rate": f"{success_rate:.1f}%",
                    })
        
        # Online partners now
        online_count = DeliveryPartnerProfile.objects.filter(is_online=True).count()
        total_partners = DeliveryPartnerProfile.objects.count()
        
        return {
            "success": True,
            "period": period,
            "summary": {
                "total_assignments": assignments.count(),
                "delivered": total_delivered,
                "on_time_rate": f"{(total_delivered / assignments.count() * 100):.1f}%" if assignments.count() > 0 else "N/A",
                "avg_delivery_time_minutes": round(avg_delivery_time, 1) if avg_delivery_time else None,
                "partners_online_now": f"{online_count}/{total_partners}",
            },
            "status_breakdown": [
                {"status": item['status'], "count": item['count']}
                for item in status_breakdown
            ],
            "top_performing_partners": partner_stats if partner_stats else None,
        }
        
    except Exception as e:
        logger.error(f"[FounderAgent] get_delivery_metrics error: {e}")
        return {"success": False, "error": str(e)}


@founder_tools.register(
    name="get_customer_metrics",
    description="Get customer acquisition, retention, and engagement metrics including active users, new signups, and repeat purchase rate.",
    parameters={
        "period": "Time period: today, this_week, this_month, last_30_days (default: this_month)",
    },
    requires_user=True,
)
def get_customer_metrics(
    period: str = "this_month",
    user=None
) -> dict:
    """Get customer metrics including acquisition and retention."""
    from apps.accounts.models import User, CustomerPreferences
    from apps.orders.models import Order
    from apps.wallet.models import Partnership
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        now = timezone.now()
        date_range = _get_date_range(period, now)
        start_date = date_range['start']
        end_date = date_range['end']
        
        # New signups
        new_customers = User.objects.filter(
            role='CUSTOMER',
            date_joined__gte=start_date,
            date_joined__lt=end_date
        ).count()
        
        # Total customers
        total_customers = User.objects.filter(role='CUSTOMER').count()
        
        # Active customers (made at least one order in period)
        active_customers = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date
        ).values('user').distinct().count()
        
        # Repeat customers (2+ orders in period)
        repeat_customers = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date
        ).values('user').annotate(
            order_count=Count('id')
        ).filter(order_count__gte=2).count()
        
        # PRIDE partners
        total_partners = Partnership.objects.count()
        new_partners = Partnership.objects.filter(
            start_date__gte=start_date,
            start_date__lt=end_date
        ).count()
        
        # Top customers by order value
        top_customers = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date
        ).values('user__id', 'user__first_name', 'user__username').annotate(
            total_spent=Sum('total'),
            order_count=Count('id')
        ).order_by('-total_spent')[:10]
        
        return {
            "success": True,
            "period": period,
            "acquisition": {
                "new_customers": new_customers,
                "total_customers": total_customers,
                "new_prides_partners": new_partners,
                "total_prides_partners": total_partners,
            },
            "engagement": {
                "active_customers": active_customers,
                "repeat_customers": repeat_customers,
                "repeat_rate": f"{(repeat_customers / active_customers * 100):.1f}%" if active_customers > 0 else "0%",
            },
            "top_customers": [
                {
                    "customer_id": c['user__id'],
                    "name": c['user__first_name'] or c['user__username'],
                    "total_spent": f"₹{float(c['total_spent']):,.2f}",
                    "orders": c['order_count'],
                }
                for c in top_customers
            ],
        }
        
    except Exception as e:
        logger.error(f"[FounderAgent] get_customer_metrics error: {e}")
        return {"success": False, "error": str(e)}


@founder_tools.register(
    name="get_farmer_performance",
    description="Get farmer performance metrics including sales, ratings, payouts, and top performing farmers.",
    parameters={
        "period": "Time period: this_month, last_month, this_year, all_time (default: this_month)",
        "farmer_id": "Filter by specific farmer user ID (optional)",
        "top_n": "Number of top farmers to return (default: 10)",
    },
    requires_user=True,
)
def get_farmer_performance(
    period: str = "this_month",
    farmer_id: str = None,
    top_n: int = 10,
    user=None
) -> dict:
    """Get farmer performance metrics."""
    from apps.accounts.models import FarmerProfile, User
    from apps.orders.models import OrderItem
    from apps.farmer.models import FarmerPayout
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        now = timezone.now()
        
        # Determine date range
        if period == "all_time":
            start_date = datetime(2000, 1, 1, tzinfo=now.tzinfo)
        else:
            date_range = _get_date_range(period, now)
            start_date = date_range['start']
        end_date = now
        
        # Base queryset
        sold_items = OrderItem.objects.filter(
            order__created_at__gte=start_date,
            order__created_at__lt=end_date
        )
        
        if farmer_id:
            sold_items = sold_items.filter(batch__farmer__user_id=farmer_id)
        
        # Aggregate by farmer
        farmer_sales = sold_items.values('batch__farmer').annotate(
            total_revenue=Sum('purchase_price'),
            items_sold=Count('id'),
            total_quantity=Sum('quantity'),
        ).order_by('-total_revenue')[:top_n]
        
        # Get farmer details
        farmer_list = []
        for sale in farmer_sales:
            if sale['batch__farmer']:
                try:
                    farmer = FarmerProfile.objects.select_related('user').get(id=sale['batch__farmer'])
                    
                    # Get payouts for this farmer
                    payouts = FarmerPayout.objects.filter(
                        farmer=farmer,
                        created_at__gte=start_date,
                        created_at__lt=end_date
                    ).aggregate(total=Sum('amount'))['total'] or 0
                    
                    farmer_list.append({
                        "farmer_id": farmer.user.id,
                        "name": farmer.user.get_full_name() or farmer.user.username,
                        "farm_name": farmer.farm_name,
                        "location": farmer.location,
                        "rating": float(farmer.rating),
                        "revenue_generated": f"₹{float(sale['total_revenue']):,.2f}",
                        "items_sold": sale['items_sold'],
                        "total_quantity": float(sale['total_quantity']) if sale['total_quantity'] else 0,
                        "payouts": f"₹{float(payouts):,.2f}",
                        "is_organic": farmer.organic_pledge_accepted,
                    })
                except FarmerProfile.DoesNotExist:
                    continue
        
        # Overall stats
        total_farmers = FarmerProfile.objects.count()
        active_farmers = sold_items.values('batch__farmer').distinct().count()
        total_payouts = FarmerPayout.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return {
            "success": True,
            "period": period,
            "summary": {
                "total_farmers": total_farmers,
                "active_farmers": active_farmers,
                "total_payouts": f"₹{float(total_payouts):,.2f}",
            },
            "top_performers": farmer_list,
        }
        
    except Exception as e:
        logger.error(f"[FounderAgent] get_farmer_performance error: {e}")
        return {"success": False, "error": str(e)}


@founder_tools.register(
    name="detect_anomalies",
    description="Detect unusual patterns in orders, deliveries, or inventory that may require attention.",
    parameters={
        "check_type": "Type of check: orders, deliveries, inventory, all (default: all)",
        "period": "Time period to check: today, this_week (default: today)",
    },
    requires_user=True,
)
def detect_anomalies(
    check_type: str = "all",
    period: str = "today",
    user=None
) -> dict:
    """Detect anomalies in business metrics."""
    from apps.orders.models import Order
    from apps.delivery_partner.models import DeliveryAssignment
    from apps.inventory.models import InventoryBatch
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        now = timezone.now()
        date_range = _get_date_range(period, now)
        start_date = date_range['start']
        end_date = date_range['end']
        
        anomalies = []
        
        # Order anomalies
        if check_type in ["all", "orders"]:
            # Unusually high cancellation rate
            orders = Order.objects.filter(created_at__gte=start_date, created_at__lt=end_date)
            total = orders.count()
            cancelled = orders.filter(status='CANCELLED').count()
            
            if total > 10 and (cancelled / total) > 0.3:
                anomalies.append({
                    "type": "high_cancellation_rate",
                    "severity": "high",
                    "message": f"⚠️ High cancellation rate: {cancelled}/{total} orders ({cancelled/total*100:.1f}%)",
                    "recommendation": "Check for pricing issues or inventory problems",
                })
            
            # Unusually large orders (potential fraud)
            large_orders = orders.filter(total__gt=10000)  # > ₹10,000
            if large_orders.count() > 5:
                anomalies.append({
                    "type": "unusually_large_orders",
                    "severity": "medium",
                    "message": f"📊 {large_orders.count()} orders above ₹10,000 today",
                    "recommendation": "Review for potential fraud or bulk orders",
                })
        
        # Delivery anomalies
        if check_type in ["all", "deliveries"]:
            # Long pending assignments
            long_pending = DeliveryAssignment.objects.filter(
                status='PENDING',
                created_at__lt=now - timedelta(hours=2)
            ).count()
            
            if long_pending > 3:
                anomalies.append({
                    "type": "long_pending_deliveries",
                    "severity": "high",
                    "message": f"🚚 {long_pending} deliveries pending assignment for >2 hours",
                    "recommendation": "Check delivery partner availability",
                })
            
            # Failed deliveries
            failed = DeliveryAssignment.objects.filter(
                status='CANCELLED',
                created_at__gte=start_date,
                created_at__lt=end_date
            ).count()
            
            if failed > 5:
                anomalies.append({
                    "type": "failed_deliveries",
                    "severity": "medium",
                    "message": f"❌ {failed} failed deliveries today",
                    "recommendation": "Review delivery issues and partner performance",
                })
        
        # Inventory anomalies
        if check_type in ["all", "inventory"]:
            # Many out of stock items
            out_of_stock = InventoryBatch.objects.filter(stock_level=0).count()
            if out_of_stock > 20:
                anomalies.append({
                    "type": "high_out_of_stock",
                    "severity": "medium",
                    "message": f"📦 {out_of_stock} products out of stock",
                    "recommendation": "Contact farmers to replenish inventory",
                })
            
            # Pending approvals backlog
            pending = InventoryBatch.objects.filter(is_approved=False).count()
            if pending > 10:
                anomalies.append({
                    "type": "approval_backlog",
                    "severity": "low",
                    "message": f"⏳ {pending} batches pending approval",
                    "recommendation": "Review and approve farmer submissions",
                })
        
        return {
            "success": True,
            "period": period,
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies if anomalies else [{"message": "✅ No anomalies detected. Business running smoothly!"}],
        }
        
    except Exception as e:
        logger.error(f"[FounderAgent] detect_anomalies error: {e}")
        return {"success": False, "error": str(e)}


@founder_tools.register(
    name="get_business_overview",
    description="Get a comprehensive business overview with key metrics across all areas — sales, customers, farmers, deliveries, and inventory.",
    parameters={},
    requires_user=True,
)
def get_business_overview(user=None) -> dict:
    """Get a comprehensive business overview dashboard."""
    from apps.orders.models import Order
    from apps.accounts.models import User
    from apps.inventory.models import InventoryBatch
    from apps.delivery_partner.models import DeliveryPartnerProfile
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Today's sales
        today_orders = Order.objects.filter(created_at__gte=today_start)
        today_revenue = today_orders.aggregate(total=Sum('total'))['total'] or 0
        today_order_count = today_orders.count()
        
        # This month's sales
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_orders = Order.objects.filter(created_at__gte=month_start)
        month_revenue = month_orders.aggregate(total=Sum('total'))['total'] or 0
        
        # Customer stats
        total_customers = User.objects.filter(role='CUSTOMER').count()
        new_customers_today = User.objects.filter(
            role='CUSTOMER',
            date_joined__gte=today_start
        ).count()
        
        # Farmer stats
        total_farmers = User.objects.filter(role='FARMER').count()
        
        # Inventory stats
        total_products = InventoryBatch.objects.count()
        low_stock = InventoryBatch.objects.filter(stock_level__lte=10, stock_level__gt=0).count()
        out_of_stock = InventoryBatch.objects.filter(stock_level=0).count()
        
        # Delivery stats
        online_partners = DeliveryPartnerProfile.objects.filter(is_online=True).count()
        total_partners = DeliveryPartnerProfile.objects.count()
        
        # Pending orders
        pending_orders = Order.objects.filter(
            status__in=['PENDING', 'CONFIRMED', 'PROCESSING']
        ).count()
        
        return {
            "success": True,
            "as_of": now.strftime('%Y-%m-%d %H:%M'),
            "today": {
                "revenue": f"₹{float(today_revenue):,.2f}",
                "orders": today_order_count,
                "new_customers": new_customers_today,
            },
            "this_month": {
                "revenue": f"₹{float(month_revenue):,.2f}",
                "orders": month_orders.count(),
            },
            "platform_health": {
                "total_customers": total_customers,
                "total_farmers": total_farmers,
                "total_products": total_products,
                "delivery_partners_online": f"{online_partners}/{total_partners}",
                "pending_orders": pending_orders,
                "low_stock_alerts": low_stock,
                "out_of_stock": out_of_stock,
            },
            "status": "🟢 Healthy" if pending_orders < 20 and low_stock < 50 else "🟡 Needs Attention",
        }
        
    except Exception as e:
        logger.error(f"[FounderAgent] get_business_overview error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Helper Functions
# =============================================================================

def _get_date_range(period: str, now: datetime) -> dict:
    """Calculate start and end dates for a given period."""
    
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == "yesterday":
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "this_week":
        # Start of week (Monday)
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == "last_7_days":
        start = now - timedelta(days=7)
        end = now
    elif period == "this_month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == "last_month":
        first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day_prev_month = first_day_this_month - timedelta(microseconds=1)
        start = last_day_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = last_day_prev_month
    elif period == "last_30_days":
        start = now - timedelta(days=30)
        end = now
    elif period == "this_year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    else:
        # Default to this month
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    
    return {"start": start, "end": end}


def _get_previous_period(period: str, now: datetime) -> dict:
    """Calculate the previous period for comparison."""
    
    if period == "today":
        prev = now - timedelta(days=1)
        start = prev.replace(hour=0, minute=0, second=0, microsecond=0)
        end = prev.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period in ["this_week", "last_7_days"]:
        start = now - timedelta(days=14)
        end = now - timedelta(days=7)
    elif period in ["this_month", "last_30_days"]:
        first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day_prev_month = first_day_this_month - timedelta(microseconds=1)
        start = last_day_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = last_day_prev_month
    elif period == "this_year":
        start = now.replace(year=now.year-1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(year=now.year-1, month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
    else:
        # Default
        start = now - timedelta(days=30)
        end = now - timedelta(days=60)
    
    return {"start": start, "end": end}
