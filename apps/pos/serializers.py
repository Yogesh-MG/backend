"""POS app serializers."""
from rest_framework import serializers
from .models import (
    PosEmployee, PosCustomer, PosShift, PosTransaction,
    PosTransactionItem, PosTender, PosWastageLog,
    PosSettings, CompanyProfile,
)


class PosProductSerializer(serializers.Serializer):
    """
    POS product view — derived from InventoryBatch + Product.
    Not a ModelSerializer because it aggregates across models.
    """
    pid = serializers.CharField()
    name = serializers.CharField()
    price = serializers.FloatField()
    weighed = serializers.BooleanField()
    category = serializers.CharField()
    stock = serializers.IntegerField()
    low_stock_threshold = serializers.IntegerField(default=5)
    member_eligible = serializers.BooleanField(default=False)


class PosCustomerSerializer(serializers.ModelSerializer):
    """POS walk-in customer."""
    pride = serializers.SerializerMethodField()
    wallet_balance = serializers.SerializerMethodField()

    class Meta:
        model = PosCustomer
        fields = ['id', 'name', 'phone', 'email', 'tier', 'points', 'pride', 'wallet_balance']

    def get_pride(self, obj):
        if obj.user and hasattr(obj.user, 'partnership'):
            return not obj.user.partnership.refund_requested
        return obj.is_pride

    def get_wallet_balance(self, obj):
        if obj.user and hasattr(obj.user, 'wallet'):
            return float(obj.user.wallet.balance)
        return 0.0


class PosCompanyProfileSerializer(serializers.ModelSerializer):
    """B2B company profile for POS."""
    class Meta:
        model = CompanyProfile
        fields = ['id', 'name', 'gstin', 'address', 'pan', 'email']


class PosSettingsSerializer(serializers.ModelSerializer):
    """POS terminal settings."""
    class Meta:
        model = PosSettings
        fields = [
            'pride_discount_pct', 'rounding_enabled',
            'rounding_slab', 'max_manual_discount_pct',
        ]


class PosCartItemSerializer(serializers.Serializer):
    """Cart item within a POS order request."""
    pid = serializers.CharField()
    name = serializers.CharField()
    unit_price = serializers.FloatField()
    weighed = serializers.BooleanField(default=False)
    quantity = serializers.FloatField()
    member_eligible = serializers.BooleanField(default=False)
    gst_rate = serializers.FloatField(required=False, default=18.0)


class PosTenderSerializer(serializers.Serializer):
    """Individual payment tender."""
    method = serializers.ChoiceField(choices=['Cash', 'UPI', 'Card', 'Sodexo', 'Wallet'])
    amount = serializers.FloatField()


class PosOrderCreateSerializer(serializers.Serializer):
    """Input serializer for creating a POS order."""
    customer_id = serializers.CharField(required=False, allow_blank=True)
    items = PosCartItemSerializer(many=True)
    tenders = PosTenderSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    member_discount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    manual_discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    manual_discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_reason = serializers.CharField(required=False, allow_blank=True)
    discount_applied_by_id = serializers.CharField(required=False, allow_blank=True)
    surcharge = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    rounding_adjustment = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    receipt_delivery = serializers.ChoiceField(
        choices=['Print', 'WhatsApp', 'SMS'],
        required=False,
        allow_blank=True,
    )
    is_anonymous = serializers.BooleanField(default=False)
    is_b2b = serializers.BooleanField(default=False)
    company_id = serializers.CharField(required=False, allow_blank=True)


class PosTransactionItemSerializer(serializers.ModelSerializer):
    """Output serializer for POS transaction items."""
    class Meta:
        model = PosTransactionItem
        fields = ['pid', 'name', 'unit_price', 'weighed', 'quantity', 'member_eligible', 'gst_rate']


class PosTenderOutputSerializer(serializers.ModelSerializer):
    """Output serializer for POS tenders."""
    class Meta:
        model = PosTender
        fields = ['method', 'amount']


class PosTransactionSerializer(serializers.ModelSerializer):
    """Full POS transaction output — matches SDK PosTransaction type."""
    items = PosTransactionItemSerializer(many=True, read_only=True)
    tenders = PosTenderOutputSerializer(many=True, read_only=True)
    customer_id = serializers.CharField(default='')
    timestamp = serializers.SerializerMethodField()
    company = PosCompanyProfileSerializer(read_only=True)
    discount_applied_by_id = serializers.SerializerMethodField()
    discount_applied_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PosTransaction
        fields = [
            'id', 'customer_id', 'items', 'tenders', 'method',
            'subtotal', 'member_discount', 'surcharge', 'total',
            'timestamp', 'receipt_delivery',
            'manual_discount_percentage', 'manual_discount_amount',
            'discount_reason', 'discount_applied_by_id', 'discount_applied_by_name',
            'rounding_adjustment',
            'is_anonymous', 'is_b2b', 'company', 'invoice_number',
        ]

    def get_timestamp(self, obj):
        return int(obj.created_at.timestamp() * 1000) if obj.created_at else 0

    def get_discount_applied_by_id(self, obj):
        if obj.discount_applied_by:
            return obj.discount_applied_by.employee_id
        return ""

    def get_discount_applied_by_name(self, obj):
        if obj.discount_applied_by:
            return obj.discount_applied_by.user.get_full_name() or obj.discount_applied_by.user.username
        return ""


class PosShiftSerializer(serializers.ModelSerializer):
    """POS shift output."""
    started_at = serializers.SerializerMethodField()
    variance = serializers.ReadOnlyField()

    class Meta:
        model = PosShift
        fields = [
            'id', 'started_at', 'opening_cash', 'cash_sales',
            'total_sales', 'txn_count', 'is_open', 'rounding_loss',
        ]

    def get_started_at(self, obj):
        return int(obj.started_at.timestamp() * 1000) if obj.started_at else 0


class PosShiftSummarySerializer(PosShiftSerializer):
    """Extended shift output with closing info and transactions."""
    closing_cash = serializers.DecimalField(max_digits=10, decimal_places=2)
    variance = serializers.ReadOnlyField()
    transactions = PosTransactionSerializer(many=True, read_only=True)

    class Meta(PosShiftSerializer.Meta):
        fields = PosShiftSerializer.Meta.fields + [
            'closing_cash', 'variance', 'transactions',
        ]


class PosWastageSerializer(serializers.ModelSerializer):
    """POS wastage log entry."""
    class Meta:
        model = PosWastageLog
        fields = ['id', 'pid', 'name', 'quantity', 'weighed', 'unit_price', 'reason']
