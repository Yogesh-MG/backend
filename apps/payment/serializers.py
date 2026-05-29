from rest_framework import serializers
from .models import PaymentTransaction


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'order', 'provider',
            # Razorpay fields
            'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature',
            # ICICI fields
            'icici_merchant_tran_id', 'icici_ref_id', 'icici_bank_rrn',
            # Common fields
            'amount', 'currency', 'status', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'provider',
            'razorpay_payment_id', 'razorpay_signature',
            'icici_ref_id', 'icici_bank_rrn',
            'status', 'created_at', 'updated_at'
        ]
