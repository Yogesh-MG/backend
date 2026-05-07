"""Farmer app serializers."""
from rest_framework import serializers
from apps.accounts.models import FarmerProfile
from apps.inventory.models import InventoryBatch
from .models import FarmerMedia, FarmerPayout


class FarmerProfileSerializer(serializers.ModelSerializer):
    """Full farmer profile — extends the accounts.FarmerProfile."""
    name = serializers.SerializerMethodField()
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, write_only=True,
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, write_only=True,
    )
    total_acreage = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, write_only=True,
    )

    class Meta:
        model = FarmerProfile
        fields = [
            'id', 'name', 'location', 'years_of_experience', 'rating',
            'speciality', 'bio', 'image', 'latitude', 'longitude', 'total_acreage',
        ]
        read_only_fields = ['id', 'rating']

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class FarmerBatchSerializer(serializers.ModelSerializer):
    """Farmer-facing batch view — includes computed status field."""
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    product_id = serializers.IntegerField(source='variant.product.id', read_only=True)
    is_organic = serializers.BooleanField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = InventoryBatch
        fields = [
            'id', 'product_id', 'product_name', 'price', 'mrp',
            'stock_level', 'harvest_date', 'is_organic', 'status',
        ]

    def get_status(self, obj):
        if obj.stock_level == 0:
            return "Out of Stock"
        # Could add admin approval logic here
        return "Live"


class FarmerAddBatchSerializer(serializers.Serializer):
    """Input serializer for adding a new batch."""
    product_id = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    stock_level = serializers.IntegerField(min_value=0)
    harvest_date = serializers.DateTimeField()
    is_organic = serializers.BooleanField(default=False)


class FarmerDashboardSerializer(serializers.Serializer):
    """Aggregated dashboard metrics for the farmer."""
    total_earnings = serializers.FloatField()
    current_month_earnings = serializers.FloatField()
    total_products = serializers.IntegerField()
    live_products = serializers.IntegerField()
    avg_rating = serializers.FloatField()
    total_orders = serializers.IntegerField()
    weekly_sales = serializers.FloatField()
    monthly_sales = serializers.FloatField()


class FarmerPayoutSerializer(serializers.ModelSerializer):
    """Payout history item."""
    class Meta:
        model = FarmerPayout
        fields = ['id', 'amount', 'status', 'created_at', 'completed_at']


class FarmerMediaSerializer(serializers.ModelSerializer):
    """Uploaded media item."""
    url = serializers.SerializerMethodField()

    class Meta:
        model = FarmerMedia
        fields = ['id', 'type', 'url', 'is_approved', 'created_at']

    def get_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return str(obj.file.url) if obj.file else None
