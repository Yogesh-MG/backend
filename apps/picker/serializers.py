"""Picker app serializers."""
from rest_framework import serializers
from .models import Hub, PickerProfile, PickerTask, PickerTaskItem


class HubSerializer(serializers.ModelSerializer):
    """Serializer for hub locations."""
    class Meta:
        model = Hub
        fields = ['id', 'name', 'latitude', 'longitude', 'radius_meters']


class PickerTaskItemSerializer(serializers.ModelSerializer):
    """Serializer for individual pick items within a task."""
    substitutions = serializers.SerializerMethodField()

    class Meta:
        model = PickerTaskItem
        fields = [
            'id', 'name', 'sku', 'batch_code', 'quantity', 'unit',
            'location', 'emoji', 'status', 'substitutions',
        ]
        # Rename batch_code → batch in output for SDK compatibility
        extra_kwargs = {'batch_code': {'source': 'batch_code'}}

    def get_substitutions(self, obj):
        if obj.substitution_name:
            return [{
                'name': obj.substitution_name,
                'sku': obj.substitution_sku,
                'reason': obj.substitution_reason,
            }]
        return []

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # SDK expects `batch` not `batch_code`
        data['batch'] = data.pop('batch_code', '')
        return data


class PickerTaskSerializer(serializers.ModelSerializer):
    """Serializer for picker tasks (order queue)."""
    items = PickerTaskItemSerializer(many=True, read_only=True)
    customer = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = PickerTask
        fields = [
            'id', 'customer', 'deadline_minutes', 'item_count',
            'priority', 'items', 'status',
        ]

    def get_customer(self, obj):
        return obj.order.user.get_full_name() or obj.order.user.username

    def get_item_count(self, obj):
        return obj.items.count()


class PickerGeoVerifyResponseSerializer(serializers.Serializer):
    """Response for geo-fence verification."""
    verified = serializers.BooleanField()
    message = serializers.CharField()
    hub_name = serializers.CharField(required=False)


class PickerProfileSerializer(serializers.ModelSerializer):
    """Serializer for the picker's profile."""
    username = serializers.CharField(source='user.username', read_only=True)
    hub_details = HubSerializer(source='hub', read_only=True)

    class Meta:
        model = PickerProfile
        fields = [
            'id', 'username', 'hub', 'hub_details',
            'hub_name', 'hub_latitude', 'hub_longitude',
            'hub_radius_meters', 'is_active',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # If hub relation exists, override deprecated fields with hub data
        if instance.hub:
            data['hub_name'] = instance.hub.name
            data['hub_latitude'] = float(instance.hub.latitude)
            data['hub_longitude'] = float(instance.hub.longitude)
            data['hub_radius_meters'] = instance.hub.radius_meters
        return data
