from rest_framework import serializers
from django.utils.timezone import now
from decimal import Decimal
from .models import Wallet, WalletTransaction, WalletTopup, Partnership, Referral


class WalletSerializer(serializers.ModelSerializer):
    """Wallet balance and status."""
    tier_display = serializers.CharField(source='get_tier_display', read_only=True)
    
    class Meta:
        model = Wallet
        fields = ['balance', 'tier', 'tier_display', 'created_at', 'updated_at']
        read_only_fields = ['balance', 'tier', 'created_at', 'updated_at']


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Transaction history with full audit trail."""
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'amount', 'reason', 'reason_display',
            'balance_before', 'balance_after',
            'related_order', 'related_topup',
            'notes', 'created_at'
        ]
        read_only_fields = fields


class WalletTopupSerializer(serializers.ModelSerializer):
    """Wallet top-up transaction."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = WalletTopup
        fields = [
            'id', 'amount', 'status', 'status_display',
            'razorpay_order_id', 'razorpay_payment_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class WalletTopupInitiateSerializer(serializers.Serializer):
    """Initiate a wallet top-up."""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('100.00'))
    
    def validate_amount(self, value):
        # Max daily top-up limit: ₹10,000
        if value > Decimal('10000.00'):
            raise serializers.ValidationError("Maximum top-up amount is ₹10,000 per transaction.")
        return value


class PartnershipSerializer(serializers.ModelSerializer):
    """Partnership tier details."""
    tier_display = serializers.CharField(source='get_tier_display', read_only=True)
    total_savings = serializers.SerializerMethodField()
    
    class Meta:
        model = Partnership
        fields = [
            'tier', 'tier_display', 'invested_amount',
            'monthly_credit_percentage', 'annual_loyalty_percentage',
            'start_date', 'refund_requested', 'total_savings'
        ]
        read_only_fields = ['tier', 'invested_amount', 'start_date', 'refund_requested']
    
    def get_total_savings(self, obj):
        """Calculate total savings from partnership."""
        # This is a simplified calculation; adjust based on actual business logic
        months_active = (now() - obj.start_date).days // 30
        monthly_credit = (obj.invested_amount * obj.monthly_credit_percentage) / 100
        total = monthly_credit * months_active
        
        # Add annual loyalty bonus if applicable
        if months_active >= 12:
            annual_bonus = (obj.invested_amount * obj.annual_loyalty_percentage) / 100
            total += annual_bonus
        
        return float(total)


class ReferralSerializer(serializers.ModelSerializer):
    """Referral information."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    referee_name = serializers.CharField(source='referee.username', read_only=True)
    
    class Meta:
        model = Referral
        fields = [
            'id', 'referral_code', 'referee_name', 'bonus_amount',
            'status', 'status_display', 'bonus_credited_date', 'created_at'
        ]
        read_only_fields = fields


class WalletDetailSerializer(serializers.ModelSerializer):
    """Comprehensive wallet details with recent transactions."""
    tier_display = serializers.CharField(source='get_tier_display', read_only=True)
    accumulated_pride_limit = serializers.SerializerMethodField()
    remaining_pride_limit = serializers.SerializerMethodField()
    transactions = serializers.SerializerMethodField()
    partnership = PartnershipSerializer(source='user.partnership', read_only=True, allow_null=True)
    
    class Meta:
        model = Wallet
        fields = ['balance', 'tier', 'tier_display', 'accumulated_pride_limit', 'remaining_pride_limit', 'transactions', 'partnership', 'updated_at']
        read_only_fields = fields
    
    def get_accumulated_pride_limit(self, obj):
        try:
            return float(getattr(obj, 'accumulated_pride_limit', 0.00))
        except Exception:
            return 0.00

    def get_remaining_pride_limit(self, obj):
        try:
            return float(getattr(obj, 'accumulated_pride_limit', 0.00))
        except Exception:
            return 0.00
    
    def get_transactions(self, obj):
        """Get last 10 transactions."""
        transactions = obj.transactions.all()[:10]
        return WalletTransactionSerializer(transactions, many=True).data
