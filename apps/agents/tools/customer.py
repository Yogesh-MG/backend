"""
Customer Agent Tools — Real Django ORM queries for customer support.

These are the production versions of the fake tools from Lesson 2.
Each tool queries actual database models and returns structured data
the agent can use to answer customer questions.
"""

import logging
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from apps.agents.engine.tools import ToolRegistry

logger = logging.getLogger(__name__)

# Create the customer tools registry
customer_tools = ToolRegistry()


@customer_tools.register(
    name="get_order_status",
    description="Look up the status and details of an order by its tracking ID (e.g., FRSH-A1B2C3)",
    parameters={"tracking_id": "The order tracking ID (string, e.g., 'FRSH-A1B2C3')"},
    requires_user=True,
)
def get_order_status(tracking_id: str, user=None) -> dict:
    """Look up order status by tracking ID, scoped to the current user."""
    from apps.orders.models import Order
    
    logger.info(f"[TOOL get_order_status] Called with tracking_id={tracking_id}, user={user}, type={type(user)}")
    
    try:
        # Only allow users to see their own orders
        filters = {"tracking_id": tracking_id.upper().strip()}
        if user:
            filters["user"] = user
            logger.info(f"[TOOL get_order_status] Filtering by user_id={user.id}")
        
        logger.info(f"[TOOL get_order_status] Querying with filters: {filters}")
        order = Order.objects.select_related("user").prefetch_related("items").get(**filters)
        
        logger.info(f"[TOOL get_order_status] Found order: {order.tracking_id}, user={order.user}")
        
        items = [
            {
                "product": item.product_name,
                "quantity": item.quantity,
                "unit": item.unit,
                "price": str(item.price),
            }
            for item in order.items.all()
        ]
        
        result = {
            "found": True,
            "tracking_id": order.tracking_id,
            "status": order.get_status_display(),
            "status_code": order.status,
            "items": items,
            "subtotal": str(order.subtotal),
            "delivery_fee": str(order.delivery_fee),
            "total": str(order.total),
            "delivery_slot": order.get_delivery_slot_display(),
            "payment_method": order.get_payment_method_display(),
            "is_paid": order.is_paid,
            "placed_at": order.created_at.strftime("%b %d, %Y at %I:%M %p"),
        }
        
        logger.info(f"[TOOL get_order_status] Returning result: {result}")
        return result
        
    except Order.DoesNotExist:
        logger.warning(f"[TOOL get_order_status] Order not found: {tracking_id}")
        return {"found": False, "error": f"No order found with tracking ID '{tracking_id}'"}
    except Exception as e:
        logger.error(f"[TOOL get_order_status] Exception: {e}")
        import traceback
        logger.error(f"[TOOL get_order_status] Traceback: {traceback.format_exc()}")
        return {"found": False, "error": str(e)}


@customer_tools.register(
    name="get_my_recent_orders",
    description="Get the customer's recent orders (last 5 orders with status and totals)",
    parameters={},
    requires_user=True,
)
def get_my_recent_orders(user=None) -> list:
    """Get the current user's recent orders."""
    from apps.orders.models import Order
    
    logger.info(f"[TOOL get_my_recent_orders] Called with user={user}, type={type(user)}")
    
    if not user:
        logger.warning("[TOOL get_my_recent_orders] No user provided!")
        return [{"error": "User not authenticated"}]
    
    logger.info(f"[TOOL get_my_recent_orders] User id={user.id}, username={user.username}")
    
    orders = Order.objects.filter(user=user).order_by("-created_at")[:5]
    logger.info(f"[TOOL get_my_recent_orders] Found {orders.count()} orders")
    
    if not orders:
        return [{"message": "You don't have any orders yet. Start shopping! 🛒"}]
    
    result = [
        {
            "tracking_id": o.tracking_id,
            "status": o.get_status_display(),
            "total": str(o.total),
            "items_count": o.items.count(),
            "placed_at": o.created_at.strftime("%b %d, %I:%M %p"),
        }
        for o in orders
    ]
    
    logger.info(f"[TOOL get_my_recent_orders] Returning result: {result}")
    return result


