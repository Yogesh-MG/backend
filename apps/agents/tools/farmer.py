"""
Farmer Inventory Agent Tools — Helps farmers list harvests via natural language.

These tools enable farmers to:
  1. List their current inventory batches
  2. Add new harvests by describing them naturally (e.g., "I have 50kg tomatoes")
  3. Get pricing suggestions based on market rates
  4. Update existing batch quantities
  5. View their sales and earnings summary
"""

import logging
import re
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from apps.agents.engine.tools import ToolRegistry

logger = logging.getLogger(__name__)

# Create the farmer tools registry
farmer_tools = ToolRegistry()


@farmer_tools.register(
    name="get_my_inventory",
    description="Get the farmer's current inventory batches with stock levels, prices, and approval status",
    parameters={},
    requires_user=True,
)
def get_my_inventory(user=None) -> list:
    """Get all inventory batches for the current farmer."""
    from apps.inventory.models import InventoryBatch
    from apps.accounts.models import FarmerProfile
    
    if not user:
        return [{"error": "User not authenticated"}]
    
    try:
        profile = FarmerProfile.objects.get(user=user)
        batches = InventoryBatch.objects.filter(farmer=profile).select_related(
            'variant', 'variant__product'
        ).order_by('-harvest_date')
        
        if not batches:
            return [{
                "message": "You don't have any inventory listed yet. Use 'add_harvest' to list your produce! 🌾"
            }]
        
        return [
            {
                "batch_id": str(batch.id),
                "product": batch.variant.product.name,
                "variant": batch.variant.unit,
                "stock_level": float(batch.stock_level),
                "purchase_price": str(batch.purchase_price),
                "selling_price": str(batch.variant.price),
                "is_organic": batch.is_organic,
                "is_approved": batch.is_approved,
                "harvest_date": batch.harvest_date.strftime("%b %d, %Y"),
                "status": "Live" if batch.is_approved and batch.stock_level > 0 else "Pending Approval" if not batch.is_approved else "Out of Stock",
            }
            for batch in batches
        ]
        
    except FarmerProfile.DoesNotExist:
        return [{"error": "Farmer profile not found. Please complete your profile first."}]
    except Exception as e:
        return [{"error": str(e)}]


@farmer_tools.register(
    name="add_harvest",
    description="Add a new harvest/inventory batch. Parse natural language like 'I have 50kg tomatoes at ₹30/kg' or provide structured data.",
    parameters={
        "product_name": "Name of the product (e.g., 'Tomato', 'Spinach', 'Potato')",
        "quantity": "Amount with unit (e.g., '50kg', '100 pieces', '2 dozen')",
        "price_per_unit": "Price per unit in INR (e.g., 30, 45.50)",
        "is_organic": "Whether the produce is organic (true/false, default: false)",
        "harvest_date": "When harvested, ISO format or 'today', 'yesterday', '2 days ago' (optional)",
        "custom_product": "Set to true if this is a new product not in catalog (optional)"
    },
    requires_user=True,
)
def add_harvest(
    product_name: str,
    quantity: str,
    price_per_unit: float,
    is_organic: bool = False,
    harvest_date: str = None,
    custom_product: bool = False,
    user=None
) -> dict:
    """
    Add a new harvest batch to the farmer's inventory.
    Creates product/variant if needed and links to the farmer.
    """
    from apps.inventory.models import InventoryBatch, Product, ProductVariant, Category
    from apps.accounts.models import FarmerProfile
    
    if not user:
        return {"success": False, "error": "User not authenticated"}
    
    try:
        profile = FarmerProfile.objects.get(user=user)
        
        # Parse quantity (e.g., "50kg" -> 50, "kg")
        stock_level, unit = _parse_quantity(quantity)
        if stock_level is None:
            return {
                "success": False, 
                "error": f"Could not parse quantity: '{quantity}'. Please use format like '50kg', '100 pieces', '2 dozen'"
            }
        
        # Parse harvest date
        parsed_harvest_date = _parse_harvest_date(harvest_date)
        
        # Find or create product
        product = None
        if not custom_product:
            # Try to find existing product (case-insensitive)
            product = Product.objects.filter(name__iexact=product_name.strip()).first()
        
        is_new_product = False
        if not product:
            # Create new product (will need approval)
            is_new_product = True
            default_category = Category.objects.first()
            if not default_category:
                return {"success": False, "error": "No product categories configured in system"}
            
            product = Product.objects.create(
                name=product_name.strip().title(),
                category=default_category,
                description=f"Fresh {product_name.lower()} from {profile.farm_name or profile.user.get_full_name()}",
                storage_instructions="Store in a cool, dry place.",
                is_perishable=True,
            )
            logger.info(f"[FarmerAgent] Created new product: {product.name}")
        
        # Get or create variant with the parsed unit
        variant = product.variants.filter(unit__iexact=unit).first()
        if not variant:
            variant = ProductVariant.objects.create(
                product=product,
                unit=unit,
                price=Decimal(str(price_per_unit)) * Decimal('1.25'),  # 25% markup for selling price
                mrp=Decimal(str(price_per_unit)) * Decimal('1.4'),  # 40% markup for MRP
            )
        else:
            # Update pricing on existing variant
            variant.price = Decimal(str(price_per_unit)) * Decimal('1.25')
            variant.mrp = Decimal(str(price_per_unit)) * Decimal('1.4')
            variant.save(update_fields=['price', 'mrp'])
        
        # Create the inventory batch
        batch = InventoryBatch.objects.create(
            farmer=profile,
            variant=variant,
            purchase_price=Decimal(str(price_per_unit)),
            stock_level=Decimal(str(stock_level)),
            harvest_date=parsed_harvest_date,
            is_organic=is_organic,
            is_farm_fresh=True,
            is_approved=not is_new_product,  # New products need approval
        )
        
        result = {
            "success": True,
            "message": f"✅ Listed {stock_level} {unit} of {product.name} at ₹{price_per_unit}/{unit}",
            "batch_id": str(batch.id),
            "product": product.name,
            "quantity": f"{stock_level} {unit}",
            "your_price": f"₹{price_per_unit}",
            "selling_price": f"₹{variant.price}",
            "is_organic": is_organic,
            "status": "Pending Approval" if is_new_product else "Live",
            "harvest_date": parsed_harvest_date.strftime("%b %d, %Y"),
        }
        
        if is_new_product:
            result["note"] = "This is a new product and will be reviewed by our team before going live."
        
        return result
        
    except FarmerProfile.DoesNotExist:
        return {"success": False, "error": "Farmer profile not found. Please complete your profile first."}
    except Exception as e:
        logger.error(f"[FarmerAgent] add_harvest error: {e}")
        return {"success": False, "error": str(e)}


