"""
Delivery Partner app models.

DeliveryPartnerProfile — extends User for delivery-specific data (online status, GPS, vehicle).
DeliveryAssignment     — a delivery mission with stops (pickup from hub, dropoff to customer).
DeliveryStop           — individual stop within a mission.
ProofOfDelivery        — OTP or photo proof for each delivered stop.
"""
import uuid
from django.db import models
from django.conf import settings


class DeliveryPartnerProfile(models.Model):
    """Delivery partner profile linked to a DELIVERY user."""
    VEHICLE_CHOICES = [
        ('BIKE', 'Bike'),
        ('SCOOTER', 'Scooter'),
        ('CYCLE', 'Bicycle'),
        ('VAN', 'Van'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delivery_partner_profile',
    )
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_CHOICES, default='BIKE')
    vehicle_number = models.CharField(max_length=20, blank=True)
    is_online = models.BooleanField(default=False)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    # Lifetime stats
    total_deliveries = models.PositiveIntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status = "🟢 Online" if self.is_online else "🔴 Offline"
        return f"Driver: {self.user.get_full_name() or self.user.username} ({status})"

    class Meta:
        ordering = ['-is_online', '-updated_at']


class DeliveryAssignment(models.Model):
    """
    A delivery mission assigned to a partner.
    Lifecycle: PENDING → ACCEPTED → PICKED_UP → IN_TRANSIT → DELIVERED
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Acceptance'),
        ('ACCEPTED', 'Accepted'),
        ('PICKED_UP', 'Picked Up from Hub'),
        ('IN_TRANSIT', 'In Transit'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]

    SERVICE_CHOICES = [
        ('swift', 'Swift (12 min)'),
        ('next-day', 'Next Day'),
        ('standard', 'Standard'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='delivery_assignment',
    )
    partner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivery_assignments',
        limit_choices_to={'role': 'DELIVERY'},
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    service = models.CharField(max_length=20, choices=SERVICE_CHOICES, default='swift')

    # Fee breakdown
    earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    fee_weight = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    fee_distance = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    fee_premium = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    accepted_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    in_transit_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Assignment {self.id} — Order {self.order.tracking_id} [{self.status}]"

    class Meta:
        ordering = ['-created_at']


class DeliveryStop(models.Model):
    """Individual stop within a delivery assignment (pickup/dropoff)."""
    STOP_TYPES = [
        ('pickup', 'Pickup'),
        ('dropoff', 'Dropoff'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        DeliveryAssignment,
        on_delete=models.CASCADE,
        related_name='stops',
    )
    type = models.CharField(max_length=10, choices=STOP_TYPES)
    label = models.CharField(max_length=100, help_text="e.g. 'FreshOn Hub' or 'Customer Home'")
    address = models.TextField()
    customer_name = models.CharField(max_length=100, blank=True)
    eta = models.CharField(max_length=50, blank=True, help_text="e.g. '12:45 PM'")
    notes = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    sequence = models.PositiveIntegerField(default=0, help_text="Stop ordering within the mission")

    def __str__(self):
        return f"{self.type.title()}: {self.label}"

    class Meta:
        ordering = ['sequence']


class ProofOfDelivery(models.Model):
    """Proof of delivery — OTP verification or photo."""
    PROOF_TYPES = [
        ('otp', 'OTP Verification'),
        ('photo', 'Delivery Photo'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        DeliveryAssignment,
        on_delete=models.CASCADE,
        related_name='proofs',
    )
    stop = models.ForeignKey(
        DeliveryStop,
        on_delete=models.CASCADE,
        related_name='proofs',
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=10, choices=PROOF_TYPES)
    otp_code = models.CharField(max_length=6, blank=True)
    otp_verified = models.BooleanField(default=False)
    photo = models.ImageField(upload_to='delivery_proofs/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Proof ({self.type}) for Assignment {self.assignment_id}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Proofs of Delivery"