@customer_tools.register(
    name="search_products",
    description="Search for products by name or keyword. Returns matching products with prices and availability.",
    parameters={"query": "Search term (string, e.g., 'tomato', 'spinach', 'organic rice')"},
)
def search_products(query: str) -> list:
    """Search products by name, returning variants with prices."""
    from apps.inventory.models import Product, ProductVariant
    
    products = Product.objects.filter(
        name__icontains=query.strip()
    ).prefetch_related("variants", "variants__batches")[:10]
    
    if not products:
        return [{"message": f"No products found matching '{query}'. Try a different search term."}]
    
    results = []
    for product in products:
        variants = []
        for v in product.variants.filter(is_active=True):
            stock = sum(b.stock_level for b in v.batches.all())
            variants.append({
                "unit": v.unit,
                "price": str(v.price),
                "mrp": str(v.mrp) if v.mrp else None,
                "in_stock": stock > 0,
                "stock_qty": float(stock),
            })
        
        results.append({
            "name": product.name,
            "category": product.category.name if product.category else None,
            "description": product.description[:100],
            "variants": variants,
        })
    
    return results


@customer_tools.register(
    name="get_product_details",
    description="Get full details about a specific product including storage tips, organic info, and farmer origin.",
    parameters={"product_name": "Exact or partial product name (string)"},
)
def get_product_details(product_name: str) -> dict:
    """Get detailed info about a product."""
    from apps.inventory.models import Product
    
    try:
        product = Product.objects.filter(
            name__icontains=product_name.strip()
        ).select_related("category").prefetch_related(
            "benefits", "variants", "variants__batches__farmer__user"
        ).first()
        
        if not product:
            return {"found": False, "error": f"Product '{product_name}' not found"}
        
        # Get farmers who supply this product
        farmers = set()
        for variant in product.variants.all():
            for batch in variant.batches.all():
                if batch.farmer:
                    farmer = batch.farmer
                    farmers.add((
                        farmer.user.get_full_name() or farmer.user.username,
                        farmer.location,
                        batch.is_organic,
                    ))
        
        return {
            "found": True,
            "name": product.name,
            "category": product.category.name if product.category else None,
            "description": product.description,
            "storage_tips": product.storage_instructions,
            "benefits": [b.benefit for b in product.benefits.all()],
            "farmers": [
                {"name": f[0], "location": f[1], "organic": f[2]}
                for f in farmers
            ],
            "impact": {
                "water_saved_litres": float(product.water_score),
                "soil_supported_sqft": float(product.soil_score),
                "chemicals_reduced_grams": float(product.chemical_score),
            },
        }
        
    except Exception as e:
        return {"found": False, "error": str(e)}


@customer_tools.register(
    name="get_categories",
    description="List all product categories available on FreshOn.",
    parameters={},
)
def get_categories() -> list:
    """List all product categories."""
    from apps.inventory.models import Category
    
    categories = Category.objects.all()
    return [
        {"name": c.name, "emoji": c.emoji, "slug": c.slug}
        for c in categories
    ]


@customer_tools.register(
    name="get_farmer_info",
    description="Get information about a farmer by name — their location, crops, rating, and organic status.",
    parameters={"farmer_name": "Farmer's name (string, e.g., 'Ramesh')"},
)
def get_farmer_info(farmer_name: str) -> dict:
    """Look up farmer details by name."""
    from apps.accounts.models import FarmerProfile
    from django.db.models import Q
    
    try:
        farmer = FarmerProfile.objects.filter(
            Q(user__first_name__icontains=farmer_name.strip()) |
            Q(user__username__icontains=farmer_name.strip()) |
            Q(farm_name__icontains=farmer_name.strip())
        ).select_related("user").first()
        
        if not farmer:
            return {"found": False, "error": f"No farmer found matching '{farmer_name}'"}
        
        return {
            "found": True,
            "name": farmer.user.get_full_name() or farmer.user.username,
            "farm_name": farmer.farm_name,
            "location": farmer.location,
            "speciality": farmer.speciality,
            "years_experience": farmer.years_of_experience,
            "rating": float(farmer.rating),
            "organic_certified": farmer.organic_pledge_accepted,
            "crops": farmer.crops,
        }
        
    except Exception as e:
        return {"found": False, "error": str(e)}


