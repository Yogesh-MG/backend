from django.contrib.auth.models import AbstractUser
from django.db import models
import secrets
from django.utils import timezone
from datetime import timedelta

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        CUSTOMER = "CUSTOMER", "Customer"
        FARMER = "FARMER", "Farmer"
        DELIVERY = "DELIVERY", "Delivery"
        PICKER = "PICKER", "Picker"
        POS_OPERATOR = "POS_OPERATOR", "POS Operator"

    role = models.CharField(
        max_length=20, 
        choices=Role.choices, 
        default=Role.CUSTOMER
    )
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.role})"


class OtpCode(models.Model):
    """Store OTP codes sent to phone numbers for delivery partner authentication."""
    phone_number = models.CharField(max_length=15)
    code = models.CharField(max_length=6)
    attempts = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'is_verified']),
        ]

    def __str__(self):
        return f"OTP for {self.phone_number} - {'Verified' if self.is_verified else 'Pending'}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_expired() and not self.is_verified and self.attempts < 5

    @classmethod
    def create_otp(cls, phone_number, validity_minutes=10):
        """Create a new OTP code for a phone number."""
        import random
        code = str(random.randint(100000, 999999))
        expires_at = timezone.now() + timedelta(minutes=validity_minutes)
        otp = cls.objects.create(
            phone_number=phone_number,
            code=code,
            expires_at=expires_at
        )
        return otp


class DeviceAuthKey(models.Model):
    """Store long-lived device authentication keys for delivery partners."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='device_auth_key')
    key = models.CharField(max_length=255, unique=True, db_index=True)
    device_name = models.CharField(max_length=100, blank=True, help_text="e.g., iPhone 12, Samsung Galaxy")
    device_identifier = models.CharField(max_length=255, blank=True, help_text="Device UUID or fingerprint")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Device key for {self.user.username} - {'Active' if self.is_active else 'Inactive'}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def mark_used(self):
        """Update last_used_at timestamp."""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])

    @classmethod
    def create_device_key(cls, user, device_name="", device_identifier="", validity_days=90):
        """Create a new device auth key for a user."""
        key = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=validity_days)
        
        # Use update_or_create to handle OneToOneField constraint
        device_key, created = cls.objects.update_or_create(
            user=user,
            defaults={
                'key': key,
                'device_name': device_name,
                'device_identifier': device_identifier,
                'expires_at': expires_at,
                'is_active': True,
                'last_used_at': None
            }
        )
        return device_key


class FarmerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmer_profile')
    farm_name = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255)
    years_of_experience = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.0)
    speciality = models.CharField(max_length=255, help_text="e.g. Leafy greens & herbs")
    bio = models.TextField(blank=True)
    image = models.ImageField(upload_to='farmers/', null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    total_acreage = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    crops = models.JSONField(default=list, blank=True)
    organic_pledge_accepted = models.BooleanField(default=False)
    organic_pledge_signature = models.CharField(max_length=255, blank=True)
    organic_pledge_accepted_at = models.DateTimeField(null=True, blank=True)
    preferred_language = models.CharField(max_length=10, default='en')
    fcm_token = models.TextField(blank=True, help_text="Firebase Cloud Messaging token for push notifications")
    fcm_token_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Farmer: {self.user.get_full_name() or self.user.username}"


class CustomerPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")
    organic_only = models.BooleanField(default=False)
    vegetarian = models.BooleanField(default=True)
    avoid_plastic = models.BooleanField(default=True)
    allergens = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user.username}"


class CustomerSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_settings")
    order_updates = models.BooleanField(default=True)
    offers = models.BooleanField(default=False)
    weekly_summary = models.BooleanField(default=True)
    private_profile = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Settings for {self.user.username}"
