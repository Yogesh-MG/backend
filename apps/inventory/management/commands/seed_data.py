import random
import os
import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User, FarmerProfile
from apps.inventory.models import Category, SubCategory, Product, InventoryBatch, ProductBenefit, ProductVariant
from apps.delivery_partner.models import DeliveryPartnerProfile
from apps.picker.models import PickerProfile, Hub
from apps.pos.models import PosEmployee

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

class Command(BaseCommand):
    help = 'Seeds the database with real products from Products.csv or fallback dummy data'

    def create_users(self):
        self.stdout.write("Creating Farmers...")
        farmers_data = [
            {"username": "lakshmi", "name": "Lakshmi Devi", "loc": "Mysuru", "img": "https://images.unsplash.com/photo-1544005313-94ddf0286df2"},
            {"username": "ramesh", "name": "Ramesh Patil", "loc": "Nashik", "img": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d"},
            {"username": "anita", "name": "Anita Sharma", "loc": "Mahabaleshwar", "img": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80"},
            {"username": "gurpreet", "name": "Gurpreet Singh", "loc": "Amritsar", "img": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e"},
            {"username": "venkat", "name": "Venkat Raman", "loc": "Salem", "img": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e"},
        ]
        farmer_profiles = []
        for f in farmers_data:
            user, _ = User.objects.get_or_create(username=f['username'], defaults={"role": User.Role.FARMER})
            user.first_name = f['name'].split()[0]
            user.last_name = f['name'].split()[1] if len(f['name'].split()) > 1 else ""
            user.set_password("freshon123")
            user.save()
            profile, _ = FarmerProfile.objects.get_or_create(user=user, defaults={"location": f['loc'], "rating": 4.9})
            profile.image = f['img']
            profile.save()
            farmer_profiles.append(profile)

        self.stdout.write("Creating Hubs and Pickers...")
        hub, created = Hub.objects.get_or_create(name="FreshOn Main Hub", defaults={"latitude": 12.9548049, "longitude": 77.5202638})
        if not created:
            hub.latitude = 12.9548049
            hub.longitude = 77.5202638
            hub.save()
        
        pickers_data = [
            {"username": "picker1", "name": "Rahul Picker", "pin": "123456"},
            {"username": "picker2", "name": "Suresh Picker", "pin": "654321"},
        ]
        for p in pickers_data:
            user, _ = User.objects.get_or_create(username=p['username'], defaults={"role": User.Role.PICKER})
            user.set_password("freshon123")
            user.save()
            PickerProfile.objects.get_or_create(user=user, defaults={"hub": hub, "pin": p['pin'], "hub_name": hub.name})

        self.stdout.write("Creating Delivery Partners...")
        delivery_data = [
            {"username": "driver1", "name": "Deepak Driver", "vehicle": "BIKE", "number": "KA-01-EF-1234"},
            {"username": "driver2", "name": "Arjun Driver", "vehicle": "SCOOTER", "number": "KA-02-GH-5678"},
        ]
        for d in delivery_data:
            user, _ = User.objects.get_or_create(username=d['username'], defaults={"role": User.Role.DELIVERY})
            user.set_password("freshon123")
            user.save()
            DeliveryPartnerProfile.objects.get_or_create(user=user, defaults={"vehicle_type": d['vehicle'], "vehicle_number": d['number'], "is_online": True})

        self.stdout.write("Creating POS Operators...")
        pos_data = [
            {"username": "pos1", "name": "Priya POS", "emp_id": "EMP-001", "pin": "112233"},
            {"username": "pos2", "name": "Kiran POS", "emp_id": "EMP-002", "pin": "445566"},
        ]
        for pos in pos_data:
            user, _ = User.objects.get_or_create(username=pos['username'], defaults={"role": User.Role.POS_OPERATOR})
            user.set_password("freshon123")
            user.save()
            PosEmployee.objects.get_or_create(user=user, defaults={"employee_id": pos['emp_id'], "pin": pos['pin']})

        self.stdout.write("Creating Customers and Admins...")
        # Create a default customer
        customer_user, _ = User.objects.get_or_create(username="customer", defaults={"role": User.Role.CUSTOMER})
        customer_user.set_password("freshon123")
        customer_user.save()
        
        # Create a default admin
        admin_user, _ = User.objects.get_or_create(username="admin", defaults={"role": User.Role.ADMIN, "is_staff": True, "is_superuser": True})
        admin_user.set_password("freshon123")
        admin_user.save()
        
        return farmer_profiles

    def handle(self, *args, **kwargs):
        self.stdout.write("Cleaning old data...")
        InventoryBatch.objects.all().delete()
        ProductVariant.objects.all().delete()
        ProductBenefit.objects.all().delete()
        Product.objects.all().delete()
        SubCategory.objects.all().delete()
        Category.objects.all().delete()

        # Try to load from Products.csv first (the main product data file)
        csv_file = "Products.csv"
        if os.path.exists(csv_file):
            self.stdout.write(f"Loading from {csv_file}...")
            self.seed_from_products_csv(csv_file)
            return

        # Fallback to dummy data seeding
        self.stdout.write(self.style.WARNING(f"{csv_file} not found. Using fallback dummy data..."))
        self.seed_fallback_data()

    def seed_from_products_csv(self, csv_file):
        """Load products from Products.csv with fields matching our models"""
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f)
                if csv_reader.fieldnames is None:
                    raise ValueError("CSV file is empty or cannot be read")
                
                rows = list(csv_reader)
                if not rows:
                    raise ValueError("No data rows in CSV file")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading CSV: {e}. Falling back to dummy data..."))
            return self.seed_fallback_data()

        farmer_profiles = self.create_users()

        self.stdout.write("Seeding products from Products.csv...")
        
        # Image pools for categories
        img_pools = {
            "Millets Poha": "https://images.unsplash.com/photo-1586201375761-83865001e31c",
            "Whole Grain Millets": "https://images.unsplash.com/photo-1586201375761-83865001e31c",
            "Millets Rice": "https://images.unsplash.com/photo-1586201375761-83865001e31c",
            "Raisins": "https://images.unsplash.com/photo-1599599810694-b5ac4dd0b676",
            "Dry Fruits": "https://images.unsplash.com/photo-1599599810694-b5ac4dd0b676",
            "Roasted": "https://images.unsplash.com/photo-1599599810694-b5ac4dd0b676",
            "Cashew": "https://images.unsplash.com/photo-1599599810694-b5ac4dd0b676",
            "Seeds": "https://images.unsplash.com/photo-1536591030366-f76f74296482",
            "Almonds": "https://images.unsplash.com/photo-1599599810694-b5ac4dd0b676",
            "Concentrate": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5",
            "Tea & Coffee": "https://images.unsplash.com/photo-1544787210-2211d7c00676",
            "Cold Pressed Oil": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5",
            "Dry Fruits & Seeds": "https://images.unsplash.com/photo-1599599810694-b5ac4dd0b676",
            "Glass Products": "https://images.unsplash.com/photo-1542838132-92c53300491e",
            "Immunity Booster": "https://images.unsplash.com/photo-1505576399279-565b52d4ac71",
            "Nature Friendly": "https://images.unsplash.com/photo-1542838132-92c53300491e",
            "Pulses": "https://images.unsplash.com/photo-1585994192701-97061730872c",
            "Rava Sooji": "https://images.unsplash.com/photo-1509440159596-0249088772ff",
            "Ready To Cook": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c",
            "Rice": "https://images.unsplash.com/photo-1586201375761-83865001e31c",
            "Rice Products": "https://images.unsplash.com/photo-1586201375761-83865001e31c",
            "Salt": "https://images.unsplash.com/photo-1518110925495-5fe2fda0442c",
            "Snacks": "https://images.unsplash.com/photo-1599490659213-e2b9527bb087",
            "Spice Powder": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d",
            "Blended Masalas": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d",
            "Sweet": "https://images.unsplash.com/photo-1587049352846-4a222e784d38",
            "Table Ware": "https://images.unsplash.com/photo-1542838132-92c53300491e",
            "Whole grains": "https://images.unsplash.com/photo-1586201375761-83865001e31c",
            "Whole Spices": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d",
            "Chutney Powder": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d",
            "Jaggery": "https://images.unsplash.com/photo-1587049352846-4a222e784d38",
            "Default": "https://images.unsplash.com/photo-1542838132-92c53300491e"
        }

        # Track created categories/subcategories to avoid duplicates
        created_categories = {}
        created_subcategories = {}
        product_data = {}  # Track products by name to group variants
        product_count = 0
        variant_count = 0

        for row in rows:
            try:
                # Extract fields from CSV
                product_name = row.get('name', '').strip()
                category_name = row.get('category', '').strip()
                size = row.get('size', '').strip()
                unit = row.get('unit', '').strip()
                price_str = row.get('price', '0').strip()
                market_price_str = row.get('marketPrice', '0').strip()
                purchase_price_str = row.get('purchasePrice', '').strip()
                in_stock = row.get('inStock', 'No').strip().lower() == 'yes'
                is_active = row.get('isActive', 'No').strip().lower() == 'yes'
                description = row.get('description', '').strip()
                photos = row.get('photos', '').strip()
                sku = row.get('sku', '').strip()
                hsn_sac_code = row.get('hsnSacCode', '').strip()
                gst_str = row.get('gst', '0').strip()
                is_coming_soon = row.get('isComingSoon', 'No').strip().lower() == 'yes'
                vegan = row.get('vegan', '').strip()
                brand = row.get('brand', '').strip() or row.get('productBrand', '').strip()

                # Skip rows with missing critical data
                if not product_name or not category_name:
                    continue

                # Parse price
                try:
                    price = int(float(price_str)) if price_str else random.randint(50, 500)
                except ValueError:
                    price = random.randint(50, 500)

                # Parse market price (for MRP)
                try:
                    mrp = int(float(market_price_str)) if market_price_str else int(price * 1.2)
                except ValueError:
                    mrp = int(price * 1.2)

                # Parse purchase price
                try:
                    purchase_price = int(float(purchase_price_str)) if purchase_price_str else int(price * 0.75)
                except ValueError:
                    purchase_price = int(price * 0.75)

                # Create or get main category
                if category_name not in created_categories:
                    cat_slug = category_name.lower().replace(" ", "-").replace("&", "and")
                    cat = Category.objects.create(
                        name=category_name,
                        slug=cat_slug,
                        emoji="🥬",  # Default emoji
                        description=f"Fresh {category_name} sourced directly from farms."
                    )
                    created_categories[category_name] = cat
                cat_obj = created_categories[category_name]

                # Create or get subcategory (use category as subcategory for simplicity)
                sub_key = f"{category_name}_{category_name}"
                if sub_key not in created_subcategories:
                    sub_slug = f"{category_name.lower().replace(' ', '-').replace('&', 'and')}-sub"
                    sub = SubCategory.objects.create(
                        category=cat_obj,
                        name=category_name,
                        slug=sub_slug,
                        emoji="✓"
                    )
                    created_subcategories[sub_key] = sub
                sub_obj = created_subcategories[sub_key]

                # Create or get product (group by product name)
                prod_key = f"{category_name}_{product_name}"
                if prod_key not in product_data:
                    # Dynamic organic impact scores based on category
                    if 'Millet' in category_name or 'Grain' in category_name or 'Rice' in category_name:
                        water = random.uniform(5.0, 15.0)
                        soil = random.uniform(3.0, 6.0)
                        chem = random.uniform(10.0, 25.0)
                        farm = random.uniform(3.0, 7.0)
                    elif 'Dry Fruit' in category_name or 'Nut' in category_name or 'Cashew' in category_name or 'Almond' in category_name:
                        water = random.uniform(15.0, 30.0)
                        soil = random.uniform(1.5, 3.0)
                        chem = random.uniform(8.0, 20.0)
                        farm = random.uniform(4.0, 8.0)
                    elif 'Oil' in category_name:
                        water = random.uniform(25.0, 50.0)
                        soil = random.uniform(1.0, 2.5)
                        chem = random.uniform(0.0, 2.0)
                        farm = random.uniform(5.0, 10.0)
                    elif 'Spice' in category_name or 'Masala' in category_name:
                        water = random.uniform(2.0, 10.0)
                        soil = random.uniform(0.5, 2.0)
                        chem = random.uniform(1.0, 5.0)
                        farm = random.uniform(1.0, 3.0)
                    else:
                        water = random.uniform(2.0, 10.0)
                        soil = random.uniform(0.5, 2.0)
                        chem = random.uniform(1.0, 5.0)
                        farm = random.uniform(1.0, 3.0)

                    # Use description from CSV if available, otherwise generate one
                    prod_description = description if description else f"Premium quality {product_name} from FreshOn.in"
                    
                    prod = Product.objects.create(
                        category=cat_obj,
                        subcategory=sub_obj,
                        name=product_name,
                        description=prod_description,
                        storage_instructions="Store in cool, dry conditions.",
                        water_score=round(water, 2),
                        soil_score=round(soil, 2),
                        chemical_score=round(chem, 2),
                        farmer_score=round(farm, 2)
                    )
                    
                    # Add image link
                    base_img = img_pools.get(category_name, img_pools["Default"])
                    prod.base_image = f"{base_img}?auto=format&fit=crop&q=80&w=600&h=600&sig={product_count}"
                    prod.save()
                    
                    # Add benefits based on product attributes
                    benefits = ["Farm to Table"]
                    if vegan.lower() == 'veg':
                        benefits.append("100% Vegetarian")
                    if 'organic' in product_name.lower() or 'natural' in product_name.lower():
                        benefits.append("Organic")
                    if 'cold pressed' in product_name.lower():
                        benefits.append("Cold Pressed")
                    
                    for benefit in benefits:
                        ProductBenefit.objects.create(product=prod, benefit=benefit)
                    
                    product_data[prod_key] = prod
                    product_count += 1
                else:
                    prod = product_data[prod_key]

                # Create variant for this size/unit combination
                variant_unit = f"{size} {unit}".strip() if size and unit else (size or unit or "1 unit")
                
                variant, created = ProductVariant.objects.get_or_create(
                    product=prod,
                    unit=variant_unit,
                    defaults={
                        "price": price,
                        "mrp": mrp,
                        "is_active": is_active and not is_coming_soon
                    }
                )
                
                if created:
                    # Create inventory batch for this variant
                    stock_level = random.randint(10, 500) if in_stock else 0
                    InventoryBatch.objects.create(
                        farmer=random.choice(farmer_profiles),
                        variant=variant,
                        purchase_price=purchase_price,
                        stock_level=stock_level,
                        harvest_date=timezone.now() - timezone.timedelta(days=random.randint(0, 7)),
                        is_organic='organic' in product_name.lower() or 'natural' in product_name.lower(),
                        is_farm_fresh=True
                    )
                    variant_count += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Skipping row due to error: {e}"))
                continue

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded {product_count} unique products from Products.csv with {variant_count} variants and {InventoryBatch.objects.count()} inventory batches!"
        ))
        return True

    def seed_fallback_data(self):
        """Seed fallback dummy data when CSV is not available"""
        self.stdout.write("Seeding fallback 20+ Categories and Sub-categories...")
        
        data_structure = {
            "Vegetables": {
                "emoji": "🥕",
                "subs": [
                    {"name": "Root Vegetables", "emoji": "🥔"},
                    {"name": "Leafy Greens", "emoji": "🥬"},
                    {"name": "Cruciferous", "emoji": "🥦"},
                    {"name": "Marrows", "emoji": "🥒"},
                    {"name": "Allium", "emoji": "🧅"},
                    {"name": "Nightshades", "emoji": "🍅"}
                ]
            },
            "Fruits": {
                "emoji": "🍎",
                "subs": [
                    {"name": "Stone Fruits", "emoji": "🍑"},
                    {"name": "Citrus", "emoji": "🍊"},
                    {"name": "Berries", "emoji": "🍓"},
                    {"name": "Tropical", "emoji": "🥭"},
                    {"name": "Melons", "emoji": "🍉"},
                    {"name": "Apples & Pears", "emoji": "🍏"}
                ]
            },
            "Dairy & Eggs": {
                "emoji": "🥛",
                "subs": [
                    {"name": "Milk", "emoji": "🥛"},
                    {"name": "Cheese", "emoji": "🧀"},
                    {"name": "Yogurt", "emoji": "🍦"},
                    {"name": "Butter & Ghee", "emoji": "🧈"},
                    {"name": "Eggs", "emoji": "🥚"}
                ]
            },
            "Grains & Rice": {
                "emoji": "🌾",
                "subs": [
                    {"name": "Basmati Rice", "emoji": "🍚"},
                    {"name": "Whole Grains", "emoji": "🌾"},
                    {"name": "Millets", "emoji": "🥣"},
                    {"name": "Quinoa", "emoji": "🍲"}
                ]
            },
            "Pulses & Dals": {
                "emoji": "🍲",
                "subs": [
                    {"name": "Yellow Dal", "emoji": "🥣"},
                    {"name": "Red Lentils", "emoji": "🥘"},
                    {"name": "Chickpeas", "emoji": "🍢"},
                    {"name": "Kidney Beans", "emoji": "🍲"}
                ]
            },
            "Spices & Masala": {
                "emoji": "🌶️",
                "subs": [
                    {"name": "Whole Spices", "emoji": "🧂"},
                    {"name": "Powdered Spices", "emoji": "🥘"},
                    {"name": "Blended Masalas", "emoji": "🍲"}
                ]
            },
            "Oils & Ghee": {
                "emoji": "🫗",
                "subs": [
                    {"name": "Cold Pressed Oils", "emoji": "🌻"},
                    {"name": "Pure Ghee", "emoji": "🧈"},
                    {"name": "Olive Oils", "emoji": "🫒"}
                ]
            },
            "Nuts & Seeds": {
                "emoji": "🥜",
                "subs": [
                    {"name": "Almonds & Cashews", "emoji": "🥜"},
                    {"name": "Walnuts", "emoji": "🥥"},
                    {"name": "Seeds", "emoji": "🌻"}
                ]
            },
            "Flour & Atta": {
                "emoji": "🍞",
                "subs": [
                    {"name": "Wheat Atta", "emoji": "🌾"},
                    {"name": "Multigrain", "emoji": "🍞"},
                    {"name": "Speciality Flour", "emoji": "🥣"}
                ]
            },
            "Beverages": {
                "emoji": "☕",
                "subs": [
                    {"name": "Tea", "emoji": "☕"},
                    {"name": "Coffee", "emoji": "🍵"},
                    {"name": "Fruit Juices", "emoji": "🍹"},
                    {"name": "Coconut Water", "emoji": "🥥"}
                ]
            },
            "Bakery": {
                "emoji": "🥖",
                "subs": [
                    {"name": "Fresh Breads", "emoji": "🍞"},
                    {"name": "Cakes", "emoji": "🍰"},
                    {"name": "Cookies", "emoji": "🍪"}
                ]
            },
            "Herbs & Seasoning": {
                "emoji": "🌿",
                "subs": [
                    {"name": "Fresh Herbs", "emoji": "🌿"},
                    {"name": "Dried Herbs", "emoji": "🌱"},
                    {"name": "Garnish", "emoji": "🍀"}
                ]
            },
            "Exotic Produce": {
                "emoji": "🍍",
                "subs": [
                    {"name": "Imported Fruits", "emoji": "🥑"},
                    {"name": "Hydroponic Salad", "emoji": "🥗"}
                ]
            },
            "Honey & Jams": {
                "emoji": "🍯",
                "subs": [
                    {"name": "Raw Honey", "emoji": "🍯"},
                    {"name": "Fruit Preserves", "emoji": "🍓"}
                ]
            },
            "Snacks": {
                "emoji": "🥨",
                "subs": [
                    {"name": "Traditional Namkeen", "emoji": "🥟"},
                    {"name": "Roasted Snacks", "emoji": "🍿"}
                ]
            },
            "Organic Specials": {
                "emoji": "🌿",
                "subs": [
                    {"name": "Certified Organic", "emoji": "🍃"},
                    {"name": "Natural Sweets", "emoji": "🍬"}
                ]
            },
            "Kitchen Staples": {
                "emoji": "🧂",
                "subs": [
                    {"name": "Salt & Sugar", "emoji": "🧂"},
                    {"name": "Vinegars", "emoji": "🍾"}
                ]
            },
            "Breakfast": {
                "emoji": "🥣",
                "subs": [
                    {"name": "Oats & Muesli", "emoji": "🥣"},
                    {"name": "Pancake Mix", "emoji": "🥞"}
                ]
            },
            "Flowers": {
                "emoji": "🌸",
                "subs": [
                    {"name": "Fresh Cut Flowers", "emoji": "🌹"},
                    {"name": "Pooja Flowers", "emoji": "🌼"}
                ]
            },
            "Microgreens": {
                "emoji": "🌱",
                "subs": [
                    {"name": "Sprouts", "emoji": "🌱"},
                    {"name": "Shoots", "emoji": "🌿"}
                ]
            },
            "Pooja Essentials": {
                "emoji": "🪔",
                "subs": [
                    {"name": "Incense", "emoji": "🕯️"},
                    {"name": "Oils & Wicks", "emoji": "🪔"}
                ]
            }
        }

        created_categories = {}
        created_subcategories = {}

        for cat_name, cat_data in data_structure.items():
            cat = Category.objects.create(
                name=cat_name,
                slug=cat_name.lower().replace(" ", "-").replace("&", "and"),
                emoji=cat_data["emoji"],
                description=f"Fresh {cat_name} sourced directly from farms."
            )
            created_categories[cat_name] = cat
            for sub in cat_data["subs"]:
                s = SubCategory.objects.create(
                    category=cat,
                    name=sub["name"],
                    slug=sub["name"].lower().replace(" ", "-").replace("&", "and"),
                    emoji=sub["emoji"]
                )
                created_subcategories[f"{cat_name}_{sub['name']}"] = s

        farmer_profiles = self.create_users()

        self.stdout.write("Seeding 200+ Products with variants...")
        
        # Image pools for variety
        img_pools = {
            "Vegetables": "https://images.unsplash.com/photo-1597362925123-77861d3fbac7",
            "Fruits": "https://images.unsplash.com/photo-1610832958506-aa56368176cf",
            "Dairy & Eggs": "https://images.unsplash.com/photo-1628088062854-d1870b4553ad",
            "Grains & Rice": "https://images.unsplash.com/photo-1586201375761-83865001e31c",
            "Pulses & Dals": "https://images.unsplash.com/photo-1585994192701-97061730872c",
            "Spices & Masala": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d",
            "Oils & Ghee": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5",
            "Nuts & Seeds": "https://images.unsplash.com/photo-1536591030366-f76f74296482",
            "Flours & Atta": "https://images.unsplash.com/photo-1509440159596-0249088772ff",
            "Beverages": "https://images.unsplash.com/photo-1544787210-2211d7c00676",
            "Bakery": "https://images.unsplash.com/photo-1509440159596-0249088772ff",
            "Herbs & Seasoning": "https://images.unsplash.com/photo-1506477331477-33d6d8b3dc85",
            "Exotic Produce": "https://images.unsplash.com/photo-1601004890684-d8cbf643f5f2",
            "Honey & Jams": "https://images.unsplash.com/photo-1587049352846-4a222e784d38",
            "Snacks": "https://images.unsplash.com/photo-1599490659213-e2b9527bb087",
            "Flowers": "https://images.unsplash.com/photo-1526047932273-341f2a7631f9",
            "Microgreens": "https://images.unsplash.com/photo-1592752547487-526421886134",
            "Pooja Essentials": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a",
            "Default": "https://images.unsplash.com/photo-1542838132-92c53300491e"
        }

        product_count = 0
        units_options = [
            [("250 g", 1.0), ("500 g", 1.8), ("1 kg", 3.2)],
            [("1 pc", 1.0), ("Pack of 3", 2.5), ("Pack of 6", 4.5)],
            [("500 ml", 1.0), ("1 L", 1.9), ("2 L", 3.6)],
            [("100 g", 1.0), ("200 g", 1.8)],
            [("1 dozen", 1.0), ("Half dozen", 0.6)]
        ]

        # Algorithmically generate products to ensure 200+
        for cat_name, cat_data in data_structure.items():
            cat_obj = created_categories[cat_name]
            for sub in cat_data["subs"]:
                sub_obj = created_subcategories[f"{cat_name}_{sub['name']}"]
                
                # Create 3-5 products per subcategory
                for i in range(random.randint(3, 5)):
                    p_name = f"{sub['name']} Item {i+1}"
                    # Try to make names more realistic for some common ones
                    if "Tomato" in sub['name']: p_name = ["Cherry Tomatoes", "Roma Tomatoes", "Local Tomatoes"][i%3]
                    elif "Milk" in sub['name']: p_name = ["Cow Milk", "Buffalo Milk", "A2 Desi Milk"][i%3]
                    elif "Rice" in sub['name']: p_name = ["Sona Masuri", "Kolam Rice", "Brown Rice"][i%3]
                    
                    # Dynamic organic impact scores based on category
                    if cat_name == "Vegetables":
                        water = random.uniform(10.0, 20.0)
                        soil = random.uniform(2.0, 4.0)
                        chem = random.uniform(5.0, 15.0)
                        farm = random.uniform(3.0, 6.0)
                    elif cat_name == "Fruits":
                        water = random.uniform(15.0, 30.0)
                        soil = random.uniform(1.5, 3.0)
                        chem = random.uniform(8.0, 20.0)
                        farm = random.uniform(4.0, 8.0)
                    elif cat_name == "Dairy & Eggs":
                        water = random.uniform(25.0, 50.0)
                        soil = random.uniform(1.0, 2.5)
                        chem = random.uniform(0.0, 2.0)
                        farm = random.uniform(5.0, 10.0)
                    elif "Grain" in cat_name or "Pulse" in cat_name:
                        water = random.uniform(5.0, 15.0)
                        soil = random.uniform(3.0, 6.0)
                        chem = random.uniform(10.0, 25.0)
                        farm = random.uniform(3.0, 7.0)
                    else:
                        water = random.uniform(2.0, 10.0)
                        soil = random.uniform(0.5, 2.0)
                        chem = random.uniform(1.0, 5.0)
                        farm = random.uniform(1.0, 3.0)

                    prod = Product.objects.create(
                        category=cat_obj,
                        subcategory=sub_obj,
                        name=p_name,
                        description=f"Premium quality {p_name} harvested fresh for your kitchen.",
                        storage_instructions="Store in cool, dry conditions.",
                        water_score=round(water, 2),
                        soil_score=round(soil, 2),
                        chemical_score=round(chem, 2),
                        farmer_score=round(farm, 2)
                    )
                    
                    # Add image link (hack for ImageField)
                    base_img = img_pools.get(cat_name, img_pools["Default"])
                    prod.base_image = f"{base_img}?auto=format&fit=crop&q=80&w=600&h=600&sig={product_count}"
                    prod.save()

                    # Add variants
                    variant_set = random.choice(units_options)
                    base_price = random.randint(20, 150)
                    for unit_name, multiplier in variant_set:
                        price = int(base_price * multiplier)
                        mrp = int(price * 1.2)
                        v = ProductVariant.objects.create(
                            product=prod,
                            unit=unit_name,
                            price=price,
                            mrp=mrp,
                            is_active=True
                        )
                        
                        # Create Batch
                        InventoryBatch.objects.create(
                            farmer=random.choice(farmer_profiles),
                            variant=v,
                            purchase_price=int(price * 0.75),
                            stock_level=random.randint(5, 100),
                            harvest_date=timezone.now() - timezone.timedelta(days=random.randint(0, 3)),
                            is_organic=random.choice([True, False]),
                            is_farm_fresh=True
                        )
                    
                    # Add benefits
                    ProductBenefit.objects.create(product=prod, benefit="Farm to Table")
                    ProductBenefit.objects.create(product=prod, benefit="No Preservatives")
                    
                    product_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {product_count} products across {len(data_structure)} categories!"))
