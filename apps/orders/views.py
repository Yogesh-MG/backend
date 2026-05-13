from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .models import Order
from .serializers import OrderCreateSerializer, OrderDetailSerializer
from .order_modification import OrderModificationService


class OrderPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 50


class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = OrderPagination

    def get_queryset(self):
        # Users can only see their own orders
        return Order.objects.filter(
            user=self.request.user
        ).prefetch_related('items').order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderDetailSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        # Allow looking up by tracking_id instead of just PK
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]
        
        if lookup_value.startswith('FRSH-'):
            try:
                instance = Order.objects.get(tracking_id=lookup_value, user=request.user)
                serializer = self.get_serializer(instance)
                return Response(serializer.data)
            except Order.DoesNotExist:
                return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='add-item')
    def add_item(self, request, pk=None):
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
    def remove_item(self, request, pk=None):
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
