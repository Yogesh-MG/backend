from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        CUSTOMER = "CUSTOMER", "Customer"
        FARMER = "FARMER", "Farmer"
        DELIVERY = "DELIVERY", "Delivery"

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
