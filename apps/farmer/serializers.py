"""Farmer app serializers."""
from rest_framework import serializers
from apps.accounts.models import FarmerProfile
from apps.inventory.models import InventoryBatch
from .models import FarmerMedia, FarmerPayout, BankDetails, FarmerNotification


class FarmerProfileSerializer(serializers.ModelSerializer):
    """Full farmer profile, including onboarding persistence fields."""
    name = serializers.SerializerMethodField()

    class Meta:
        model = FarmerProfile
        fields = [
            'id', 'name', 'farm_name', 'location', 'years_of_experience', 'rating',
            'speciality', 'bio', 'image', 'latitude', 'longitude', 'total_acreage',
            'crops', 'organic_pledge_accepted', 'organic_pledge_signature',
            'organic_pledge_accepted_at', 'fcm_token', 'fcm_token_updated_at',
        ]
        read_only_fields = ['id', 'rating', 'fcm_token_updated_at']

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class FarmerBatchSerializer(serializers.ModelSerializer):
    """Farmer-facing batch view with frontend-friendly aliases."""
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    product_id = serializers.IntegerField(source='variant.product.id', read_only=True)
    category = serializers.CharField(source='variant.product.category.name', read_only=True)
    unit = serializers.CharField(source='variant.unit', read_only=True)
    price = serializers.DecimalField(source='purchase_price', max_digits=10, decimal_places=2, read_only=True)
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    stock_level = serializers.DecimalField(max_digits=10, decimal_places=3, read_only=True)
    stock = serializers.DecimalField(source='stock_level', max_digits=10, decimal_places=3, read_only=True)
    quantity = serializers.DecimalField(source='stock_level', max_digits=10, decimal_places=3, read_only=True)
    price_per_unit = serializers.DecimalField(source='purchase_price', max_digits=10, decimal_places=2, read_only=True)
    image = serializers.ImageField(source='variant.product.base_image', read_only=True)
    is_organic = serializers.BooleanField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = InventoryBatch
        fields = [
            'id', 'product_id', 'product_name', 'price', 'mrp',
            'stock_level', 'stock', 'quantity', 'price_per_unit', 'category',
            'unit', 'image', 'harvest_date', 'is_organic', 'status',
        ]

    def get_status(self, obj):
        if obj.stock_level == 0:
            return "Out of Stock"
        return "Live"


class FarmerAddBatchSerializer(serializers.Serializer):
    """Input serializer for adding a new batch."""
    product_id = serializers.IntegerField(required=False, default=0)
    custom_product_name = serializers.CharField(max_length=255, required=False, default='')
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    stock_level = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=0)
    harvest_date = serializers.DateTimeField()
    is_organic = serializers.BooleanField(default=False)


class BankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetails
        fields = ['id', 'account_name', 'account_number', 'ifsc_code', 'bank_name', 'upi_id', 'is_verified']
        read_only_fields = ['is_verified']


class FarmerNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerNotification
        fields = ['id', 'title', 'message', 'type', 'notification_type', 'metadata', 'is_read', 'created_at']
        read_only_fields = ['created_at']


class FarmerDashboardSerializer(serializers.Serializer):
    """Aggregated dashboard metrics for the farmer."""
    total_earnings = serializers.FloatField()
    total_sales = serializers.FloatField()
    lifetime_earnings = serializers.FloatField()
    current_month_earnings = serializers.FloatField()
    monthly_earnings = serializers.FloatField()
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
