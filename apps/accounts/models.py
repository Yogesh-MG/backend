from django.contrib.auth.models import AbstractUser
from django.db import models

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

class FarmerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmer_profile')
    location = models.CharField(max_length=255)
    years_of_experience = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.0)
    speciality = models.CharField(max_length=255, help_text="e.g. Leafy greens & herbs")
    bio = models.TextField(blank=True)
    image = models.ImageField(upload_to='farmers/', null=True, blank=True)

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
