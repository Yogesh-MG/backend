from rest_framework import serializers
from .models import PaymentTransaction


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = ['id', 'order', 'razorpay_order_id', 'razorpay_payment_id', 'amount', 'currency', 'status']
        read_only_fields = ['id', 'razorpay_payment_id', 'razorpay_signature', 'status']
