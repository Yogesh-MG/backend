import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User, FarmerProfile
from apps.inventory.models import Category, SubCategory, Product, InventoryBatch, ProductBenefit, ProductVariant

class Command(BaseCommand):
    help = 'Seeds the database with 20+ categories and 200+ products'

    def handle(self, *args, **kwargs):
        self.stdout.write("Cleaning old data...")
        InventoryBatch.objects.all().delete()
        ProductVariant.objects.all().delete()
        ProductBenefit.objects.all().delete()
        Product.objects.all().delete()
        SubCategory.objects.all().delete()
        Category.objects.all().delete()

        self.stdout.write("Seeding 20+ Categories and Sub-categories...")
        
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

        self.stdout.write("Creating Farmers...")
        farmers_data = [
            {"username": "lakshmi", "name": "Lakshmi Devi", "loc": "Mysuru"},
            {"username": "ramesh", "name": "Ramesh Patil", "loc": "Nashik"},
            {"username": "anita", "name": "Anita Sharma", "loc": "Mahabaleshwar"},
            {"username": "gurpreet", "name": "Gurpreet Singh", "loc": "Amritsar"},
            {"username": "venkat", "name": "Venkat Raman", "loc": "Salem"},
        ]
        farmer_profiles = []
        for f in farmers_data:
            user, _ = User.objects.get_or_create(username=f['username'], defaults={"role": User.Role.FARMER})
            user.set_password("freshon123")
            user.save()
            profile, _ = FarmerProfile.objects.get_or_create(user=user, defaults={"location": f['loc'], "rating": 4.9})
            farmer_profiles.append(profile)

        self.stdout.write("Seeding 200+ Products with variants...")
        
        # Image pools for variety
        img_pools = {
            "Vegetables": "https://images.unsplash.com/photo-1566385101042-1a0aa0c12e8c",
            "Fruits": "https://images.unsplash.com/photo-1619566639371-106497061938",
            "Dairy": "https://images.unsplash.com/photo-1550583724-125581cc2532",
            "Grains": "https://images.unsplash.com/photo-1586201375761-83865001e31c",
            "Spices": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d",
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
                    
                    prod = Product.objects.create(
                        category=cat_obj,
                        subcategory=sub_obj,
                        name=p_name,
                        description=f"Premium quality {p_name} harvested fresh for your kitchen.",
                        storage_instructions="Store in cool, dry conditions.",
                    )
                    
                    # Add image link (hack for ImageField)
                    base_img = img_pools.get(cat_name.split()[0], img_pools["Default"])
                    prod.base_image = f"{base_img}?auto=format&fit=crop&q=80&w=400&h=400&sig={product_count}"
                    prod.save()

                    # Add variants
                    variant_set = random.choice(units_options)
                    base_price = random.randint(20, 150)
                    for unit_name, multiplier in variant_set:
                        price = int(base_price * multiplier)
                        v = ProductVariant.objects.create(
                            product=prod,
                            unit=unit_name,
                            is_active=True
                        )
                        
                        # Create Batch
                        InventoryBatch.objects.create(
                            farmer=random.choice(farmer_profiles),
                            variant=v,
                            price=price,
                            mrp=int(price * 1.2),
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
