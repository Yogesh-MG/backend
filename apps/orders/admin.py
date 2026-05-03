from django.contrib import admin

from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'price', 'quantity', 'unit')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('tracking_id', 'user', 'status', 'total', 'created_at')
    list_filter = ('status', 'delivery_slot', 'payment_method')
    search_fields = ('tracking_id', 'user__username', 'user__email')
    inlines = [OrderItemInline]
    readonly_fields = ('tracking_id', 'created_at', 'updated_at')

