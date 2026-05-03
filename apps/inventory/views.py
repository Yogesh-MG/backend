from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Product, InventoryBatch
from .serializers import CategorySerializer, ProductSerializer, InventoryBatchSerializer, FarmerSerializer
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
    queryset = InventoryBatch.objects.filter(stock_level__gt=0).select_related('product', 'farmer', 'farmer__user', 'product__category')
    serializer_class = InventoryBatchSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['product__category__slug', 'product__category', 'product__subcategory', 'is_organic', 'is_farm_fresh', 'farmer']
    search_fields = ['product__name', 'farmer__user__username']

class FarmerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FarmerProfile.objects.all().select_related('user')
    serializer_class = FarmerSerializer
