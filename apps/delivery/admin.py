from django.contrib import admin
from .models import DeliverySlot, DeliveryAddress, ServiceArea


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
