from rest_framework import serializers
from apps.accounts.models import FarmerProfile, User
from .models import Category, SubCategory, Product, InventoryBatch, ProductBenefit, ProductVariant, ProductImage

class FarmerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.get_full_name')
    username = serializers.CharField(source='user.username')
    
    class Meta:
        model = FarmerProfile
        fields = ['id', 'username', 'name', 'location', 'image', 'years_of_experience', 'rating', 'speciality', 'bio']

class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ['id', 'slug', 'name', 'emoji']

class SubCategoryDetailSerializer(serializers.ModelSerializer):
    """Includes parent category_id for breadcrumb / back-navigation."""
    category_id = serializers.IntegerField(source='category.id', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = SubCategory
        fields = ['id', 'slug', 'name', 'emoji', 'category_id', 'category_name']

class CategoryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the list endpoint — no nested subcategories."""
    subcategory_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'slug', 'name', 'emoji', 'description', 'subcategory_count']

class CategoryDetailSerializer(serializers.ModelSerializer):
    """Full serializer for the detail / retrieve endpoint."""
    subcategories = SubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'slug', 'name', 'emoji', 'description', 'subcategories']

class BenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductBenefit
        fields = ['benefit']


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product gallery images."""
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'order']

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'unit', 'price', 'mrp', 'is_active']

class ProductSerializer(serializers.ModelSerializer):
    benefits = serializers.SlugRelatedField(many=True, read_only=True, slug_field='benefit')
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    all_images = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'storage_instructions', 
            'base_image', 'category', 'category_name', 
            'subcategory', 'subcategory_name', 'benefits', 'variants',
            'images', 'all_images'
        ]
    
    def get_all_images(self, obj):
        """Return all images including base_image as the first one."""
        images = []
        # Add base_image first if it exists
        if obj.base_image:
            request = self.context.get('request')
            if request:
                images.append({
                    'id': 'base',
                    'image': request.build_absolute_uri(obj.base_image.url),
                    'alt_text': obj.name,
                    'order': 0,
                    'is_base': True
                })
            else:
                images.append({
                    'id': 'base',
                    'image': obj.base_image.url,
                    'alt_text': obj.name,
                    'order': 0,
                    'is_base': True
                })
        # Add gallery images
        for img in obj.images.all():
            request = self.context.get('request')
            image_url = request.build_absolute_uri(img.image.url) if request else img.image.url
            images.append({
                'id': img.id,
                'image': image_url,
                'alt_text': img.alt_text or obj.name,
                'order': img.order + 1,  # +1 to ensure base_image is first
                'is_base': False
            })
        return sorted(images, key=lambda x: x['order'])

class InventoryBatchSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    product_id = serializers.IntegerField(source='variant.product.id', read_only=True)
    category_name = serializers.CharField(source='variant.product.category.name', read_only=True)
    category_slug = serializers.CharField(source='variant.product.category.slug', read_only=True)
    description = serializers.CharField(source='variant.product.description', read_only=True)
    base_image = serializers.ImageField(source='variant.product.base_image', read_only=True)
    all_images = serializers.SerializerMethodField()
    farmer = FarmerSerializer(read_only=True)
    harvest_date_display = serializers.SerializerMethodField()
    is_perishable = serializers.BooleanField(source='variant.product.is_perishable', read_only=True)
    price = serializers.DecimalField(source='variant.price', max_digits=10, decimal_places=2, read_only=True)
    mrp = serializers.DecimalField(source='variant.mrp', max_digits=10, decimal_places=2, read_only=True)
    benefits = serializers.SlugRelatedField(
        source='variant.product.benefits',
        many=True,
        read_only=True,
        slug_field='benefit'
    )
    storage_instructions = serializers.CharField(source='variant.product.storage_instructions', read_only=True)
    
    class Meta:
        model = InventoryBatch
        fields = [
            'id', 'farmer', 'variant', 'product_name', 'product_id', 
            'category_name', 'category_slug', 'description', 'base_image',
            'all_images', 'price', 'mrp', 'stock_level', 'harvest_date', 
            'harvest_date_display', 'is_organic', 'is_farm_fresh', 'batch_image',
            'is_perishable', 'benefits', 'storage_instructions'
        ]
    
    def get_all_images(self, obj):
        """Return all images for the product including base_image and gallery."""
        product = obj.variant.product
        images = []
        request = self.context.get('request')
        
        # Add base_image first if it exists
        if product.base_image:
            image_url = request.build_absolute_uri(product.base_image.url) if request else product.base_image.url
            images.append({
                'id': 'base',
                'image': image_url,
                'alt_text': product.name,
                'order': 0,
                'is_base': True
            })
        
        # Add gallery images
        for img in product.images.all():
            image_url = request.build_absolute_uri(img.image.url) if request else img.image.url
            images.append({
                'id': img.id,
                'image': image_url,
                'alt_text': img.alt_text or product.name,
                'order': img.order + 1,
                'is_base': False
            })
        
        return sorted(images, key=lambda x: x['order'])

    def get_harvest_date_display(self, obj):
        # Return None for non-perishable products (pots, household items, etc.)
        if not obj.variant.product.is_perishable:
            return None
            
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.harvest_date
        
        if diff.days == 0:
            return f"Today, {obj.harvest_date.strftime('%I:%M %p')}"
        elif diff.days == 1:
            return "Yesterday"
        else:
            return f"{diff.days} days ago"
