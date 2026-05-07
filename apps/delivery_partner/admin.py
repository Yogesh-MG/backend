"""Delivery Partner app admin registration."""
from django.contrib import admin
from .models import DeliveryPartnerProfile, DeliveryAssignment, DeliveryStop, ProofOfDelivery


@admin.register(DeliveryPartnerProfile)
class DeliveryPartnerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'vehicle_type', 'is_online', 'total_deliveries', 'rating')
    list_filter = ('is_online', 'vehicle_type')
    search_fields = ('user__username', 'vehicle_number')


class DeliveryStopInline(admin.TabularInline):
    model = DeliveryStop
    extra = 0
    readonly_fields = ('id',)


class ProofInline(admin.TabularInline):
    model = ProofOfDelivery
    extra = 0
    readonly_fields = ('id', 'created_at')


@admin.register(DeliveryAssignment)
class DeliveryAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'partner', 'status', 'service', 'earnings', 'created_at')
    list_filter = ('status', 'service')
    search_fields = ('order__tracking_id', 'partner__username')
    inlines = [DeliveryStopInline, ProofInline]
    readonly_fields = ('id',)
