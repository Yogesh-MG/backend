import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User, FarmerProfile
from apps.inventory.models import Category, SubCategory, Product, InventoryBatch, ProductBenefit

class Command(BaseCommand):
    help = 'Seeds the database with initial Freshon.in data'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding data...")

        # 1. Create Categories
        cats_data = [
            {"name": "Fruits", "slug": "fruits", "emoji": "🍎"},
            {"name": "Vegetables", "slug": "vegetables", "emoji": "🥕"},
            {"name": "Dairy", "slug": "dairy", "emoji": "🥛"},
            {"name": "Grains", "slug": "grains", "emoji": "🌾"},
            {"name": "Organic", "slug": "organic", "emoji": "🌿"},
            {"name": "Herbs", "slug": "herbs", "emoji": "🌱"},
        ]
        categories = {}
        for c in cats_data:
            cat, _ = Category.objects.get_or_create(slug=c['slug'], defaults=c)
            categories[c['slug']] = cat

        # 1.5. Create SubCategories
        sub_cats_data = [
            {"cat": "vegetables", "name": "Leafy Greens", "slug": "leafy-greens", "emoji": "🥬"},
            {"cat": "vegetables", "name": "Root Vegetables", "slug": "root-vegetables", "emoji": "🥕"},
            {"cat": "fruits", "name": "Stone Fruits", "slug": "stone-fruits", "emoji": "🍑"},
            {"cat": "dairy", "name": "Milk", "slug": "milk", "emoji": "🥛"},
            {"cat": "dairy", "name": "Eggs", "slug": "eggs", "emoji": "🥚"},
        ]
        subcategories = {}
        for s in sub_cats_data:
            sub_cat, _ = SubCategory.objects.get_or_create(
                slug=s['slug'], 
                defaults={
                    "category": categories[s['cat']],
                    "name": s['name'],
                    "emoji": s['emoji']
                }
            )
            subcategories[s['slug']] = sub_cat

        # 2. Create Farmers
        farmers_data = [
            {"username": "lakshmi_devi", "name": "Lakshmi Devi", "location": "Mysuru, Karnataka", "years": 18, "speciality": "Leafy greens & herbs"},
            {"username": "ramesh_patil", "name": "Ramesh Patil", "location": "Nashik, Maharashtra", "years": 22, "speciality": "Heirloom tomatoes"},
            {"username": "anita_sharma", "name": "Anita Sharma", "location": "Mahabaleshwar, MH", "years": 9, "speciality": "Berries & soft fruit"},
        ]
        farmer_profiles = []
        for f in farmers_data:
            user, created = User.objects.get_or_create(
                username=f['username'],
                defaults={"email": f"{f['username']}@example.com", "role": User.Role.FARMER}
            )
            if created:
                user.set_password("freshon123")
                user.save()
            
            profile, _ = FarmerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "location": f['location'],
                    "years_of_experience": f['years'],
                    "speciality": f['speciality'],
                    "rating": random.uniform(4.5, 5.0)
                }
            )
            farmer_profiles.append(profile)

        # 3. Create Products
        products_data = [
            {"name": "Vine Tomatoes", "unit": "500 g", "cat": "vegetables", "sub": "root-vegetables", "desc": "Sun-ripened heirloom tomatoes."},
            {"name": "Baby Spinach", "unit": "250 g", "cat": "vegetables", "sub": "leafy-greens", "desc": "Tender baby spinach leaves."},
            {"name": "Organic Carrots", "unit": "500 g", "cat": "vegetables", "sub": "root-vegetables", "desc": "Crisp, naturally sweet carrots."},
            {"name": "Royal Gala Apples", "unit": "1 kg", "cat": "fruits", "sub": "stone-fruits", "desc": "Crisp, juicy apples."},
            {"name": "Farm Fresh Milk", "unit": "1 L", "cat": "dairy", "sub": "milk", "desc": "A2 milk from grass-fed cows."},
        ]
        for p in products_data:
            prod, _ = Product.objects.get_or_create(
                name=p['name'],
                defaults={
                    "category": categories[p['cat']],
                    "subcategory": subcategories[p['sub']] if 'sub' in p else None,
                    "description": p['desc'],
                    "storage_instructions": "Store in a cool, dry place."
                }
            )
            
            # Create variant
            variant, _ = ProductVariant.objects.get_or_create(
                product=prod,
                unit=p['unit'],
                defaults={"is_active": True}
            )
            
            # Add benefits
            ProductBenefit.objects.get_or_create(product=prod, benefit="Rich in vitamins")
            ProductBenefit.objects.get_or_create(product=prod, benefit="100% Chemical free")

            # 4. Create Batches (Live Inventory)
            InventoryBatch.objects.get_or_create(
                farmer=random.choice(farmer_profiles),
                variant=variant,
                defaults={
                    "price": random.randint(30, 200),
                    "mrp": random.randint(220, 260),
                    "stock_level": random.randint(10, 50),
                    "harvest_date": timezone.now() - timezone.timedelta(hours=random.randint(1, 12)),
                    "is_organic": True,
                    "is_farm_fresh": True
                }
            )

        self.stdout.write(self.style.SUCCESS("Successfully seeded Freshon OS database!"))
