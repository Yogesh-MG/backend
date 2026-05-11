"""
POS (Point of Sale) app models.

PosEmployee       — POS terminal user with PIN-based auth.
PosShift          — shift tracking (open/close with cash reconciliation).
PosTransaction    — a completed walk-in sale at the counter.
PosTransactionItem — individual product within a POS transaction.
PosWastageLog     — spoiled/damaged/expired product logging.
PosCustomer       — walk-in customer for loyalty/PRIDE integration.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class PosEmployee(models.Model):
    """POS terminal employee — linked to a POS_OPERATOR user."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pos_employee',
    )
    employee_id = models.CharField(max_length=20, unique=True, help_text="e.g. EMP-001")
    pin = models.CharField(max_length=6, help_text="Numeric PIN for quick terminal login")
    is_active = models.BooleanField(default=True)
    is_manager = models.BooleanField(default=False, help_text="Can authorize refunds and returns")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"POS: {self.employee_id} ({self.user.get_full_name() or self.user.username})"

    class Meta:
        ordering = ['employee_id']
        verbose_name = "POS Employee"
        verbose_name_plural = "POS Employees"


class PosCustomer(models.Model):
    """Walk-in customer registered at POS for loyalty tracking."""
    TIER_CHOICES = [
        ('Bronze', 'Bronze'),
        ('Silver', 'Silver'),
        ('Gold', 'Gold'),
        ('Platinum', 'Platinum'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Optionally linked to an existing FreshOn user
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pos_customer',
    )
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='Bronze')
    points = models.PositiveIntegerField(default=0)
    is_pride = models.BooleanField(default=False, help_text="Whether customer is a PRIDE partner")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.phone}) — {self.tier}"

    class Meta:
        ordering = ['name']
        verbose_name = "POS Customer"
        verbose_name_plural = "POS Customers"


class PosShift(models.Model):
    """Tracks a POS terminal shift from open to close."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        PosEmployee,
        on_delete=models.CASCADE,
        related_name='shifts',
    )
    opening_cash = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    closing_cash = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cash_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    txn_count = models.PositiveIntegerField(default=0)
    is_open = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        status = "🟢 Open" if self.is_open else "🔴 Closed"
        return f"Shift {self.id} — {self.employee.employee_id} ({status})"

    @property
    def variance(self):
        """Cash variance = closing_cash - (opening_cash + cash_sales)."""
        if self.closing_cash is None:
            return 0
        return float(self.closing_cash) - (float(self.opening_cash) + float(self.cash_sales))

    class Meta:
        ordering = ['-started_at']


class PosTransaction(models.Model):
    """A completed point-of-sale transaction (sale or return)."""
    TRANSACTION_TYPES = [
        ('SALE', 'Sale'),
        ('RETURN', 'Return'),
    ]

    PAYMENT_METHODS = [
        ('Cash', 'Cash'),
        ('UPI', 'UPI'),
        ('Card', 'Card'),
        ('Sodexo', 'Sodexo'),
        ('Split', 'Split Payment'),
    ]

    RECEIPT_CHOICES = [
        ('Print', 'Print'),
        ('WhatsApp', 'WhatsApp'),
        ('SMS', 'SMS'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shift = models.ForeignKey(
        PosShift,
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    customer = models.ForeignKey(
        PosCustomer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
    )
    transaction_type = models.CharField(
        max_length=10, choices=TRANSACTION_TYPES, default='SALE',
    )
    related_transaction = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='returns',
        help_text='For RETURN type: links to the original SALE transaction',
    )
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='Cash')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    member_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    surcharge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    receipt_delivery = models.CharField(max_length=20, choices=RECEIPT_CHOICES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"POS Txn {self.id} — ₹{self.total} ({self.method})"

    class Meta:
        ordering = ['-created_at']


class PosTransactionItem(models.Model):
    """Individual product line item within a POS transaction."""
    transaction = models.ForeignKey(
        PosTransaction,
        on_delete=models.CASCADE,
        related_name='items',
    )
    # Snapshot fields (denormalized for receipt permanence)
    pid = models.CharField(max_length=50, help_text="Product ID from inventory")
    name = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    weighed = models.BooleanField(default=False)
    quantity = models.DecimalField(max_digits=8, decimal_places=3, help_text="Supports fractional for weighed items")
    member_eligible = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.quantity}x {self.name} @ ₹{self.unit_price}"

    class Meta:
        ordering = ['name']


class PosTender(models.Model):
    """Individual payment tender within a split-payment transaction."""
    transaction = models.ForeignKey(
        PosTransaction,
        on_delete=models.CASCADE,
        related_name='tenders',
    )
    method = models.CharField(max_length=20, choices=PosTransaction.PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.method}: ₹{self.amount}"


class PosWastageLog(models.Model):
    """Tracks spoiled/damaged/expired product wastage at the POS."""
    REASON_CHOICES = [
        ('Spoiled', 'Spoiled'),
        ('Damaged', 'Damaged'),
        ('Expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shift = models.ForeignKey(
        PosShift,
        on_delete=models.CASCADE,
        related_name='wastage_logs',
    )
    pid = models.CharField(max_length=50, help_text="Product ID from inventory")
    name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=8, decimal_places=3)
    weighed = models.BooleanField(default=False)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wastage: {self.quantity}x {self.name} ({self.reason})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "POS Wastage Log"
        verbose_name_plural = "POS Wastage Logs"
