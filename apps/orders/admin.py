from django.contrib import admin
from django.db.models import Prefetch

from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'price', 'quantity', 'unit')
    
    def get_queryset(self, request):
        """Optimize inline queryset to avoid N+1 queries."""
        qs = super().get_queryset(request)
        return qs.select_related(
            'batch',
            'batch__variant',
            'batch__variant__product'
        )

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('tracking_id', 'user', 'status', 'total', 'created_at')
    list_filter = ('status', 'delivery_slot', 'payment_method')
    search_fields = ('tracking_id', 'user__username', 'user__email')
    inlines = [OrderItemInline]
    readonly_fields = ('tracking_id', 'created_at', 'updated_at')
    
    def get_queryset(self, request):
        """Optimize admin list queryset with prefetch to avoid N+1 queries."""
        qs = super().get_queryset(request)
        # Prefetch items with their batch relations
        items_prefetch = Prefetch(
            'items',
            queryset=OrderItem.objects.select_related(
                'batch__variant__product'
            )
        )
        return qs.select_related('user').prefetch_related(items_prefetch)

