from django_filters import rest_framework as filters
from .models import InventoryBatch

class InventoryBatchFilter(filters.FilterSet):
    category = filters.CharFilter(field_name='variant__product__category')
    category_slug = filters.CharFilter(field_name='variant__product__category__slug')
    subcategory = filters.CharFilter(field_name='variant__product__subcategory')
    
    class Meta:
        model = InventoryBatch
        fields = ['category', 'category_slug', 'subcategory', 'is_organic', 'is_farm_fresh', 'farmer']