@farmer_tools.register(
    name="update_batch_stock",
    description="Update the stock level for an existing batch (add more quantity or mark as sold out)",
    parameters={
        "batch_id": "The batch ID (from get_my_inventory)",
        "new_quantity": "New stock level (number)",
        "action": "'set' to set exact quantity, 'add' to add to existing, 'subtract' to reduce (default: 'set')"
    },
    requires_user=True,
)
def update_batch_stock(batch_id: str, new_quantity: float, action: str = "set", user=None) -> dict:
    """Update stock level for an existing batch."""
    from apps.inventory.models import InventoryBatch
    from apps.accounts.models import FarmerProfile
    
    if not user:
        return {"success": False, "error": "User not authenticated"}
    
    try:
        profile = FarmerProfile.objects.get(user=user)
        batch = InventoryBatch.objects.get(id=batch_id, farmer=profile)
        
        old_quantity = float(batch.stock_level)
        
        if action == "add":
            batch.stock_level += Decimal(str(new_quantity))
        elif action == "subtract":
            batch.stock_level -= Decimal(str(new_quantity))
            if batch.stock_level < 0:
                batch.stock_level = 0
        else:  # set
            batch.stock_level = Decimal(str(new_quantity))
        
        batch.save(update_fields=['stock_level', 'updated_at'])
        
        return {
            "success": True,
            "message": f"✅ Stock updated for {batch.variant.product.name}",
            "batch_id": str(batch.id),
            "product": batch.variant.product.name,
            "previous_quantity": old_quantity,
            "new_quantity": float(batch.stock_level),
            "unit": batch.variant.unit,
        }
        
    except InventoryBatch.DoesNotExist:
        return {"success": False, "error": "Batch not found or you don't have permission to update it"}
    except FarmerProfile.DoesNotExist:
        return {"success": False, "error": "Farmer profile not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@farmer_tools.register(
    name="get_pricing_suggestion",
    description="Get suggested pricing for a product based on current market rates and similar products",
    parameters={
        "product_name": "Name of the product to get pricing for"
    },
)
def get_pricing_suggestion(product_name: str) -> dict:
    """Get pricing suggestions based on similar products in the catalog."""
    from apps.inventory.models import Product, ProductVariant, InventoryBatch
    from django.db.models import Avg, Min, Max
    
    try:
        # Find similar products
        similar_products = Product.objects.filter(name__icontains=product_name.strip())
        
        if not similar_products.exists():
            # Try broader search
            words = product_name.strip().split()
            for word in words:
                if len(word) > 3:
                    similar_products = Product.objects.filter(name__icontains=word)
                    if similar_products.exists():
                        break
        
        if not similar_products.exists():
            return {
                "found": False,
                "message": f"No similar products found for '{product_name}'. You can set your own price.",
                "suggested_range": {"min": 20, "max": 100},
            }
        
        # Get pricing data from variants
        variants = ProductVariant.objects.filter(product__in=similar_products, is_active=True)
        
        if not variants.exists():
            return {
                "found": False,
                "message": f"No pricing data available for '{product_name}'",
            }
        
        # Calculate stats
        price_stats = variants.aggregate(
            avg_price=Avg('price'),
            min_price=Min('price'),
            max_price=Max('price')
        )
        
        # Get recent batches for farmer pricing reference
        recent_batches = InventoryBatch.objects.filter(
            variant__product__in=similar_products
        ).select_related('variant').order_by('-created_at')[:5]
        
        farmer_prices = [float(b.purchase_price) for b in recent_batches]
        
        return {
            "found": True,
            "product": product_name,
            "market_rates": {
                "average_selling_price": f"₹{price_stats['avg_price']:.2f}" if price_stats['avg_price'] else "N/A",
                "price_range": f"₹{price_stats['min_price']:.0f} - ₹{price_stats['max_price']:.0f}" if price_stats['min_price'] else "N/A",
            },
            "recent_farmer_prices": farmer_prices if farmer_prices else None,
            "suggested_farmer_price": f"₹{sum(farmer_prices)/len(farmer_prices):.2f}" if farmer_prices else f"₹{price_stats['avg_price'] * 0.8:.2f}" if price_stats['avg_price'] else "₹30-50",
            "note": "These are reference prices. You can set your own price based on quality and demand."
        }
        
    except Exception as e:
        return {"found": False, "error": str(e)}


