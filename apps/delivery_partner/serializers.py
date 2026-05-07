"""Delivery Partner app serializers."""
from rest_framework import serializers
from .models import DeliveryPartnerProfile, DeliveryAssignment, DeliveryStop, ProofOfDelivery


class DeliveryStopItemSerializer(serializers.Serializer):
    """Inline serializer for items within a stop (from OrderItems)."""
    name = serializers.CharField()
    qty = serializers.IntegerField()
    weight = serializers.CharField()
    fragile = serializers.BooleanField(default=False)


class DeliveryStopSerializer(serializers.ModelSerializer):
    """Serializer for individual delivery stops."""
    items = serializers.SerializerMethodField()
    customer = serializers.CharField(source='customer_name', default='')

    class Meta:
        model = DeliveryStop
        fields = [
            'id', 'type', 'label', 'address', 'customer',
            'eta', 'items', 'notes',
        ]

    def get_items(self, obj):
        """Pull items from the parent assignment's order."""
        if obj.type == 'dropoff' and obj.assignment.order:
            order_items = obj.assignment.order.items.all()
            return [{
                'name': item.product_name,
                'qty': item.quantity,
                'weight': item.unit,
                'fragile': False,
            } for item in order_items]
        return []


class DeliveryAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for delivery missions — matches SDK DeliveryMission type."""
    stops = DeliveryStopSerializer(many=True, read_only=True)
    fee = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryAssignment
        fields = [
            'id', 'service', 'earnings', 'distance_km',
            'weight_kg', 'stops', 'fee', 'status',
        ]

    def get_fee(self, obj):
        return {
            'weight': float(obj.fee_weight),
            'distance': float(obj.fee_distance),
            'premium': float(obj.fee_premium),
        }


class DeliveryPartnerStatsSerializer(serializers.Serializer):
    """Today's earnings summary — matches SDK DeliveryPartnerStats."""
    earnings = serializers.FloatField()
    goal = serializers.FloatField()
    deliveries = serializers.IntegerField()
    distance = serializers.FloatField()
    rating = serializers.FloatField()


class DeliveryPartnerProfileSerializer(serializers.ModelSerializer):
    """Serializer for delivery partner profile."""
    username = serializers.CharField(source='user.username', read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryPartnerProfile
        fields = [
            'id', 'username', 'name', 'vehicle_type', 'vehicle_number',
            'is_online', 'total_deliveries', 'total_earnings', 'rating',
        ]

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class ProofOfDeliverySerializer(serializers.ModelSerializer):
    """Serializer for proof of delivery uploads."""
    class Meta:
        model = ProofOfDelivery
        fields = ['id', 'type', 'otp_code', 'otp_verified', 'photo', 'created_at']
        read_only_fields = ['otp_verified']
