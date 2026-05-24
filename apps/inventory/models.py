from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    emoji = models.CharField(max_length=10, help_text="Emoji icon for the UI")
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.emoji} {self.name}"

class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    emoji = models.CharField(max_length=10, blank=True, help_text="Optional emoji icon")

    class Meta:
        verbose_name_plural = "Sub-Categories"

    def __str__(self):
        return f"{self.category.name} > {self.name}"

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField()
    storage_instructions = models.TextField(help_text="Storage tips for customers")
    base_image = models.ImageField(upload_to='products/', null=True, blank=True)
    is_perishable = models.BooleanField(default=True, help_text="Whether this product shows harvest date (e.g., vegetables, fruits) or not (e.g., pots, household items)")
    
    # Impact scores (Organic Impact Tracker)
    water_score = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Water saved/protected in litres per unit")
    soil_score = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Soil supported in sq.ft per unit")
    chemical_score = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Harmful chemicals reduced in grams per unit")
    farmer_score = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Farmer support score per unit")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    unit = models.CharField(max_length=50, help_text="e.g. 500 g, 1 kg, 1 dozen")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Selling price for this variant")
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="MRP for this variant")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Product Variants"
        unique_together = ('product', 'unit')

    def __str__(self):
        return f"{self.product.name} ({self.unit}) - ₹{self.price}"

class InventoryBatch(models.Model):
    farmer = models.ForeignKey('accounts.FarmerProfile', on_delete=models.CASCADE, related_name='inventory_batches')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='batches')
    
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price FreshOn pays to the farmer")
    stock_level = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    
    harvest_date = models.DateTimeField()
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    is_organic = models.BooleanField(default=False)
    is_farm_fresh = models.BooleanField(default=True)
    
    # Approval workflow - new batches start as pending
    is_approved = models.BooleanField(default=False, help_text="Approved by admin for listing")
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_batches')
    
    batch_image = models.ImageField(upload_to='batches/', null=True, blank=True, help_text="Optional batch-specific image")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Inventory Batches"
        ordering = ['-harvest_date']

    def __str__(self):
        return f"{self.variant} - {self.farmer.user.username} ({self.stock_level} available)"

class ProductBenefit(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='benefits')
    benefit = models.CharField(max_length=255)

    def __str__(self):
        return self.benefit


class ProductImage(models.Model):
    """Additional images for a product."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')
    alt_text = models.CharField(max_length=255, blank=True, help_text="Alt text for accessibility")
    order = models.PositiveIntegerField(default=0, help_text="Display order (0 = first)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name_plural = "Product Images"

    def __str__(self):
        return f"{self.product.name} - Image {self.order + 1}"
