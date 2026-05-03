from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Product, InventoryBatch
from .serializers import CategorySerializer, ProductSerializer, InventoryBatchSerializer, FarmerSerializer
from .filters import InventoryBatchFilter
from apps.accounts.models import FarmerProfile

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category__slug', 'category']
    search_fields = ['name', 'description']

class InventoryBatchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Main endpoint for the app's catalog. 
    Shows available batches of products from different farmers.
    """
    queryset = InventoryBatch.objects.filter(stock_level__gt=0).select_related(
        'variant__product', 'variant__product__category', 'farmer', 'farmer__user'
    )
    serializer_class = InventoryBatchSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = InventoryBatchFilter
    search_fields = ['variant__product__name', 'farmer__user__username']

class FarmerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FarmerProfile.objects.all().select_related('user')
    serializer_class = FarmerSerializer