@farmer_tools.register(
    name="get_my_sales_summary",
    description="Get a summary of the farmer's sales, earnings, and order statistics",
    parameters={},
    requires_user=True,
)
def get_my_sales_summary(user=None) -> dict:
    """Get sales summary for the current farmer."""
    from apps.orders.models import OrderItem
    from apps.accounts.models import FarmerProfile
    from django.db.models import Sum, Count
    from datetime import timedelta
    
    if not user:
        return {"error": "User not authenticated"}
    
    try:
        profile = FarmerProfile.objects.get(user=user)
        
        # Get all sold items
        sold_items = OrderItem.objects.filter(batch__farmer=profile)
        
        # Overall stats
        total_revenue = sold_items.aggregate(total=Sum('purchase_price'))['total'] or 0
        total_orders = sold_items.values('order').distinct().count()
        total_items_sold = sold_items.aggregate(total=Sum('quantity'))['total'] or 0
        
        # This month's stats
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_items = sold_items.filter(order__created_at__gte=month_start)
        monthly_revenue = monthly_items.aggregate(total=Sum('purchase_price'))['total'] or 0
        
        # This week's stats
        week_start = timezone.now() - timedelta(days=7)
        weekly_items = sold_items.filter(order__created_at__gte=week_start)
        weekly_revenue = weekly_items.aggregate(total=Sum('purchase_price'))['total'] or 0
        
        # Top selling products
        top_products = sold_items.values('product_name').annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('purchase_price')
        ).order_by('-total_quantity')[:5]
        
        return {
            "found": True,
            "summary": {
                "total_revenue": f"₹{float(total_revenue):.2f}",
                "total_orders": total_orders,
                "total_items_sold": int(total_items_sold) if total_items_sold else 0,
                "this_month": f"₹{float(monthly_revenue):.2f}",
                "this_week": f"₹{float(weekly_revenue):.2f}",
            },
            "top_selling_products": [
                {
                    "product": p['product_name'],
                    "quantity_sold": int(p['total_quantity']) if p['total_quantity'] else 0,
                    "revenue": f"₹{float(p['total_revenue']):.2f}" if p['total_revenue'] else "₹0.00",
                }
                for p in top_products
            ] if top_products else [],
            "message": "Keep up the great work! 🌾" if total_revenue > 0 else "Start listing your produce to see sales here! 🌱"
        }
        
    except FarmerProfile.DoesNotExist:
        return {"error": "Farmer profile not found"}
    except Exception as e:
        return {"error": str(e)}


