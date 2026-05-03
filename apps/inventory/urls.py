from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, InventoryBatchViewSet, FarmerViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'batches', InventoryBatchViewSet)
router.register(r'farmers', FarmerViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
