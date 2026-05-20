from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from .models import Order, OrderItem
from .serializers import OrderCreateSerializer, OrderDetailSerializer, OrderListSerializer
from .order_modification import OrderModificationService


class OrderPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 50


class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = OrderPagination
    lookup_field = 'tracking_id'

    def get_queryset(self):
        # Users can only see their own orders
        # Optimize with nested prefetch to avoid N+1 queries
        items_prefetch = Prefetch(
            'items',
            queryset=OrderItem.objects.select_related(
                'batch',
                'batch__variant',
                'batch__variant__product',
                'batch__variant__product__category',
                'batch__farmer',
                'batch__farmer__user'
            )
        )
        
        # Prefetch customer impact to avoid N+1 on organic_impact calculation
        # NOTE: CustomerImpact is a OneToOneField with related_name='impact'
        from apps.wallet.models import CustomerImpact
        impact_prefetch = Prefetch(
            'user__impact',
            queryset=CustomerImpact.objects.all()
        )
        
        return Order.objects.filter(
            user=self.request.user
        ).prefetch_related(
            items_prefetch,
            impact_prefetch
        ).order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        if self.action == 'list':
            return OrderListSerializer  # Lightweight serializer for list views
        return OrderDetailSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # retrieve is now handled by lookup_field = 'tracking_id'

    @action(detail=True, methods=['post'], url_path='add-item')
    def add_item(self, request, tracking_id=None):
        """Add a product to an existing order (if not yet packed)."""
        order = self.get_object()
        
        # Verify ownership
        if order.user != request.user:
            return Response(
                {"detail": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            batch_id = request.data.get('batch_id')
            quantity = request.data.get('quantity')
            
            if not batch_id or not quantity:
                return Response(
                    {"detail": "batch_id and quantity are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = OrderModificationService.add_item_to_order(
                order=order,
                batch_id=int(batch_id),
                quantity=int(quantity)
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": "Failed to add item: " + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='remove-item')
    def remove_item(self, request, tracking_id=None):
        """Remove a product from an existing order (if not yet packed)."""
        order = self.get_object()
        
        # Verify ownership
        if order.user != request.user:
            return Response(
                {"detail": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            order_item_id = request.data.get('order_item_id')
            
            if not order_item_id:
                return Response(
                    {"detail": "order_item_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = OrderModificationService.remove_item_from_order(
                order=order,
                order_item_id=int(order_item_id)
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": "Failed to remove item: " + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='update-item')
    def update_item(self, request, tracking_id=None):
        """Update the quantity of an item in an existing order."""
        order = self.get_object()
        
        if order.user != request.user:
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            order_item_id = request.data.get('order_item_id')
            quantity = request.data.get('quantity')
            
            if not order_item_id or quantity is None:
                return Response(
                    {"detail": "order_item_id and quantity are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = OrderModificationService.update_item_quantity(
                order=order,
                order_item_id=int(order_item_id),
                quantity=int(quantity)
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"detail": "Failed to update item: " + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
