from rest_framework import serializers
from apps.accounts.models import FarmerProfile, User
from .models import Category, SubCategory, Product, InventoryBatch, ProductBenefit, ProductVariant

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

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'unit', 'is_active']

class ProductSerializer(serializers.ModelSerializer):
    benefits = serializers.SlugRelatedField(many=True, read_only=True, slug_field='benefit')
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'storage_instructions', 
            'base_image', 'category', 'category_name', 
            'subcategory', 'subcategory_name', 'benefits', 'variants'
        ]

class InventoryBatchSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    product_id = serializers.IntegerField(source='variant.product.id', read_only=True)
    category_name = serializers.CharField(source='variant.product.category.name', read_only=True)
    category_slug = serializers.CharField(source='variant.product.category.slug', read_only=True)
    description = serializers.CharField(source='variant.product.description', read_only=True)
    base_image = serializers.ImageField(source='variant.product.base_image', read_only=True)
    farmer = FarmerSerializer(read_only=True)
    harvest_date_display = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryBatch
        fields = [
            'id', 'farmer', 'variant', 'product_name', 'product_id', 
            'category_name', 'category_slug', 'description', 'base_image',
            'price', 'mrp', 'stock_level', 'harvest_date', 
            'harvest_date_display', 'is_organic', 'is_farm_fresh', 'batch_image'
        ]

    def get_harvest_date_display(self, obj):
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.harvest_date
        
        if diff.days == 0:
            return f"Today, {obj.harvest_date.strftime('%I:%M %p')}"
        elif diff.days == 1:
            return "Yesterday"
        else:
            return f"{diff.days} days ago"
