import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from apps.inventory.models import InventoryBatch

class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYMENT_METHODS = [
        ('WALLET', 'Wallet Only'),
        ('WALLET_CARD', 'Wallet + Card'),
        ('WALLET_UPI', 'Wallet + UPI'),
        ('UPI', 'UPI'),
        ('CARD', 'Credit/Debit Card'),
        ('COD', 'Cash on Delivery'),
    ]

    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    SLOT_CHOICES = [
        ('EXPRESS', 'Express (12 min)'),
        ('SAME_DAY', 'Same Day'),
        ('NEXT_DAY', 'Next Day'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    tracking_id = models.CharField(max_length=20, unique=True, editable=False)
    
    # Address Info
    address_title = models.CharField(max_length=50, default="Home")
    address_line = models.TextField()
    
    # Delivery Info
    delivery_slot = models.CharField(max_length=20, choices=SLOT_CHOICES, default='EXPRESS')
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Payment Info
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='UPI')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    wallet_amount_used = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_paid = models.BooleanField(default=False)
    
    # Totals
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # PRIDE discount tracking
    member_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    pride_limit_used = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Organic Impact Tracker Snapshot for this specific order
    order_water = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    order_soil = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    order_chemical = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    order_farmer = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.tracking_id:
            self.tracking_id = f"FRSH-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.tracking_id} - {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    batch = models.ForeignKey(InventoryBatch, on_delete=models.SET_NULL, null=True)
    
    product_name = models.CharField(max_length=255) # Snapshot at time of order
    price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.quantity} x {self.product_name} (Order {self.order.tracking_id})"
