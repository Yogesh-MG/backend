"""
Customer Agent Tools — Real Django ORM queries for customer support.

These are the production versions of the fake tools from Lesson 2.
Each tool queries actual database models and returns structured data
the agent can use to answer customer questions.
"""

from apps.agents.engine.tools import ToolRegistry

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
    
    try:
        # Only allow users to see their own orders
        filters = {"tracking_id": tracking_id.upper().strip()}
        if user:
            filters["user"] = user
        
        order = Order.objects.select_related("user").prefetch_related("items").get(**filters)
        
        items = [
            {
                "product": item.product_name,
                "quantity": item.quantity,
                "unit": item.unit,
                "price": str(item.price),
            }
            for item in order.items.all()
        ]
        
        return {
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
        
    except Order.DoesNotExist:
        return {"found": False, "error": f"No order found with tracking ID '{tracking_id}'"}
    except Exception as e:
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
    
    if not user:
        return [{"error": "User not authenticated"}]
    
    orders = Order.objects.filter(user=user).order_by("-created_at")[:5]
    
    if not orders:
        return [{"message": "You don't have any orders yet. Start shopping! 🛒"}]
    
    return [
        {
            "tracking_id": o.tracking_id,
            "status": o.get_status_display(),
            "total": str(o.total),
            "items_count": o.items.count(),
            "placed_at": o.created_at.strftime("%b %d, %I:%M %p"),
        }
        for o in orders
    ]


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