@farmer_tools.register(
    name="search_catalog_products",
    description="Search the product catalog to see what's already available before listing new produce",
    parameters={
        "query": "Search term (e.g., 'tomato', 'leafy', 'vegetable')"
    },
)
def search_catalog_products(query: str) -> list:
    """Search existing products in the catalog."""
    from apps.inventory.models import Product
    
    try:
        products = Product.objects.filter(
            name__icontains=query.strip()
        ).prefetch_related('variants')[:10]
        
        if not products:
            return [{"message": f"No products found matching '{query}'. You can create a new product listing."}]
        
        return [
            {
                "product_id": p.id,
                "name": p.name,
                "category": p.category.name if p.category else None,
                "variants": [
                    {"unit": v.unit, "price": str(v.price)}
                    for v in p.variants.filter(is_active=True)
                ],
                "is_perishable": p.is_perishable,
            }
            for p in products
        ]
        
    except Exception as e:
        return [{"error": str(e)}]


@farmer_tools.register(
    name="parse_harvest_message",
    description="Parse a natural language harvest announcement and extract structured data (product, quantity, price, etc.)",
    parameters={
        "message": "Natural language message from farmer (e.g., 'I have 50kg fresh tomatoes at ₹30 per kg harvested yesterday')"
    },
)
def parse_harvest_message(message: str) -> dict:
    """
    Parse natural language harvest announcements.
    This is a helper tool that extracts structured data without creating the batch.
    """
    try:
        parsed = _parse_natural_language_harvest(message)
        
        if parsed.get("product"):
            return {
                "success": True,
                "parsed_data": parsed,
                "message": f"I understood: {parsed['quantity']} of {parsed['product']} at ₹{parsed.get('price', 'unknown')}/unit, harvested {parsed.get('harvest_date', 'recently')}",
                "ready_to_add": parsed.get("product") and parsed.get("quantity") and parsed.get("price"),
            }
        else:
            return {
                "success": False,
                "parsed_data": parsed,
                "message": "I couldn't fully understand your message. Please provide: product name, quantity (e.g., 50kg), and price per unit.",
                "ready_to_add": False,
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Helper Functions
# =============================================================================

def _parse_quantity(quantity_str: str) -> tuple:
    """
    Parse quantity string like '50kg', '100 pieces', '2 dozen' into (number, unit).
    Returns (None, None) if parsing fails.
    """
    if not quantity_str:
        return None, None
    
    quantity_str = quantity_str.strip().lower()
    
    # Pattern: number followed by unit (50kg, 100 pieces, etc.)
    patterns = [
        r'^(\d+\.?\d*)\s*(kg|kilos?|kilograms?)$',
        r'^(\d+\.?\d*)\s*(g|grams?|gm)$',
        r'^(\d+\.?\d*)\s*(l|liters?|litres?)$',
        r'^(\d+\.?\d*)\s*(ml|milliliters?)$',
        r'^(\d+\.?\d*)\s*(pieces?|pcs?)$',
        r'^(\d+\.?\d*)\s*(dozen|dz)$',
        r'^(\d+\.?\d*)\s*(bunches?|bun)$',
        r'^(\d+\.?\d*)\s*(boxes?|bx)$',
        r'^(\d+\.?\d*)\s*(units?|pcs?)$',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, quantity_str)
        if match:
            amount = float(match.group(1))
            unit_raw = match.group(2)
            
            # Normalize unit
            unit_map = {
                'kg': 'kg', 'kilo': 'kg', 'kilos': 'kg', 'kilogram': 'kg', 'kilograms': 'kg',
                'g': 'g', 'gram': 'g', 'grams': 'g', 'gm': 'g',
                'l': 'L', 'liter': 'L', 'liters': 'L', 'litre': 'L', 'litres': 'L',
                'ml': 'ml', 'milliliter': 'ml', 'milliliters': 'ml', 'millilitre': 'ml',
                'piece': 'piece', 'pieces': 'piece', 'pc': 'piece', 'pcs': 'piece',
                'dozen': 'dozen', 'dz': 'dozen',
                'bunch': 'bunch', 'bunches': 'bunch', 'bun': 'bunch',
                'box': 'box', 'boxes': 'box', 'bx': 'box',
                'unit': 'unit', 'units': 'unit',
            }
            
            unit = unit_map.get(unit_raw, unit_raw)
            return amount, unit
    
    # Try simple number extraction as fallback
    number_match = re.match(r'^(\d+\.?\d*)', quantity_str)
    if number_match:
        return float(number_match.group(1)), 'kg'  # Default to kg
    
    return None, None


def _parse_harvest_date(date_str: str) -> datetime:
    """Parse various date formats into a datetime object."""
    if not date_str:
        return timezone.now()
    
    date_str = date_str.strip().lower()
    
    # Handle relative dates
    if date_str == 'today':
        return timezone.now()
    elif date_str == 'yesterday':
        return timezone.now() - timedelta(days=1)
    elif 'day ago' in date_str or 'days ago' in date_str:
        match = re.search(r'(\d+)\s*days?\s*ago', date_str)
        if match:
            days = int(match.group(1))
            return timezone.now() - timedelta(days=days)
    
    # Try ISO format
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        pass
    
    # Try common date formats
    formats = [
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%b %d, %Y',
        '%d %b %Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Default to now if parsing fails
    return timezone.now()


def _parse_natural_language_harvest(message: str) -> dict:
    """
    Parse natural language harvest descriptions.
    Examples:
      - "I have 50kg tomatoes at ₹30/kg"
      - "Fresh spinach 20 bunches harvested yesterday"
      - "Organic potatoes 100kg price 25 per kg"
    """
    message = message.lower()
    
    result = {
        "product": None,
        "quantity": None,
        "price": None,
        "is_organic": False,
        "harvest_date": None,
    }
    
    # Check for organic
    if 'organic' in message:
        result["is_organic"] = True
    
    # Extract price - look for rupee symbol or "rs" or "price" or "at"
    price_patterns = [
        r'[₹rs]\s*(\d+\.?\d*)\s*(?:per|/|\s)\s*(?:kg|g|piece|unit)',
        r'price\s*:?\s*(\d+\.?\d*)',
        r'at\s+(\d+\.?\d*)\s*(?:per|/|\s)',
        r'(\d+\.?\d*)\s*(?:per|/|\s)\s*(?:kg|g|piece|unit)',
        r'[₹rs]\s*(\d+\.?\d*)',
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, message)
        if match:
            result["price"] = float(match.group(1))
            break
    
    # Extract quantity - look for number + unit patterns
    quantity_patterns = [
        r'(\d+\.?\d*)\s*(kg|kilos?|g|grams?|pieces?|pcs?|dozen|bunches?|boxes?|units?)',
        r'(\d+\.?\d*)\s*(kg|kilos?|g|grams?)',
    ]
    
    for pattern in quantity_patterns:
        match = re.search(pattern, message)
        if match:
            amount = match.group(1)
            unit = match.group(2)
            result["quantity"] = f"{amount}{unit}"
            break
    
    # Extract harvest date keywords
    if 'today' in message:
        result["harvest_date"] = "today"
    elif 'yesterday' in message:
        result["harvest_date"] = "yesterday"
    else:
        days_match = re.search(r'(\d+)\s*days?\s*ago', message)
        if days_match:
            result["harvest_date"] = f"{days_match.group(1)} days ago"
    
    # Extract product name - this is trickier
    # Remove common words and look for what's left
    common_words = ['i', 'have', 'fresh', 'organic', 'harvested', 'at', 'price', 'per', 'kg', 'rs', 'rupees', 'today', 'yesterday']
    
    # Try to find product after quantity or before price
    words = message.split()
    for i, word in enumerate(words):
        # Skip numbers and common words
        if word.replace('.', '').isdigit() or word in common_words:
            continue
        # Skip units
        if word in ['kg', 'g', 'grams', 'kilos', 'pieces', 'pcs', 'dozen', 'bunches', 'boxes']:
            continue
        # If we found a quantity before this, this might be the product
        if result["quantity"] and i > 0:
            # Look for the word right before quantity
            qty_match = re.search(r'(\d+\.?\d*)\s*\w+', message)
            if qty_match:
                qty_start = message.find(qty_match.group(0))
                if qty_start > 0:
                    # Product is likely before the quantity
                    before_qty = message[:qty_start].strip()
                    # Remove common words
                    for cw in common_words:
                        before_qty = before_qty.replace(cw, '').strip()
                    if before_qty:
                        result["product"] = before_qty.title()
                        break
        
        # If no quantity found yet, look for product after "have" or at start
        if not result["product"] and len(word) > 2:
            if word not in common_words:
                # Check if next words form a product name
                potential_product = word
                for j in range(i+1, min(i+3, len(words))):
                    next_word = words[j]
                    if next_word not in common_words and not next_word.replace('.', '').isdigit():
                        potential_product += " " + next_word
                    else:
                        break
                result["product"] = potential_product.title()
                break
    
    return result
