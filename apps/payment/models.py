from django.db import models
from django.conf import settings
from apps.orders.models import Order


class PaymentTransaction(models.Model):
    """Record of payment transactions."""
    PAYMENT_STATUS_CHOICES = [
        ('INITIATED', 'Initiated'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    PAYMENT_PROVIDER_CHOICES = [
        ('RAZORPAY', 'Razorpay'),
        ('ICICI', 'ICICI'),
        ('CASH', 'Cash'),
        ('WALLET', 'Wallet'),
        ('OTHER', 'Other'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment_transaction')
    
    # Payment provider identification
    provider = models.CharField(
        max_length=20, 
        choices=PAYMENT_PROVIDER_CHOICES, 
        default='RAZORPAY',
        help_text='Payment service provider'
    )
    
    # Legacy Razorpay fields (kept for backward compatibility)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    
    # ICICI Eazypay fields
    icici_merchant_tran_id = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text='ICICI Merchant Transaction ID (max 20 chars)'
    )
    icici_ref_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text='ICICI Reference ID from QR generation'
    )
    icici_bank_rrn = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text='Bank Reference Number (RRN) from ICICI'
    )
    
    # Common fields
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='INITIATED')
    
    # Additional metadata (can store raw response, error details, etc.)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order.tracking_id} - {self.provider} - {self.status}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['icici_merchant_tran_id']),
            models.Index(fields=['razorpay_order_id']),
            models.Index(fields=['provider', 'status']),
        ]
