"""
Picker app models.

PickerProfile — extends User for picker-specific data (hub assignment, geo-fence).
PickerTask    — a single order assigned to a picker for fulfillment.
PickerTaskItem — individual line item within a picker task.
"""
import uuid
from django.db import models
from django.conf import settings


class Hub(models.Model):
    """A physical store or fulfillment center location."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius_meters = models.PositiveIntegerField(
        default=200,
        help_text="Geo-fence radius in meters around the hub",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "FreshOn Hub"
        verbose_name_plural = "FreshOn Hubs"


class PickerProfile(models.Model):
    """Picker-specific profile tied to a PICKER user."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='picker_profile',
    )
    hub = models.ForeignKey(
        Hub,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pickers',
        help_text="The hub this picker is primarily assigned to",
    )
    # Deprecated: These should be fetched from the linked Hub
    hub_name = models.CharField(max_length=100, default="FreshOn Hub", blank=True)
    hub_latitude = models.DecimalField(max_digits=9, decimal_places=6, default=0)
    hub_longitude = models.DecimalField(max_digits=9, decimal_places=6, default=0)
    hub_radius_meters = models.PositiveIntegerField(
        default=200,
        help_text="Geo-fence radius in meters around the hub",
    )
    is_active = models.BooleanField(default=True)
    pin = models.CharField(max_length=6, blank=True, help_text="Optional numeric PIN for quick login")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Picker: {self.user.get_full_name() or self.user.username} @ {self.hub_name} @ {self.user.id}"

    class Meta:
        ordering = ['-created_at']


class PickerTask(models.Model):
    """
    A picker task represents a single customer order that needs to be picked,
    packed, and handed over to delivery. Lifecycle:
    QUEUED → IN_PROGRESS → PACKED → HANDED_OVER
    """
    STATUS_CHOICES = [
        ('QUEUED', 'Queued'),
        ('IN_PROGRESS', 'In Progress'),
        ('PACKED', 'All Items Packed'),
        ('HANDED_OVER', 'Handed to Delivery'),
        ('CANCELLED', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('urgent', 'Urgent'),
        ('high', 'High'),
        ('normal', 'Normal'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='picker_task',
    )
    picker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='picker_tasks',
        limit_choices_to={'role': 'PICKER'},
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='QUEUED')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    deadline_minutes = models.PositiveIntegerField(
        default=12,
        help_text="Minutes from order placement to target dispatch",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    packed_at = models.DateTimeField(null=True, blank=True)
    handed_over_at = models.DateTimeField(null=True, blank=True)
    delivery_partner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_tasks',
        limit_choices_to={'role': 'DELIVERY'},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PickerTask {self.id} — Order {self.order.tracking_id} [{self.status}]"

    class Meta:
        ordering = ['priority', 'created_at']


class PickerTaskItem(models.Model):
    """Individual item within a picker task, tracking scan/pack status."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('scanning', 'Scanning'),
        ('packed', 'Packed'),
        ('issue', 'Issue'),
        ('substituted', 'Substituted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(PickerTask, on_delete=models.CASCADE, related_name='items')
    order_item = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.CASCADE,
        related_name='picker_task_items',
    )
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, blank=True)
    batch_code = models.CharField(max_length=50, blank=True, help_text="Expected barcode/QR")
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=50)
    location = models.CharField(max_length=100, blank=True, help_text="Aisle/shelf location in hub")
    emoji = models.CharField(max_length=10, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    scanned_barcode = models.CharField(max_length=100, blank=True, help_text="Actual barcode scanned by picker")
    substitution_name = models.CharField(max_length=255, blank=True)
    substitution_sku = models.CharField(max_length=50, blank=True)
    substitution_reason = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.quantity}x {self.name} [{self.status}]"

    class Meta:
        ordering = ['name']


class PickerShift(models.Model):
    """Tracks a picker's work shift and attendance."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    picker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shifts',
    )
    shift_start = models.DateTimeField(auto_now_add=True)
    shift_end = models.DateTimeField(null=True, blank=True)
    break_start = models.DateTimeField(null=True, blank=True)
    break_end = models.DateTimeField(null=True, blank=True)
    
    # Aggregated metrics for the shift
    total_pick_time_minutes = models.PositiveIntegerField(default=0)
    total_items_picked = models.PositiveIntegerField(default=0)
    total_orders_completed = models.PositiveIntegerField(default=0)
    location_check_points = models.PositiveIntegerField(default=0)
    
    device_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Shift {self.id} for {self.picker.username} - {self.shift_start}"

    class Meta:
        ordering = ['-shift_start']


class PickerLocationCheckIn(models.Model):
    """Periodic location check-ins during a shift."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shift = models.ForeignKey(PickerShift, on_delete=models.CASCADE, related_name='checkins')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy = models.FloatField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
