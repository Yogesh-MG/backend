from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count

from .models import Category, SubCategory, Product, InventoryBatch
from .serializers import (
    CategoryListSerializer,
    CategoryDetailSerializer,
    SubCategoryDetailSerializer,
    ProductSerializer,
    InventoryBatchSerializer,
    FarmerSerializer,
)
from .filters import InventoryBatchFilter
from apps.accounts.models import FarmerProfile


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class StandardPagination(PageNumberPagination):
    """Default pagination for list endpoints returning many rows."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ---------------------------------------------------------------------------
# Category  (Lazy-load pattern)
# ---------------------------------------------------------------------------

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /categories/           → lightweight list (no nested subcategories)
    GET /categories/{slug}/    → full detail (with subcategories array)
    GET /categories/{slug}/subcategories/  → subcategories only
    """
    lookup_field = 'slug'
    pagination_class = StandardPagination

    def get_queryset(self):
        # Annotate subcategory_count for the list serializer
        return Category.objects.annotate(
            subcategory_count=Count('subcategories')
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return CategoryListSerializer
        return CategoryDetailSerializer

    @action(detail=True, methods=['get'], url_path='subcategories')
    def subcategories(self, request, slug=None):
        """
        GET /categories/{slug}/subcategories/
        Returns subcategories for a specific category.
        """
        category = self.get_object()
        subs = SubCategory.objects.filter(category=category).select_related('category')
        serializer = SubCategoryDetailSerializer(subs, many=True)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Products  (paginated)
# ---------------------------------------------------------------------------

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.select_related(
        'category', 'subcategory'
    ).prefetch_related('variants', 'benefits')
    serializer_class = ProductSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category__slug', 'category']
    search_fields = ['name', 'description']


# ---------------------------------------------------------------------------
# Inventory Batches  (paginated, deep select_related)
# ---------------------------------------------------------------------------

class InventoryBatchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Main endpoint for the app's catalog.
    Shows available batches of products from different farmers.
    Paginated to avoid large payloads.
    """
    queryset = InventoryBatch.objects.filter(stock_level__gt=0).select_related(
        'variant', 'variant__product', 'variant__product__category',
        'variant__product__subcategory', 'farmer', 'farmer__user'
    ).prefetch_related('variant__product__benefits')
    serializer_class = InventoryBatchSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = InventoryBatchFilter
    search_fields = ['variant__product__name', 'farmer__user__username']


# ---------------------------------------------------------------------------
# Farmers  (paginated)
# ---------------------------------------------------------------------------

class FarmerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FarmerProfile.objects.all().select_related('user')
    serializer_class = FarmerSerializer
    pagination_class = StandardPagination