# =============================================================================
# NEW TOOLS: Order Management (Cancel, Refund, Track)
# =============================================================================

@customer_tools.register(
    name="cancel_order",
    description="Cancel an order by tracking ID. Only orders in PENDING or CONFIRMED status can be cancelled.",
    parameters={"tracking_id": "The order tracking ID to cancel (e.g., 'FRSH-A1B2C3')"},
    requires_user=True,
)
def cancel_order(tracking_id: str, user=None) -> dict:
    """
    Cancel an order if it's still in a cancellable state.
    Only PENDING or CONFIRMED orders can be cancelled.
    """
    from apps.orders.models import Order
    from apps.wallet.models import WalletTransaction
    
    if not user:
        return {"success": False, "error": "User not authenticated"}
    
    try:
        order = Order.objects.get(tracking_id=tracking_id.upper().strip(), user=user)
        
        # Check if order can be cancelled
        cancellable_statuses = ['PENDING', 'CONFIRMED']
        if order.status not in cancellable_statuses:
            return {
                "success": False,
                "error": f"Order cannot be cancelled. Current status: {order.get_status_display()}. "
                        f"Only PENDING or CONFIRMED orders can be cancelled.",
                "status": order.status,
                "status_display": order.get_status_display(),
            }
        
        # Store original status for response
        original_status = order.get_status_display()
        
        # Update order status
        order.status = 'CANCELLED'
        order.save(update_fields=['status', 'updated_at'])
        
        # Handle refund if payment was made
        refund_amount = Decimal('0.00')
        if order.is_paid and order.payment_status == 'COMPLETED':
            # Refund to wallet
            try:
                wallet = user.wallet
                refund_amount = order.total
                
                # Create wallet transaction for refund
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=refund_amount,
                    reason='ORDER_REFUND',
                    balance_before=wallet.balance,
                    balance_after=wallet.balance + refund_amount,
                    related_order=order,
                    notes=f"Refund for cancelled order {order.tracking_id}"
                )
                
                # Update wallet balance
                wallet.balance += refund_amount
                wallet.save(update_fields=['balance', 'updated_at'])
                
            except Exception as e:
                logger.error(f"[cancel_order] Wallet refund failed: {e}")
                # Continue - order is cancelled even if refund fails
        
        response = {
            "success": True,
            "message": f"Order {order.tracking_id} has been cancelled successfully.",
            "tracking_id": order.tracking_id,
            "previous_status": original_status,
            "cancelled_at": timezone.now().strftime("%b %d, %Y at %I:%M %p"),
        }
        
        if refund_amount > 0:
            response["refund"] = {
                "amount": str(refund_amount),
                "method": "Wallet credit",
                "message": f"₹{refund_amount} has been credited to your wallet.",
            }
        
        return response
        
    except Order.DoesNotExist:
        return {"success": False, "error": f"No order found with tracking ID '{tracking_id}'"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@customer_tools.register(
    name="request_refund",
    description="Request a refund for a delivered order. Provide reason and issue description.",
    parameters={
        "tracking_id": "The order tracking ID (e.g., 'FRSH-A1B2C3')",
        "reason": "Reason for refund: DAMAGED, MISSING, WRONG_ITEM, QUALITY_ISSUE, or OTHER",
        "description": "Detailed description of the issue (optional)",
    },
    requires_user=True,
)
def request_refund(tracking_id: str, reason: str, description: str = "", user=None) -> dict:
    """
    Request a refund for a delivered order.
    Creates a refund request that will be reviewed by customer support.
    """
    from apps.orders.models import Order
    
    if not user:
        return {"success": False, "error": "User not authenticated"}
    
    valid_reasons = ['DAMAGED', 'MISSING', 'WRONG_ITEM', 'QUALITY_ISSUE', 'OTHER']
    reason = reason.upper().strip()
    
    if reason not in valid_reasons:
        return {
            "success": False,
            "error": f"Invalid reason. Must be one of: {', '.join(valid_reasons)}",
        }
    
    try:
        order = Order.objects.get(tracking_id=tracking_id.upper().strip(), user=user)
        
        # Check if order is eligible for refund
        if order.status != 'DELIVERED':
            return {
                "success": False,
                "error": f"Order is not eligible for refund. Current status: {order.get_status_display()}. "
                        f"Only delivered orders can be refunded.",
            }
        
        # Check if already refunded
        if order.payment_status == 'REFUNDED':
            return {
                "success": False,
                "error": "This order has already been refunded.",
            }
        
        # Check if refund already requested (within last 7 days)
        # Note: In production, you'd have a RefundRequest model
        # For now, we'll create a note on the order
        
        # Update order with refund request info
        order.payment_status = 'PENDING'  # Mark as pending review
        order.save(update_fields=['payment_status', 'updated_at'])
        
        # Map reason codes to readable text
        reason_map = {
            'DAMAGED': 'Product was damaged',
            'MISSING': 'Item missing from order',
            'WRONG_ITEM': 'Wrong item delivered',
            'QUALITY_ISSUE': 'Quality not as expected',
            'OTHER': 'Other reason',
        }
        
        return {
            "success": True,
            "message": f"Refund request submitted for order {order.tracking_id}.",
            "tracking_id": order.tracking_id,
            "refund_amount": str(order.total),
            "reason": reason_map.get(reason, reason),
            "description": description,
            "status": "PENDING_REVIEW",
            "next_steps": "Our support team will review your request within 24 hours. "
                         "You will receive an email with the decision.",
            "submitted_at": timezone.now().strftime("%b %d, %Y at %I:%M %p"),
        }
        
    except Order.DoesNotExist:
        return {"success": False, "error": f"No order found with tracking ID '{tracking_id}'"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@customer_tools.register(
    name="track_delivery",
    description="Get real-time delivery tracking information for an order including driver location and ETA.",
    parameters={"tracking_id": "The order tracking ID (e.g., 'FRSH-A1B2C3')"},
    requires_user=True,
)
def track_delivery(tracking_id: str, user=None) -> dict:
    """
    Get delivery tracking information for an order.
    Returns driver details, current location, and delivery status.
    """
    from apps.orders.models import Order
    from apps.delivery_partner.models import DeliveryAssignment, DeliveryStop
    
    if not user:
        return {"found": False, "error": "User not authenticated"}
    
    try:
        order = Order.objects.select_related('delivery_assignment').get(
            tracking_id=tracking_id.upper().strip(), 
            user=user
        )
        
        # Get basic order info
        order_info = {
            "tracking_id": order.tracking_id,
            "status": order.get_status_display(),
            "delivery_slot": order.get_delivery_slot_display(),
            "address": order.address_line,
        }
        
        # If order doesn't have a delivery assignment yet
        if not hasattr(order, 'delivery_assignment') or not order.delivery_assignment:
            # Check order status to provide appropriate message
            if order.status in ['PENDING', 'CONFIRMED', 'PROCESSING']:
                return {
                    "found": True,
                    "order": order_info,
                    "delivery_status": "PREPARING",
                    "message": "Your order is being prepared. A delivery partner will be assigned soon.",
                    "eta": "Will be updated once a driver is assigned",
                }
            else:
                return {
                    "found": True,
                    "order": order_info,
                    "delivery_status": order.status,
                    "message": f"Order status: {order.get_status_display()}",
                }
        
        assignment = order.delivery_assignment
        
        # Get delivery stops
        stops = []
        for stop in assignment.stops.all().order_by('sequence'):
            stops.append({
                "sequence": stop.sequence,
                "type": stop.type,
                "label": stop.label,
                "address": stop.address,
                "eta": stop.eta,
                "is_completed": stop.is_completed,
                "completed_at": stop.completed_at.strftime("%I:%M %p") if stop.completed_at else None,
            })
        
        # Build response
        tracking_info = {
            "found": True,
            "order": order_info,
            "delivery_status": assignment.get_status_display(),
            "service_type": assignment.get_service_display(),
            "assigned_at": assignment.created_at.strftime("%b %d, %I:%M %p"),
        }
        
        # Add driver info if assigned
        if assignment.partner:
            partner_profile = getattr(assignment.partner, 'delivery_partner_profile', None)
            driver_info = {
                "name": assignment.partner.get_full_name() or assignment.partner.username,
                "phone": assignment.partner.phone_number or "Available via app",
            }
            
            if partner_profile:
                driver_info.update({
                    "vehicle_type": partner_profile.get_vehicle_type_display(),
                    "vehicle_number": partner_profile.vehicle_number,
                    "rating": float(partner_profile.rating),
                    "is_online": partner_profile.is_online,
                })
                
                # Add live location if available
                if partner_profile.current_latitude and partner_profile.current_longitude:
                    driver_info["current_location"] = {
                        "lat": float(partner_profile.current_latitude),
                        "lng": float(partner_profile.current_longitude),
                        "updated_at": partner_profile.last_location_update.strftime("%I:%M %p") if partner_profile.last_location_update else None,
                    }
            
            tracking_info["driver"] = driver_info
        
        # Add stops
        tracking_info["stops"] = stops
        
        # Calculate progress
        total_stops = len(stops)
        completed_stops = sum(1 for s in stops if s["is_completed"])
        tracking_info["progress"] = {
            "completed_stops": completed_stops,
            "total_stops": total_stops,
            "percentage": int((completed_stops / total_stops * 100)) if total_stops > 0 else 0,
        }
        
        # Add status-specific messages
        status_messages = {
            'PENDING': "A delivery partner will accept your order soon.",
            'ACCEPTED': "Driver is heading to the pickup location.",
            'PICKED_UP': "Your order has been picked up and is on the way!",
            'IN_TRANSIT': "Your order is on the way to you!",
            'DELIVERED': "Your order has been delivered. Enjoy! 🎉",
            'CANCELLED': "This delivery has been cancelled.",
        }
        tracking_info["status_message"] = status_messages.get(assignment.status, "Tracking information updated.")
        
        return tracking_info
        
    except Order.DoesNotExist:
        return {"found": False, "error": f"No order found with tracking ID '{tracking_id}'"}
    except Exception as e:
        return {"found": False, "error": str(e)}


# =============================================================================
# NEW TOOLS: Wallet & Balance Inquiry
# =============================================================================

@customer_tools.register(
    name="get_wallet_balance",
    description="Get the user's wallet balance, tier status, and PRIDE partnership details.",
    parameters={},
    requires_user=True,
)
def get_wallet_balance(user=None) -> dict:
    """Get user's wallet balance and related information."""
    from apps.wallet.models import Wallet
    
    if not user:
        return {"error": "User not authenticated"}
    
    try:
        wallet = Wallet.objects.select_related('user').get(user=user)
        
        result = {
            "found": True,
            "balance": str(wallet.balance),
            "tier": wallet.get_tier_display(),
            "tier_code": wallet.tier,
        }
        
        # Add PRIDE partnership info if applicable
        if wallet.tier != 'STANDARD':
            result["pride_limit"] = {
                "accumulated": str(wallet.accumulated_pride_limit),
                "monthly_addition": str(wallet.get_monthly_pride_limit()),
            }
        
        return result
        
    except Wallet.DoesNotExist:
        return {
            "found": False,
            "balance": "0.00",
            "message": "No wallet found. A new wallet will be created when you make your first top-up.",
        }
    except Exception as e:
        return {"error": str(e)}


@customer_tools.register(
    name="get_wallet_transactions",
    description="Get recent wallet transactions (deposits, payments, refunds, credits).",
    parameters={"limit": "Number of transactions to return (default: 10, max: 50)"},
    requires_user=True,
)
def get_wallet_transactions(limit: int = 10, user=None) -> dict:
    """Get user's recent wallet transactions."""
    from apps.wallet.models import Wallet, WalletTransaction
    
    if not user:
        return {"error": "User not authenticated"}
    
    try:
        # Validate limit
        limit = min(max(int(limit), 1), 50)
        
        wallet = Wallet.objects.get(user=user)
        transactions = wallet.transactions.select_related('related_order').all()[:limit]
        
        if not transactions:
            return {
                "found": True,
                "wallet_balance": str(wallet.balance),
                "transactions": [],
                "message": "No transactions yet. Your wallet activity will appear here.",
            }
        
        return {
            "found": True,
            "wallet_balance": str(wallet.balance),
            "transactions": [
                {
                    "id": t.id,
                    "type": t.get_reason_display(),
                    "reason_code": t.reason,
                    "amount": str(t.amount),
                    "balance_before": str(t.balance_before),
                    "balance_after": str(t.balance_after),
                    "order_tracking_id": t.related_order.tracking_id if t.related_order else None,
                    "notes": t.notes,
                    "date": t.created_at.strftime("%b %d, %Y at %I:%M %p"),
                }
                for t in transactions
            ],
        }
        
    except Wallet.DoesNotExist:
        return {"error": "No wallet found. Please top up to create your wallet."}
    except Exception as e:
        return {"error": str(e)}


@customer_tools.register(
    name="get_partnership_details",
    description="Get PRIDE partnership details including tier, invested amount, benefits, and refund status.",
    parameters={},
    requires_user=True,
)
def get_partnership_details(user=None) -> dict:
    """Get user's PRIDE partnership details."""
    from apps.wallet.models import Partnership
    
    if not user:
        return {"error": "User not authenticated"}
    
    try:
        partnership = Partnership.objects.select_related('user').get(user=user)
        
        tier_benefits = {
            'TIER_1': {
                'discount': '30% immediate discount on MRP',
                'wallet_cashback': '10% added back to wallet instantly upon payment',
                'annual_bonus': '5% accumulated loyalty bonus credited once a year',
                'referral_bonus': '5% referral bonus on references\' 1st purchase',
                'total_benefits': 'Up to 50% total discount & savings benefits',
                'investment': '₹1.5 Lakhs',
            },
            'TIER_2': {
                'discount': '30% immediate discount on MRP',
                'wallet_cashback': '10% added back to wallet instantly upon payment',
                'annual_bonus': '5% accumulated loyalty bonus credited once a year',
                'referral_bonus': '5% referral bonus on references\' 1st purchase',
                'total_benefits': 'Up to 50% total discount & savings benefits',
                'investment': '₹3 Lakhs',
            },
            'TIER_3': {
                'discount': '30% immediate discount on MRP',
                'wallet_cashback': '10% added back to wallet instantly upon payment',
                'annual_bonus': '5% accumulated loyalty bonus credited once a year',
                'referral_bonus': '5% referral bonus on references\' 1st purchase',
                'total_benefits': 'Up to 50% total discount & savings benefits + Premium perks',
                'investment': '₹5 Lakhs',
            },
        }
        
        benefits = tier_benefits.get(partnership.tier, {})
        
        result = {
            "is_partner": True,
            "tier": partnership.get_tier_display(),
            "tier_code": partnership.tier,
            "invested_amount": str(partnership.invested_amount),
            "start_date": partnership.start_date.strftime("%b %d, %Y"),
            "monthly_credit_percentage": str(partnership.monthly_credit_percentage),
            "annual_loyalty_percentage": str(partnership.annual_loyalty_percentage),
            "benefits": benefits,
        }
        
        if partnership.refund_requested:
            result["refund_status"] = {
                "requested": True,
                "approved_date": partnership.refund_approved_date.strftime("%b %d, %Y") if partnership.refund_approved_date else "Pending approval",
                "message": "Your refund request is being processed. 100% refundable with 1-month notice.",
            }
        
        return result
        
    except Partnership.DoesNotExist:
        return {
            "is_partner": False,
            "message": "You are not a PRIDE partner yet. Join PRIDE to earn up to 50% total discount & savings benefits!",
            "tiers_available": [
                {
                    "tier": "Tier 1", 
                    "investment": "₹1.5L", 
                    "benefits": "Up to 50% total benefits: 30% immediate discount + 10% wallet cashback + 5% annual loyalty bonus + 5% referral reference bonus"
                },
                {
                    "tier": "Tier 2", 
                    "investment": "₹3L", 
                    "benefits": "Up to 50% total benefits: 30% immediate discount + 10% wallet cashback + 5% annual loyalty bonus + 5% referral reference bonus"
                },
                {
                    "tier": "Tier 3", 
                    "investment": "₹5L", 
                    "benefits": "Up to 50% total benefits: 30% immediate discount + 10% wallet cashback + 5% annual loyalty bonus + 5% referral reference bonus + Premium perks"
                },
            ],
        }
    except Exception as e:
        return {"error": str(e)}


@customer_tools.register(
    name="get_referral_info",
    description="Get referral code, share link, and referral bonus earnings.",
    parameters={},
    requires_user=True,
)
def get_referral_info(user=None) -> dict:
    """Get user's referral information."""
    from apps.wallet.models import Referral
    
    if not user:
        return {"error": "User not authenticated"}
    
    try:
        # Generate referral code from user data
        referral_code = f"FRESH{user.id:04d}"
        share_link = f"https://freshon.in/join?ref={referral_code}"
        
        # Get referral stats
        referrals_given = Referral.objects.filter(referrer=user)
        total_earned = sum(r.bonus_amount for r in referrals_given.filter(status='CREDITED'))
        
        pending_count = referrals_given.filter(status='PENDING').count()
        completed_count = referrals_given.filter(status__in=['COMPLETED', 'CREDITED']).count()
        
        return {
            "found": True,
            "referral_code": referral_code,
            "share_link": share_link,
            "stats": {
                "total_referrals": referrals_given.count(),
                "completed": completed_count,
                "pending": pending_count,
                "total_earned": str(total_earned),
            },
            "message": f"Share your code {referral_code} with friends! You both get bonuses when they place their first order.",
        }
        
    except Exception as e:
        return {"error": str(e)}


@customer_tools.register(
    name="get_my_impact",
    description="Get the user's cumulative environmental impact metrics from organic purchases.",
    parameters={},
    requires_user=True,
)
def get_my_impact(user=None) -> dict:
    """Get user's environmental impact metrics."""
    from apps.wallet.models import CustomerImpact
    
    if not user:
        return {"error": "User not authenticated"}
    
    try:
        impact, created = CustomerImpact.objects.get_or_create(user=user)
        
        return {
            "found": True,
            "total_orders": impact.total_orders,
            "environmental_impact": {
                "water_saved_litres": float(impact.total_water),
                "soil_supported_sqft": float(impact.total_soil),
                "chemicals_reduced_grams": float(impact.total_chemical),
            },
            "farmer_support": float(impact.total_farmer),
            "message": "Thank you for supporting organic farming! Every order makes a difference. 🌱",
        }
        
    except Exception as e:
        return {"error": str(e)}
