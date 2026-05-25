from rest_framework import serializers
from .models import DeliverySlot, DeliveryAddress, ServiceArea, CheckoutConfig


class DeliverySlotSerializer(serializers.ModelSerializer):
    fee = serializers.DecimalField(source='delivery_fee', max_digits=5, decimal_places=2)

    class Meta:
        model = DeliverySlot
        fields = ['id', 'title', 'description', 'slot_type', 'fee', 'available', 'start_time', 'end_time']


class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = ['id', 'address_type', 'title', 'address_line', 'latitude', 'longitude', 'is_default']
        read_only_fields = ['id']


class ServiceAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceArea
        fields = ['id', 'name', 'center_latitude', 'center_longitude', 'radius_km', 'is_active']


class CheckoutConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckoutConfig
        fields = ['cod_enabled', 'free_delivery_threshold', 'updated_at']
        read_only_fields = ['updated_at']
