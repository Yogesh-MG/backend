from django.contrib import admin
from .models import DeliverySlot, DeliveryAddress, ServiceArea, CheckoutConfig


@admin.register(DeliverySlot)
class DeliverySlotAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'slot_type', 'delivery_fee', 'available']
    list_filter = ['available', 'slot_type']
    search_fields = ['title', 'description']


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'address_type', 'title', 'is_default']
    list_filter = ['address_type', 'is_default']
    search_fields = ['user__username', 'title', 'address_line']


@admin.register(ServiceArea)
class ServiceAreaAdmin(admin.ModelAdmin):
    list_display = ['name', 'radius_km', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'is_active')}),
        ('Location', {'fields': ('center_latitude', 'center_longitude', 'radius_km')}),
    )


@admin.register(CheckoutConfig)
class CheckoutConfigAdmin(admin.ModelAdmin):
    list_display = ['cod_enabled', 'free_delivery_threshold', 'updated_at', 'updated_by']
    readonly_fields = ['updated_at']
    
    def has_add_permission(self, request):
        # Only allow one instance (singleton pattern)
        return not CheckoutConfig.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of the config
        return False
