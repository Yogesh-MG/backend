from django.contrib import admin
from .models import Product, Category, SubCategory, InventoryBatch, ProductBenefit, ProductVariant, ProductImage

# Register your models here.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('emoji', 'name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'slug')
    list_filter = ('category',)
    prepopulated_fields = {'slug': ('name',)}

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

class ProductBenefitInline(admin.TabularInline):
    model = ProductBenefit
    extra = 1


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'order']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'subcategory')
    list_filter = ('category', 'subcategory')
    search_fields = ('name',)
    inlines = [ProductVariantInline, ProductBenefitInline, ProductImageInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'alt_text', 'order', 'created_at')
    list_filter = ('product__category',)
    search_fields = ('product__name', 'alt_text')
    ordering = ['product', 'order', 'created_at']

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'unit', 'price', 'mrp', 'is_active')
    list_filter = ('is_active', 'unit')
    search_fields = ('product__name', 'unit')

@admin.register(InventoryBatch)
class InventoryBatchAdmin(admin.ModelAdmin):
    list_display = ('variant', 'farmer', 'stock_level', 'purchase_price', 'get_retail_price', 'harvest_date')
    list_filter = ('is_organic', 'is_farm_fresh', 'harvest_date')
    search_fields = ('variant__product__name', 'farmer__user__username')

    def get_retail_price(self, obj):
        return obj.variant.price
    get_retail_price.short_description = "Retail Price"

@admin.register(ProductBenefit)
class ProductBenefitAdmin(admin.ModelAdmin):
    list_display = ('product', 'benefit')
