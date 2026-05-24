"""
Comprehensive BI Agent Tools — Universal Business Intelligence for Owners.

This module provides the BI agent with access to ALL business data:
  1. Sales & Revenue Analytics
  2. Inventory Management
  3. Delivery & Logistics
  4. Customer Insights
  5. Farmer Performance
  6. Financial & Banking
  7. HR & Payroll
  8. Support & Tickets
  9. POS & Retail
  10. Predictive Analytics
  11. Cross-domain Queries

The owner can ask ANY business question and the agent will route to the right tools.
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F, Q, Max, Min
from django.db.models.functions import TruncDate, TruncHour, TruncDay, TruncWeek, TruncMonth
from apps.agents.engine.tools import ToolRegistry

logger = logging.getLogger(__name__)

# Create the comprehensive BI tools registry
bi_tools = ToolRegistry()


# =============================================================================
# SALES & REVENUE TOOLS
# =============================================================================

@bi_tools.register(
    name="query_sales",
    description="Query sales data with flexible filters. Can filter by period, category, product, customer segment, payment method, delivery slot, and more. Returns revenue, order count, and trends.",
    parameters={
        "period": "Time period: today, yesterday, this_week, last_week, this_month, last_month, this_year, last_7_days, last_30_days, last_90_days, custom (default: this_month)",
        "start_date": "Start date for custom period (YYYY-MM-DD)",
        "end_date": "End date for custom period (YYYY-MM-DD)",
        "category": "Filter by product category name (optional)",
        "product_name": "Filter by product name (optional, partial match)",
        "delivery_slot": "Filter by slot: EXPRESS, SAME_DAY, NEXT_DAY (optional)",
        "payment_method": "Filter by payment: WALLET, UPI, CARD, COD (optional)",
        "customer_type": "Filter by: new, returning, pride_partner (optional)",
        "area": "Filter by delivery area/zone (optional)",
        "group_by": "Group results by: day, week, month, category, product, area (default: none)",
    },
    requires_user=True,
)
def query_sales(
    period: str = "this_month",
    start_date: str = None,
    end_date: str = None,
    category: str = None,
    product_name: str = None,
    delivery_slot: str = None,
    payment_method: str = None,
    customer_type: str = None,
    area: str = None,
    group_by: str = None,
    user=None
) -> dict:
    """Comprehensive sales query with flexible filtering and grouping."""
    from apps.orders.models import Order, OrderItem
    from apps.inventory.models import Category
    from apps.accounts.models import User
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        # Determine date range
        now = timezone.now()
        if period == "custom" and start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=now.tzinfo)
            end = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=now.tzinfo)
        else:
            date_range = _get_date_range(period, now)
            start = date_range['start']
            end = date_range['end']
        
        # Base queryset
        orders = Order.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
            status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']
        )
        
        # Apply filters
        if delivery_slot:
            orders = orders.filter(delivery_slot=delivery_slot.upper())
        if payment_method:
            orders = orders.filter(payment_method=payment_method.upper())
        if category:
            orders = orders.filter(items__batch__variant__product__category__name__iexact=category.strip()).distinct()
        if area:
            orders = orders.filter(address_line__icontains=area)
        
        # Customer type filter
        if customer_type == "new":
            # First order in this period
            new_user_ids = User.objects.filter(
                role='CUSTOMER',
                date_joined__gte=start,
                date_joined__lt=end
            ).values_list('id', flat=True)
            orders = orders.filter(user_id__in=new_user_ids)
        elif customer_type == "returning":
            # Users with 2+ orders
            repeat_users = Order.objects.values('user').annotate(
                count=Count('id')
            ).filter(count__gte=2).values_list('user', flat=True)
            orders = orders.filter(user_id__in=repeat_users)
        elif customer_type == "pride_partner":
            from apps.wallet.models import Partnership
            pride_users = Partnership.objects.values_list('user_id', flat=True)
            orders = orders.filter(user_id__in=pride_users)
        
        # Product name filter (on order items)
        if product_name:
            orders = orders.filter(
                items__product_name__icontains=product_name
            ).distinct()
        
        # Calculate metrics
        total_revenue = orders.aggregate(total=Sum('total'))['total'] or 0
        total_orders = orders.count()
        avg_order_value = orders.aggregate(avg=Avg('total'))['avg'] or 0
        
        # Grouping logic
        results = {
            "summary": {
                "total_revenue": f"₹{float(total_revenue):,.2f}",
                "total_orders": total_orders,
                "average_order_value": f"₹{float(avg_order_value):,.2f}",
                "period": period,
                "date_range": {"from": start.strftime('%Y-%m-%d'), "to": end.strftime('%Y-%m-%d')},
            }
        }
        
        if group_by == "day":
            daily = orders.annotate(day=TruncDate('created_at')).values('day').annotate(
                revenue=Sum('total'),
                orders=Count('id')
            ).order_by('day')
            results["trend"] = [
                {"date": d['day'].strftime('%Y-%m-%d'), "revenue": float(d['revenue']), "orders": d['orders']}
                for d in daily
            ]
        elif group_by == "week":
            weekly = orders.annotate(week=TruncWeek('created_at')).values('week').annotate(
                revenue=Sum('total'),
                orders=Count('id')
            ).order_by('week')
            results["trend"] = [
                {"week": w['week'].strftime('%Y-W%U'), "revenue": float(w['revenue']), "orders": w['orders']}
                for w in weekly
            ]
        elif group_by == "category":
            by_category = orders.values(
                'items__batch__variant__product__category__name'
            ).annotate(
                revenue=Sum('total'),
                orders=Count('id', distinct=True)
            ).order_by('-revenue')
            results["breakdown"] = [
                {"category": c['items__batch__variant__product__category__name'] or "Unknown", 
                 "revenue": float(c['revenue']), "orders": c['orders']}
                for c in by_category[:20]
            ]
        elif group_by == "product":
            by_product = orders.values('items__product_name').annotate(
                revenue=Sum(F('items__price') * F('items__quantity')),
                quantity=Sum('items__quantity')
            ).order_by('-revenue')
            results["breakdown"] = [
                {"product": p['items__product_name'], 
                 "revenue": float(p['revenue']), 
                 "quantity": float(p['quantity'])}
                for p in by_product[:20]
            ]
        elif group_by == "area":
            # Extract area from address (simplified)
            by_area = orders.values('address_line').annotate(
                revenue=Sum('total'),
                orders=Count('id')
            ).order_by('-revenue')
            results["breakdown"] = [
                {"area": a['address_line'][:50] + "..." if len(a['address_line']) > 50 else a['address_line'], 
                 "revenue": float(a['revenue']), "orders": a['orders']}
                for a in by_area[:20]
            ]
        
        # Payment method breakdown
        payment_breakdown = orders.values('payment_method').annotate(
            count=Count('id'),
            revenue=Sum('total')
        ).order_by('-revenue')
        results["by_payment_method"] = [
            {"method": p['payment_method'], "orders": p['count'], "revenue": f"₹{float(p['revenue']):,.2f}"}
            for p in payment_breakdown
        ]
        
        # Slot breakdown
        slot_breakdown = orders.values('delivery_slot').annotate(
            count=Count('id'),
            revenue=Sum('total')
        ).order_by('-revenue')
        results["by_delivery_slot"] = [
            {"slot": s['delivery_slot'], "orders": s['count'], "revenue": f"₹{float(s['revenue']):,.2f}"}
            for s in slot_breakdown
        ]
        
        return {"success": True, "data": results}
        
    except Exception as e:
        logger.error(f"[BI Agent] query_sales error: {e}")
        return {"success": False, "error": str(e)}


@bi_tools.register(
    name="compare_periods",
    description="Compare business metrics between two time periods. Useful for analyzing growth, decline, or changes in any metric.",
    parameters={
        "metric": "Metric to compare: revenue, orders, customers, aov (average order value), (default: revenue)",
        "current_period": "Current period: today, this_week, this_month, last_7_days, last_30_days (default: this_month)",
        "previous_period": "Previous period: last_week, last_month, last_year, or auto (default: auto)",
        "category": "Filter by category (optional)",
    },
    requires_user=True,
)
def compare_periods(
    metric: str = "revenue",
    current_period: str = "this_month",
    previous_period: str = "auto",
    category: str = None,
    user=None
) -> dict:
    """Compare metrics between two periods."""
    from apps.orders.models import Order
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        now = timezone.now()
        
        # Determine periods
        current_range = _get_date_range(current_period, now)
        if previous_period == "auto":
            previous_range = _get_previous_period(current_period, now)
        else:
            previous_range = _get_date_range(previous_period, now)
        
        # Base querysets
        current_orders = Order.objects.filter(
            created_at__gte=current_range['start'],
            created_at__lt=current_range['end'],
            status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']
        )
        previous_orders = Order.objects.filter(
            created_at__gte=previous_range['start'],
            created_at__lt=previous_range['end'],
            status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']
        )
        
        if category:
            current_orders = current_orders.filter(
                items__batch__variant__product__category__name__iexact=category.strip()
            ).distinct()
            previous_orders = previous_orders.filter(
                items__batch__variant__product__category__name__iexact=category.strip()
            ).distinct()
        
        # Calculate metrics
        if metric == "revenue":
            current_value = current_orders.aggregate(total=Sum('total'))['total'] or 0
            previous_value = previous_orders.aggregate(total=Sum('total'))['total'] or 0
            unit = "₹"
        elif metric == "orders":
            current_value = current_orders.count()
            previous_value = previous_orders.count()
            unit = ""
        elif metric == "aov":
            current_value = current_orders.aggregate(avg=Avg('total'))['avg'] or 0
            previous_value = previous_orders.aggregate(avg=Avg('total'))['avg'] or 0
            unit = "₹"
        elif metric == "customers":
            current_value = current_orders.values('user').distinct().count()
            previous_value = previous_orders.values('user').distinct().count()
            unit = ""
        else:
            return {"error": f"Unknown metric: {metric}"}
        
        # Calculate change
        if previous_value > 0:
            change_pct = ((float(current_value) - float(previous_value)) / float(previous_value)) * 100
        else:
            change_pct = 100 if current_value > 0 else 0
        
        return {
            "success": True,
            "metric": metric,
            "current_period": {
                "label": current_period,
                "from": current_range['start'].strftime('%Y-%m-%d'),
                "to": current_range['end'].strftime('%Y-%m-%d'),
                "value": f"{unit}{float(current_value):,.2f}" if unit else current_value,
            },
            "previous_period": {
                "label": previous_period if previous_period != "auto" else f"before {current_period}",
                "from": previous_range['start'].strftime('%Y-%m-%d'),
                "to": previous_range['end'].strftime('%Y-%m-%d'),
                "value": f"{unit}{float(previous_value):,.2f}" if unit else previous_value,
            },
            "change": {
                "absolute": f"{unit}{float(current_value - previous_value):,.2f}" if unit else current_value - previous_value,
                "percentage": f"{change_pct:+.1f}%",
                "trend": "up" if change_pct > 0 else "down" if change_pct < 0 else "flat",
            }
        }
        
    except Exception as e:
        logger.error(f"[BI Agent] compare_periods error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# INVENTORY TOOLS
# =============================================================================

@bi_tools.register(
    name="query_inventory",
    description="Query inventory status with advanced filters. Check stock levels, expiring items, low stock alerts, pending approvals, and stock value by category or farmer.",
    parameters={
        "filter": "Filter type: all, low_stock, out_of_stock, expiring, expired, pending_approval, by_farmer, by_category (default: all)",
        "category": "Filter by category name (optional)",
        "farmer_name": "Filter by farmer name (optional)",
        "days_to_expiry": "For expiring filter, days threshold (default: 3)",
        "include_value": "Include inventory value calculation (default: true)",
    },
    requires_user=True,
)
def query_inventory(
    filter: str = "all",
    category: str = None,
    farmer_name: str = None,
    days_to_expiry: int = 3,
    include_value: bool = True,
    user=None
) -> dict:
    """Comprehensive inventory query."""
    from apps.inventory.models import InventoryBatch, Category
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
                Q(farmer__farm_name__icontains=farmer_name)
            )
        
        # Apply status filters
        if filter == "low_stock":
            batches = batches.filter(stock_level__lte=10, stock_level__gt=0)
        elif filter == "out_of_stock":
            batches = batches.filter(stock_level=0)
        elif filter == "expiring":
            expiry_threshold = timezone.now() + timedelta(days=days_to_expiry)
            batches = batches.filter(expiry_date__lte=expiry_threshold, expiry_date__gt=timezone.now())
        elif filter == "expired":
            batches = batches.filter(expiry_date__lte=timezone.now())
        elif filter == "pending_approval":
            batches = batches.filter(is_approved=False)
        
        # Calculate value
        total_value = 0
        if include_value:
            total_value = sum(float(b.purchase_price) * float(b.stock_level) for b in batches)
        
        # Summary stats
        all_batches = InventoryBatch.objects.all()
        summary = {
            "total_batches": all_batches.count(),
            "filtered_batches": batches.count(),
            "low_stock": all_batches.filter(stock_level__lte=10, stock_level__gt=0).count(),
            "out_of_stock": all_batches.filter(stock_level=0).count(),
            "pending_approval": all_batches.filter(is_approved=False).count(),
            "expiring_soon": all_batches.filter(
                expiry_date__lte=timezone.now() + timedelta(days=3),
                expiry_date__gt=timezone.now()
            ).count(),
            "total_value": f"₹{total_value:,.2f}" if include_value else None,
        }
        
        # Detailed results (limited)
        batch_list = []
        for b in batches[:30]:
            status = "✅ OK"
            if b.stock_level == 0:
                status = "❌ Out of Stock"
            elif b.stock_level <= 10:
                status = "⚠️ Low Stock"
            elif not b.is_approved:
                status = "⏳ Pending Approval"
            elif b.expiry_date and b.expiry_date <= timezone.now() + timedelta(days=3):
                status = "🔴 Expiring Soon"
            elif b.expiry_date and b.expiry_date <= timezone.now():
                status = "💀 Expired"
            
            batch_list.append({
                "batch_id": str(b.id),
                "product": b.variant.product.name,
                "variant": b.variant.unit,
                "stock_level": float(b.stock_level),
                "farmer": b.farmer.user.get_full_name() or b.farmer.user.username,
                "category": b.variant.product.category.name if b.variant.product.category else "Uncategorized",
                "purchase_price": f"₹{b.purchase_price}",
                "selling_price": f"₹{b.variant.price}",
                "margin": f"{((float(b.variant.price) - float(b.purchase_price)) / float(b.purchase_price) * 100):.1f}%" if float(b.purchase_price) > 0 else "N/A",
                "status": status,
                "harvest_date": b.harvest_date.strftime('%Y-%m-%d') if b.harvest_date else None,
                "expiry_date": b.expiry_date.strftime('%Y-%m-%d') if b.expiry_date else None,
            })
        
        return {
            "success": True,
            "filter_applied": filter,
            "summary": summary,
            "batches": batch_list,
        }
        
    except Exception as e:
        logger.error(f"[BI Agent] query_inventory error: {e}")
        return {"success": False, "error": str(e)}


@bi_tools.register(
    name="get_demand_forecast",
    description="Get AI-powered demand forecast for products. Shows predicted demand for next 7 days based on historical patterns.",
    parameters={
        "product_id": "Specific product ID (optional)",
        "category": "Filter by category (optional)",
        "top_n": "Number of top products to show (default: 10)",
    },
    requires_user=True,
)
def get_demand_forecast(
    product_id: str = None,
    category: str = None,
    top_n: int = 10,
    user=None
) -> dict:
    """Generate demand forecast based on historical sales patterns."""
    from apps.orders.models import OrderItem
    from apps.inventory.models import InventoryBatch
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        # Get last 30 days sales by product
        last_30_days = timezone.now() - timedelta(days=30)
        
        sales = OrderItem.objects.filter(
            order__created_at__gte=last_30_days
        ).values(
            'batch__variant__product__name',
            'batch__variant__product__category__name'
        ).annotate(
            total_sold=Sum('quantity'),
            avg_daily=Avg('quantity'),
            order_count=Count('order', distinct=True)
        ).order_by('-total_sold')[:top_n]
        
        forecasts = []
        for s in sales:
            avg_daily = float(s['avg_daily']) if s['avg_daily'] else 0
            # Simple forecast: avg daily * 7 with some variance
            forecast_7d = avg_daily * 7
            
            forecasts.append({
                "product": s['batch__variant__product__name'],
                "category": s['batch__variant__product__category__name'] or "Uncategorized",
                "sold_last_30d": float(s['total_sold']),
                "avg_daily_sales": round(avg_daily, 2),
                "forecast_next_7d": round(forecast_7d, 0),
                "confidence": "medium" if s['order_count'] > 10 else "low",
            })
        
        return {
            "success": True,
            "forecast_period": "next_7_days",
            "method": "historical_average",
            "forecasts": forecasts,
        }
        
    except Exception as e:
        logger.error(f"[BI Agent] get_demand_forecast error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# CUSTOMER TOOLS
# =============================================================================

@bi_tools.register(
    name="query_customers",
    description="Query customer data with segmentation, cohort analysis, and behavior metrics. Filter by purchase history, engagement, or demographics.",
    parameters={
        "segment": "Customer segment: all, new, returning, churned, vip, pride_partners (default: all)",
        "period": "Time period for activity: this_month, last_30_days, last_90_days (default: last_30_days)",
        "min_orders": "Minimum number of orders (optional)",
        "min_spent": "Minimum total spent (optional)",
        "top_n": "Number of customers to return (default: 20)",
    },
    requires_user=True,
)
def query_customers(
    segment: str = "all",
    period: str = "last_30_days",
    min_orders: int = None,
    min_spent: float = None,
    top_n: int = 20,
    user=None
) -> dict:
    """Query customer segments and metrics."""
    from apps.accounts.models import User
    from apps.orders.models import Order
    from apps.wallet.models import Partnership
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        now = timezone.now()
        date_range = _get_date_range(period, now)
        
        # Base customer queryset
        customers = User.objects.filter(role='CUSTOMER')
        
        # Segment filtering
        if segment == "new":
            customers = customers.filter(
                date_joined__gte=date_range['start'],
                date_joined__lt=date_range['end']
            )
        elif segment == "returning":
            # Customers with 2+ orders in period
            repeat_users = Order.objects.filter(
                created_at__gte=date_range['start'],
                created_at__lt=date_range['end']
            ).values('user').annotate(count=Count('id')).filter(count__gte=2).values_list('user', flat=True)
            customers = customers.filter(id__in=repeat_users)
        elif segment == "churned":
            # No orders in period but ordered before
            active_in_period = Order.objects.filter(
                created_at__gte=date_range['start'],
                created_at__lt=date_range['end']
            ).values_list('user', flat=True).distinct()
            customers = customers.exclude(id__in=active_in_period)
        elif segment == "pride_partners":
            pride_users = Partnership.objects.values_list('user_id', flat=True)
            customers = customers.filter(id__in=pride_users)
        elif segment == "vip":
            # Top 10% by spend
            customer_spends = Order.objects.filter(
                created_at__gte=date_range['start'],
                created_at__lt=date_range['end']
            ).values('user').annotate(spent=Sum('total')).order_by('-spent')
            top_10_percent = int(len(customer_spends) * 0.1) or 1
            vip_ids = [c['user'] for c in customer_spends[:top_10_percent]]
            customers = customers.filter(id__in=vip_ids)
        
        # Calculate metrics for each customer
        customer_data = []
        for c in customers[:top_n]:
            orders = Order.objects.filter(user=c, created_at__gte=date_range['start'], created_at__lt=date_range['end'])
            total_spent = orders.aggregate(total=Sum('total'))['total'] or 0
            order_count = orders.count()
            
            # Apply min filters
            if min_orders and order_count < min_orders:
                continue
            if min_spent and float(total_spent) < min_spent:
                continue
            
            # Check PRIDE status
            is_pride = Partnership.objects.filter(user=c).exists()
            
            customer_data.append({
                "customer_id": c.id,
                "name": c.get_full_name() or c.username,
                "email": c.email,
                "joined": c.date_joined.strftime('%Y-%m-%d'),
                "orders_in_period": order_count,
                "total_spent": f"₹{float(total_spent):,.2f}",
                "avg_order_value": f"₹{float(total_spent)/order_count:,.2f}" if order_count > 0 else "₹0.00",
                "is_prides_partner": is_pride,
            })
        
        # Summary
        total_customers = User.objects.filter(role='CUSTOMER').count()
        new_this_month = User.objects.filter(
            role='CUSTOMER',
            date_joined__gte=now.replace(day=1, hour=0, minute=0, second=0)
        ).count()
        
        return {
            "success": True,
            "segment": segment,
            "period": period,
            "summary": {
                "total_customers": total_customers,
                "new_this_month": new_this_month,
                "matching_segment": len(customer_data),
            },
            "customers": customer_data,
        }
        
    except Exception as e:
        logger.error(f"[BI Agent] query_customers error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# DELIVERY TOOLS
# =============================================================================

@bi_tools.register(
    name="query_deliveries",
    description="Query delivery performance metrics. Check on-time rates, partner performance, delivery times by area, and assignment status.",
    parameters={
        "period": "Time period: today, yesterday, this_week, this_month (default: today)",
        "status": "Filter by status: PENDING, ACCEPTED, PICKED_UP, DELIVERED, CANCELLED (optional)",
        "partner_id": "Filter by specific partner ID (optional)",
        "area": "Filter by delivery area (optional)",
        "metric": "Specific metric: all, on_time_rate, avg_delivery_time, partner_performance (default: all)",
    },
    requires_user=True,
)
def query_deliveries(
    period: str = "today",
    status: str = None,
    partner_id: str = None,
    area: str = None,
    metric: str = "all",
    user=None
) -> dict:
    """Query delivery metrics and performance."""
    from apps.delivery_partner.models import DeliveryAssignment, DeliveryPartnerProfile
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        now = timezone.now()
        date_range = _get_date_range(period, now)
        
        assignments = DeliveryAssignment.objects.filter(
            created_at__gte=date_range['start'],
            created_at__lt=date_range['end']
        )
        
        if status:
            assignments = assignments.filter(status=status.upper())
        if partner_id:
            assignments = assignments.filter(partner_id=partner_id)
        
        # Calculate metrics
        total = assignments.count()
        delivered = assignments.filter(status='DELIVERED')
        delivered_count = delivered.count()
        
        # On-time calculation
        on_time_count = 0
        for d in delivered:
            if d.delivered_at and d.estimated_delivery_time:
                if d.delivered_at <= d.estimated_delivery_time:
                    on_time_count += 1
        
        on_time_rate = (on_time_count / delivered_count * 100) if delivered_count > 0 else 0
        
        # Average delivery time
        delivery_times = []
        for d in delivered:
            if d.accepted_at and d.delivered_at:
                delta = (d.delivered_at - d.accepted_at).total_seconds() / 60
                delivery_times.append(delta)
        avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
        
        # Partner performance
        partner_stats = []
        if metric in ["all", "partner_performance"]:
            partner_data = assignments.values('partner__id', 'partner__first_name', 'partner__username').annotate(
                total=Count('id'),
                delivered_count=Count('id', filter=Q(status='DELIVERED')),
                avg_time=Avg('delivered_at', filter=Q(status='DELIVERED'))  # Simplified
            ).order_by('-total')[:10]
            
            for p in partner_data:
                if p['partner__id']:
                    success_rate = (p['delivered_count'] / p['total'] * 100) if p['total'] > 0 else 0
                    partner_stats.append({
                        "partner_id": p['partner__id'],
                        "name": p['partner__first_name'] or p['partner__username'],
                        "assignments": p['total'],
                        "delivered": p['delivered_count'],
                        "success_rate": f"{success_rate:.1f}%",
                    })
        
        # Status breakdown
        status_breakdown = assignments.values('status').annotate(count=Count('id')).order_by('-count')
        
        # Online partners
        online_now = DeliveryPartnerProfile.objects.filter(is_online=True).count()
        total_partners = DeliveryPartnerProfile.objects.count()
        
        return {
            "success": True,
            "period": period,
            "summary": {
                "total_assignments": total,
                "delivered": delivered_count,
                "on_time_rate": f"{on_time_rate:.1f}%",
                "avg_delivery_time_minutes": round(avg_delivery_time, 1),
                "partners_online": f"{online_now}/{total_partners}",
            },
            "status_breakdown": [
                {"status": s['status'], "count": s['count']} for s in status_breakdown
            ],
            "partner_performance": partner_stats if partner_stats else None,
        }
        
    except Exception as e:
        logger.error(f"[BI Agent] query_deliveries error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# FARMER TOOLS
# =============================================================================

@bi_tools.register(
    name="query_farmers",
    description="Query farmer performance, payouts, inventory contributions, and ratings. Filter by performance tier, location, or product category.",
    parameters={
        "period": "Time period: this_month, last_month, this_year, all_time (default: this_month)",
        "filter_by": "Filter: all, top_performers, low_performers, unpaid, by_location (default: all)",
        "location": "Filter by location/region (optional)",
        "category": "Filter by product category they supply (optional)",
        "top_n": "Number of farmers to return (default: 15)",
    },
    requires_user=True,
)
def query_farmers(
    period: str = "this_month",
    filter_by: str = "all",
    location: str = None,
    category: str = None,
    top_n: int = 15,
    user=None
) -> dict:
    """Query farmer performance and metrics."""
    from apps.accounts.models import FarmerProfile
    from apps.orders.models import OrderItem
    from apps.farmer.models import FarmerPayout
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        now = timezone.now()
        if period == "all_time":
            start_date = datetime(2000, 1, 1, tzinfo=now.tzinfo)
        else:
            date_range = _get_date_range(period, now)
            start_date = date_range['start']
        end_date = now
        
        # Get farmer sales data
        sales = OrderItem.objects.filter(
            order__created_at__gte=start_date,
            order__created_at__lt=end_date
        )
        
        if category:
            sales = sales.filter(batch__variant__product__category__name__iexact=category.strip())
        
        farmer_sales = sales.values('batch__farmer').annotate(
            revenue=Sum('purchase_price'),
            items_sold=Count('id'),
            quantity=Sum('quantity')
        )
        
        if filter_by == "top_performers":
            farmer_sales = farmer_sales.order_by('-revenue')[:top_n]
        elif filter_by == "low_performers":
            farmer_sales = farmer_sales.order_by('revenue')[:top_n]
        
        # Build farmer list
        farmers = []
        for fs in farmer_sales:
            if fs['batch__farmer']:
                try:
                    farmer = FarmerProfile.objects.select_related('user').get(id=fs['batch__farmer'])
                    
                    # Location filter
                    if location and location.lower() not in farmer.location.lower():
                        continue
                    
                    # Get payouts
                    payouts = FarmerPayout.objects.filter(
                        farmer=farmer,
                        created_at__gte=start_date,
                        created_at__lt=end_date
                    ).aggregate(total=Sum('amount'))['total'] or 0
                    
                    farmers.append({
                        "farmer_id": farmer.user.id,
                        "name": farmer.user.get_full_name() or farmer.user.username,
                        "farm_name": farmer.farm_name,
                        "location": farmer.location,
                        "rating": float(farmer.rating),
                        "revenue_generated": f"₹{float(fs['revenue']):,.2f}",
                        "items_sold": fs['items_sold'],
                        "total_quantity": float(fs['quantity']) if fs['quantity'] else 0,
                        "payouts": f"₹{float(payouts):,.2f}",
                        "is_organic": farmer.organic_pledge_accepted,
                    })
                except FarmerProfile.DoesNotExist:
                    continue
        
        # Summary
        total_farmers = FarmerProfile.objects.count()
        active_farmers = len(farmer_sales)
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
            "farmers": farmers,
        }
        
    except Exception as e:
        logger.error(f"[BI Agent] query_farmers error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# FINANCIAL TOOLS
# =============================================================================

@bi_tools.register(
    name="query_finance",
    description="Query financial metrics including revenue, costs, profit margins, payment method breakdown, and receivables.",
    parameters={
        "period": "Time period: today, this_week, this_month, last_month, this_year (default: this_month)",
        "metric": "Metric type: revenue, costs, profit, payment_breakdown, receivables (default: revenue)",
        "group_by": "Group by: day, week, category, payment_method (optional)",
    },
    requires_user=True,
)
def query_finance(
    period: str = "this_month",
    metric: str = "revenue",
    group_by: str = None,
    user=None
) -> dict:
    """Query financial metrics and breakdowns."""
    from apps.orders.models import Order
    from apps.pos.models import PosTransaction
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        now = timezone.now()
        date_range = _get_date_range(period, now)
        
        # Online orders
        online_orders = Order.objects.filter(
            created_at__gte=date_range['start'],
            created_at__lt=date_range['end'],
            status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']
        )
        
        # POS transactions
        pos_transactions = PosTransaction.objects.filter(
            created_at__gte=date_range['start'],
            created_at__lt=date_range['end'],
            transaction_type='SALE'
        )
        
        online_revenue = online_orders.aggregate(total=Sum('total'))['total'] or 0
        pos_revenue = pos_transactions.aggregate(total=Sum('total'))['total'] or 0
        total_revenue = online_revenue + pos_revenue
        
        results = {
            "period": period,
            "date_range": {
                "from": date_range['start'].strftime('%Y-%m-%d'),
                "to": date_range['end'].strftime('%Y-%m-%d'),
            },
            "summary": {
                "total_revenue": f"₹{float(total_revenue):,.2f}",
                "online_revenue": f"₹{float(online_revenue):,.2f}",
                "pos_revenue": f"₹{float(pos_revenue):,.2f}",
                "online_orders": online_orders.count(),
                "pos_transactions": pos_transactions.count(),
            }
        }
        
        # Payment method breakdown
        if metric == "payment_breakdown" or metric == "all":
            online_payment = online_orders.values('payment_method').annotate(
                count=Count('id'),
                revenue=Sum('total')
            ).order_by('-revenue')
            
            results["payment_breakdown"] = {
                "online": [
                    {"method": p['payment_method'], "orders": p['count'], "revenue": f"₹{float(p['revenue']):,.2f}"}
                    for p in online_payment
                ],
                "pos_methods": list(pos_transactions.values('method').annotate(
                    count=Count('id'),
                    revenue=Sum('total')
                ).order_by('-revenue').values('method', 'count', 'revenue')[:10])
            }
        
        return {"success": True, "data": results}
        
    except Exception as e:
        logger.error(f"[BI Agent] query_finance error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# HR & PAYROLL TOOLS
# =============================================================================

@bi_tools.register(
    name="query_hr",
    description="Query HR metrics including employee count, attendance, payroll summary, and department breakdown.",
    parameters={
        "metric": "Metric type: headcount, attendance, payroll_summary, departments (default: headcount)",
        "period": "Time period for attendance/payroll: this_month, last_month (default: this_month)",
    },
    requires_user=True,
)
def query_hr(
    metric: str = "headcount",
    period: str = "this_month",
    user=None
) -> dict:
    """Query HR and payroll metrics."""
    from apps.accounts.models import User
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        # Since we don't have a full Employee model, use role-based counts
        role_counts = User.objects.values('role').annotate(count=Count('id')).order_by('-count')
        
        results = {
            "headcount_by_role": [
                {"role": r['role'], "count": r['count']}
                for r in role_counts
            ],
            "total_users": User.objects.count(),
        }
        
        # Active users by date joined
        recent_hires = User.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=30)
        ).count()
        results["recent_hires_last_30d"] = recent_hires
        
        return {
            "success": True,
            "metric": metric,
            "data": results,
        }
        
    except Exception as e:
        logger.error(f"[BI Agent] query_hr error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# SUPPORT TOOLS
# =============================================================================

@bi_tools.register(
    name="query_support",
    description="Query support ticket metrics including volume, resolution times, sentiment analysis, and agent performance.",
    parameters={
        "period": "Time period: today, this_week, this_month (default: this_week)",
        "metric": "Metric: volume, resolution_time, sentiment, category_breakdown (default: volume)",
        "status": "Filter by status: open, resolved, escalated (optional)",
    },
    requires_user=True,
)
def query_support(
    period: str = "this_week",
    metric: str = "volume",
    status: str = None,
    user=None
) -> dict:
    """Query support metrics."""
    # Note: This uses mock data since we don't have a full ticket model
    # In production, this would query a SupportTicket model
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        # Mock support data - would be replaced with actual model queries
        mock_data = {
            "volume": {
                "total_tickets": 45,
                "open": 12,
                "resolved": 30,
                "escalated": 3,
                "avg_resolution_time_hours": 4.5,
            },
            "category_breakdown": [
                {"category": "Late Delivery", "count": 18},
                {"category": "Damaged Product", "count": 12},
                {"category": "Payment Issue", "count": 8},
                {"category": "App Issue", "count": 7},
            ],
            "sentiment": {
                "angry": 5,
                "frustrated": 15,
                "neutral": 20,
                "happy": 5,
            }
        }
        
        return {
            "success": True,
            "period": period,
            "metric": metric,
            "data": mock_data.get(metric, mock_data),
            "note": "Using sample data - integrate with SupportTicket model for production",
        }
        
    except Exception as e:
        logger.error(f"[BI Agent] query_support error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# ANOMALY DETECTION TOOLS
# =============================================================================

@bi_tools.register(
    name="detect_business_anomalies",
    description="Advanced anomaly detection across all business areas. Detects unusual patterns in sales, inventory, deliveries, and customer behavior that may need attention.",
    parameters={
        "check_types": "Comma-separated list: sales, inventory, delivery, customers, finance, all (default: all)",
        "period": "Time period: today, yesterday, this_week (default: today)",
        "sensitivity": "Sensitivity level: low, medium, high (default: medium)",
    },
    requires_user=True,
)
def detect_business_anomalies(
    check_types: str = "all",
    period: str = "today",
    sensitivity: str = "medium",
    user=None
) -> dict:
    """Comprehensive anomaly detection across all business areas."""
    from apps.orders.models import Order
    from apps.inventory.models import InventoryBatch
    from apps.delivery_partner.models import DeliveryAssignment
    from apps.accounts.models import User
    
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        now = timezone.now()
        date_range = _get_date_range(period, now)
        start_date = date_range['start']
        end_date = date_range['end']
        
        types_to_check = check_types.split(",") if check_types != "all" else ["sales", "inventory", "delivery", "customers"]
        
        anomalies = []
        
        # Sales anomalies
        if "sales" in types_to_check:
            orders = Order.objects.filter(created_at__gte=start_date, created_at__lt=end_date)
            total = orders.count()
            cancelled = orders.filter(status='CANCELLED').count()
            
            # High cancellation rate
            if total > 5:
                cancel_rate = cancelled / total
                threshold = 0.2 if sensitivity == "low" else 0.15 if sensitivity == "medium" else 0.1
                if cancel_rate > threshold:
                    anomalies.append({
                        "area": "sales",
                        "severity": "high" if cancel_rate > 0.3 else "medium",
                        "type": "high_cancellation_rate",
                        "message": f"⚠️ High cancellation rate: {cancelled}/{total} orders ({cancel_rate*100:.1f}%)",
                        "recommendation": "Check for pricing issues, inventory problems, or delivery delays",
                    })
            
            # Unusually large orders (potential fraud)
            large_orders = orders.filter(total__gt=10000).count()
            if large_orders > 3:
                anomalies.append({
                    "area": "sales",
                    "severity": "medium",
                    "type": "unusually_large_orders",
                    "message": f"📊 {large_orders} orders above ₹10,000 in {period}",
                    "recommendation": "Review for potential fraud or verify bulk order legitimacy",
                })
            
            # Sudden drop in orders
            prev_range = _get_previous_period(period, now)
            prev_orders = Order.objects.filter(
                created_at__gte=prev_range['start'],
                created_at__lt=prev_range['end']
            ).count()
            if prev_orders > 10 and total < prev_orders * 0.5:
                anomalies.append({
                    "area": "sales",
                    "severity": "high",
                    "type": "sudden_order_drop",
                    "message": f"📉 Order volume dropped {((prev_orders-total)/prev_orders*100):.0f}% vs previous period",
                    "recommendation": "Investigate marketing, inventory, or technical issues",
                })
        
        # Inventory anomalies
        if "inventory" in types_to_check:
            out_of_stock = InventoryBatch.objects.filter(stock_level=0).count()
            low_stock = InventoryBatch.objects.filter(stock_level__lte=10, stock_level__gt=0).count()
            
            threshold = 30 if sensitivity == "low" else 20 if sensitivity == "medium" else 10
            if out_of_stock > threshold:
                anomalies.append({
                    "area": "inventory",
                    "severity": "high" if out_of_stock > 50 else "medium",
                    "type": "high_out_of_stock",
                    "message": f"📦 {out_of_stock} products out of stock",
                    "recommendation": "Contact farmers urgently to replenish inventory",
                })
            
            if low_stock > threshold * 2:
                anomalies.append({
                    "area": "inventory",
                    "severity": "medium",
                    "type": "high_low_stock",
                    "message": f"⚠️ {low_stock} products with low stock (≤10 units)",
                    "recommendation": "Plan restocking to avoid stockouts",
                })
            
            # Pending approvals backlog
            pending = InventoryBatch.objects.filter(is_approved=False).count()
            if pending > 15:
                anomalies.append({
                    "area": "inventory",
                    "severity": "low",
                    "type": "approval_backlog",
                    "message": f"⏳ {pending} batches pending approval",
                    "recommendation": "Review and approve farmer submissions",
                })
        
        # Delivery anomalies
        if "delivery" in types_to_check:
            long_pending = DeliveryAssignment.objects.filter(
                status='PENDING',
                created_at__lt=now - timedelta(hours=2)
            ).count()
            
            threshold = 5 if sensitivity == "low" else 3 if sensitivity == "medium" else 2
            if long_pending > threshold:
                anomalies.append({
                    "area": "delivery",
                    "severity": "high",
                    "type": "long_pending_deliveries",
                    "message": f"🚚 {long_pending} deliveries pending assignment for >2 hours",
                    "recommendation": "Check delivery partner availability and capacity",
                })
            
            failed = DeliveryAssignment.objects.filter(
                status='CANCELLED',
                created_at__gte=start_date,
                created_at__lt=end_date
            ).count()
            
            if failed > 5:
                anomalies.append({
                    "area": "delivery",
                    "severity": "medium",
                    "type": "failed_deliveries",
                    "message": f"❌ {failed} failed deliveries in {period}",
                    "recommendation": "Review delivery issues and partner performance",
                })
        
        # Customer anomalies
        if "customers" in types_to_check:
            # Sudden drop in new signups
            new_customers = User.objects.filter(
                role='CUSTOMER',
                date_joined__gte=start_date,
                date_joined__lt=end_date
            ).count()
            
            prev_range = _get_previous_period(period, now)
            prev_new = User.objects.filter(
                role='CUSTOMER',
                date_joined__gte=prev_range['start'],
                date_joined__lt=prev_range['end']
            ).count()
            
            if prev_new > 5 and new_customers < prev_new * 0.5:
                anomalies.append({
                    "area": "customers",
                    "severity": "medium",
                    "type": "drop_in_new_signups",
                    "message": f"👤 New customer signups dropped {((prev_new-new_customers)/prev_new*100):.0f}% vs previous period",
                    "recommendation": "Review marketing campaigns and onboarding flow",
                })
        
        return {
            "success": True,
            "period": period,
            "sensitivity": sensitivity,
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies if anomalies else [{"message": "✅ No anomalies detected. Business running smoothly!"}],
            "summary_by_area": {
                "sales": len([a for a in anomalies if a.get("area") == "sales"]),
                "inventory": len([a for a in anomalies if a.get("area") == "inventory"]),
                "delivery": len([a for a in anomalies if a.get("area") == "delivery"]),
                "customers": len([a for a in anomalies if a.get("area") == "customers"]),
            }
        }
        
    except Exception as e:
        logger.error(f"[BI Agent] detect_business_anomalies error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# UNIVERSAL QUERY TOOL
# =============================================================================

@bi_tools.register(
    name="ask_business_question",
    description="Universal business question answering. Use this for complex queries that may span multiple business areas. The agent will determine which data sources to query and synthesize a comprehensive answer.",
    parameters={
        "question": "The natural language business question to answer",
        "context": "Additional context or constraints (optional)",
    },
    requires_user=True,
)
def ask_business_question(
    question: str,
    context: str = None,
    user=None
) -> dict:
    """Universal business question answering with cross-domain analysis."""
    if not user or user.role != 'ADMIN':
        return {"error": "Unauthorized. Admin access required."}
    
    try:
        # This tool serves as a router for complex questions
        # The actual routing logic is in the LLM, but we provide metadata
        # about what data sources might be relevant
        
        # Keywords to suggest relevant tools
        keywords = {
            "sales": ["revenue", "orders", "sold", "gmv", "turnover", "income"],
            "inventory": ["stock", "inventory", "products", "batches", "expiring"],
            "customers": ["customers", "users", "buyers", "shoppers", "retention"],
            "delivery": ["delivery", "shipping", "logistics", "courier", "partner"],
            "farmers": ["farmers", "vendors", "suppliers", "producers"],
            "finance": ["profit", "margin", "cost", "expense", "payment"],
            "hr": ["employees", "staff", "payroll", "attendance"],
            "support": ["tickets", "complaints", "issues", "support"],
        }
        
        question_lower = question.lower()
        suggested_areas = []
        
        for area, words in keywords.items():
            if any(word in question_lower for word in words):
                suggested_areas.append(area)
        
        return {
            "success": True,
            "question": question,
            "suggested_data_sources": suggested_areas if suggested_areas else ["all"],
            "available_tools": [
                "query_sales", "query_inventory", "query_customers",
                "query_deliveries", "query_farmers", "query_finance",
                "query_hr", "query_support", "compare_periods",
                "detect_business_anomalies", "get_demand_forecast"
            ],
            "message": "Use the suggested tools to gather data for this question.",
        }
        
    except Exception as e:
        logger.error(f"[BI Agent] ask_business_question error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# HELPER FUNCTIONS
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
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == "last_week":
        last_week_start = (now - timedelta(days=now.weekday() + 7)).replace(hour=0, minute=0, second=0, microsecond=0)
        start = last_week_start
        end = last_week_start + timedelta(days=7)
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
    elif period == "last_90_days":
        start = now - timedelta(days=90)
        end = now
    elif period == "this_year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    else:
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
        start = now - timedelta(days=30)
        end = now - timedelta(days=60)
    
    return {"start": start, "end": end}
