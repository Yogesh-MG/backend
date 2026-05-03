from django.contrib import admin
from .models import PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['order', 'razorpay_order_id', 'amount', 'status', 'created_at']
    list_filter = ['status', 'currency']
    search_fields = ['razorpay_order_id', 'razorpay_payment_id', 'order__tracking_id']
    readonly_fields = ['razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature']
