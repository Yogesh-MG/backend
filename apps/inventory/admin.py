from django.contrib import admin
from .models import Product, Category, SubCategory, InventoryBatch, ProductBenefit

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

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'subcategory', 'unit')
    list_filter = ('category', 'subcategory')
    search_fields = ('name',)

@admin.register(InventoryBatch)
class InventoryBatchAdmin(admin.ModelAdmin):
    list_display = ('product', 'farmer', 'stock_level', 'price', 'harvest_date')
    list_filter = ('is_organic', 'is_farm_fresh', 'harvest_date')
    search_fields = ('product__name', 'farmer__user__username')

@admin.register(ProductBenefit)
class ProductBenefitAdmin(admin.ModelAdmin):
    list_display = ('product', 'benefit')