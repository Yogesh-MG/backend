"""
Farmer app models.

Extends the existing FarmerProfile from accounts with farmer-specific
operational models: media uploads, payout tracking, and OTP verification.
The core FarmerProfile remains in accounts — these models are supplementary.
"""
import uuid
from django.db import models
from django.conf import settings


class FarmerMedia(models.Model):
    """Media uploads for farm/product verification and marketing."""
    MEDIA_TYPES = [
        ('farm_video', 'Farm Video'),
        ('product_video', 'Product Video'),
        ('profile_photo', 'Profile Photo'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(
        'accounts.FarmerProfile',
        on_delete=models.CASCADE,
        related_name='media_uploads',
    )
    type = models.CharField(max_length=20, choices=MEDIA_TYPES)
    file = models.FileField(upload_to='farmer_media/')
    thumbnail = models.ImageField(upload_to='farmer_media/thumbnails/', null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} by {self.farmer.user.username}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Farmer Media"


class FarmerPayout(models.Model):
    """Tracks payments from FreshOn to farmers for sold produce."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(
        'accounts.FarmerProfile',
        on_delete=models.CASCADE,
        related_name='payouts',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # Optional Razorpay/NEFT reference
    transaction_ref = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payout ₹{self.amount} to {self.farmer.user.username} [{self.status}]"

    class Meta:
        ordering = ['-created_at']


class FarmerOTP(models.Model):
    """Temporary OTP storage for farmer phone verification."""
    phone = models.CharField(max_length=15)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"OTP for {self.phone}"

    class Meta:
        ordering = ['-created_at']


class BankDetails(models.Model):
    """Farmer's bank account information for payouts."""
    farmer = models.OneToOneField(
        'accounts.FarmerProfile',
        on_delete=models.CASCADE,
        related_name='bank_details',
    )
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=255, blank=True)
    upi_id = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bank: {self.account_name} ({self.farmer.user.username})"


class FarmerNotification(models.Model):
    """In-app notifications for farmers."""
    TYPE_CHOICES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(
        'accounts.FarmerProfile',
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} for {self.farmer.user.username}"

    class Meta:
        ordering = ['-created_at']
