"""POS app serializers."""
from rest_framework import serializers
from .models import (
    PosEmployee, PosCustomer, PosShift, PosTransaction,
    PosTransactionItem, PosTender, PosWastageLog,
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
    pride = serializers.BooleanField(source='is_pride', read_only=True)
    wallet_balance = serializers.SerializerMethodField()

    class Meta:
        model = PosCustomer
        fields = ['id', 'name', 'phone', 'email', 'tier', 'points', 'pride', 'wallet_balance']

    def get_wallet_balance(self, obj):
        if obj.user and hasattr(obj.user, 'wallet'):
            return float(obj.user.wallet.balance)
        return 0.0


class PosCartItemSerializer(serializers.Serializer):
    """Cart item within a POS order request."""
    pid = serializers.CharField()
    name = serializers.CharField()
    unit_price = serializers.FloatField()
    weighed = serializers.BooleanField(default=False)
    quantity = serializers.FloatField()
    member_eligible = serializers.BooleanField(default=False)


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
    surcharge = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    receipt_delivery = serializers.ChoiceField(
        choices=['Print', 'WhatsApp', 'SMS'],
        required=False,
        allow_blank=True,
    )


class PosTransactionItemSerializer(serializers.ModelSerializer):
    """Output serializer for POS transaction items."""
    class Meta:
        model = PosTransactionItem
        fields = ['pid', 'name', 'unit_price', 'weighed', 'quantity', 'member_eligible']


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

    class Meta:
        model = PosTransaction
        fields = [
            'id', 'customer_id', 'items', 'tenders', 'method',
            'subtotal', 'member_discount', 'surcharge', 'total',
            'timestamp', 'receipt_delivery',
        ]

    def get_timestamp(self, obj):
        return int(obj.created_at.timestamp() * 1000) if obj.created_at else 0


class PosShiftSerializer(serializers.ModelSerializer):
    """POS shift output."""
    started_at = serializers.SerializerMethodField()
    variance = serializers.ReadOnlyField()

    class Meta:
        model = PosShift
        fields = [
            'id', 'started_at', 'opening_cash', 'cash_sales',
            'total_sales', 'txn_count', 'is_open',
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
