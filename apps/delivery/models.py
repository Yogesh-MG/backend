from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
import math

class DeliverySlot(models.Model):
    """Delivery time slots available for orders."""
    SLOT_TYPES = [
        ('EXPRESS', 'Express'),
        ('SAME_DAY', 'Same Day'),
        ('NEXT_DAY', 'Next Day'),
        ('OUT_OF_RADIUS', '2-4 Days Delivery'),
    ]

    id = models.CharField(max_length=50, primary_key=True)
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    slot_type = models.CharField(max_length=20, choices=SLOT_TYPES)
    delivery_fee = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    weight_charge = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Delivery charge per kg (applied for weight-based pricing)")
    available = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.id})"

    class Meta:
        ordering = ['created_at']


class DeliveryAddress(models.Model):
    """Saved delivery addresses for users."""
    ADDRESS_TYPES = [
        ('HOME', 'Home'),
        ('WORK', 'Work'),
        ('OTHER', 'Other'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_addresses')
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPES, default='HOME')
    title = models.CharField(max_length=50)
    address_line = models.TextField()
    latitude = models.DecimalField(max_digits=15, decimal_places=10, null=True, blank=True)
    longitude = models.DecimalField(max_digits=15, decimal_places=10, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    class Meta:
        ordering = ['-is_default', '-created_at']


class ServiceArea(models.Model):
    """Service area zones for delivery restriction."""
    name = models.CharField(max_length=100)
    center_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    center_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius_km = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.radius_km}km)"

    def contains_point(self, latitude: float, longitude: float) -> bool:
        """Check if a point is within this service area using Haversine formula."""
        lat1 = float(self.center_latitude)
        lon1 = float(self.center_longitude)
        lat2 = float(latitude)
        lon2 = float(longitude)

        R = 6371  # Earth's radius in km
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        distance = R * c

        return distance <= float(self.radius_km)

    @staticmethod
    def is_in_any_active_service_area(latitude: float, longitude: float) -> bool:
        """Check if a coordinate point is in any active service area."""
        service_areas = ServiceArea.objects.filter(is_active=True)
        for area in service_areas:
            if area.contains_point(latitude, longitude):
                return True
        return False

    class Meta:
        ordering = ['-is_active', 'name']


class CheckoutConfig(models.Model):
    """Global checkout configuration settings."""
    cod_enabled = models.BooleanField(
        default=True,
        help_text="Enable or disable Cash on Delivery payment option"
    )
    free_delivery_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=3000.00,
        validators=[MinValueValidator(0)],
        help_text="Order subtotal threshold for free delivery (in INR)"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checkout_config_updates'
    )

    def __str__(self):
        return f"Checkout Config (COD: {'Enabled' if self.cod_enabled else 'Disabled'}, Free Delivery: ₹{self.free_delivery_threshold})"

    class Meta:
        verbose_name = "Checkout Configuration"
        verbose_name_plural = "Checkout Configuration"

    @classmethod
    def get_config(cls):
        """Get or create the singleton checkout config."""
        config, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'cod_enabled': True,
                'free_delivery_threshold': 3000.00
            }
        )
        return config
