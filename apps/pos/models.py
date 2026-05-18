"""
POS (Point of Sale) app models.

PosEmployee       — POS terminal user with PIN-based auth.
PosShift          — shift tracking (open/close with cash reconciliation).
PosTransaction    — a completed walk-in sale at the counter.
PosTransactionItem — individual product within a POS transaction.
PosWastageLog     — spoiled/damaged/expired product logging.
PosCustomer       — walk-in customer for loyalty/PRIDE integration.
PosSettings       — terminal-wide configuration (discounts, rounding).
CompanyProfile    — B2B corporate client for GST invoicing.
PosInvoiceCounter — sequential tax invoice number generator.
"""
import uuid
from decimal import Decimal
from django.core.exceptions import ValidationError
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
    is_b2b_contact = models.BooleanField(default=False, help_text="Whether this customer represents a B2B business")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.phone}) — {self.tier}"

    class Meta:
        ordering = ['name']
        verbose_name = "POS Customer"
        verbose_name_plural = "POS Customers"


class PosSettings(models.Model):
    """Terminal-wide POS configuration."""
    pride_discount_pct = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal('0.3000'),
        help_text="PRIDE member discount rate (e.g. 0.30 = 30%)"
    )
    rounding_enabled = models.BooleanField(default=True, help_text="Enable cash rounding")
    rounding_slab = models.PositiveIntegerField(
        default=5, choices=[(5, '₹5'), (10, '₹10')],
        help_text="Round change up to nearest denomination"
    )
    max_manual_discount_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('5.00'),
        help_text="Maximum manual discount % without manager override"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"POS Settings — PRIDE {float(self.pride_discount_pct):.0%}, Rounding ₹{self.rounding_slab}"

    class Meta:
        verbose_name = "POS Settings"
        verbose_name_plural = "POS Settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # Enforce singleton
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        """Get or create the singleton settings record."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


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
    rounding_loss = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total rounding adjustment loss for this shift")
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


class CompanyProfile(models.Model):
    """B2B corporate client profile for GST invoicing."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    gstin = models.CharField(max_length=15, unique=True, help_text="15-character GSTIN")
    address = models.TextField(blank=True)
    pan = models.CharField(max_length=10, blank=True, help_text="10-character PAN")
    email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=15, unique=True, null=True, blank=True, help_text="Primary contact phone for auto-detection")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.gstin})"

    class Meta:
        ordering = ['name']
        verbose_name = "Company Profile"
        verbose_name_plural = "Company Profiles"


class PosInvoiceCounter(models.Model):
    """Maintains sequential tax invoice numbers for compliance."""
    year = models.PositiveIntegerField(primary_key=True)
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Tax Invoices {self.year}: {self.last_number}"

    class Meta:
        verbose_name = "POS Invoice Counter"
        verbose_name_plural = "POS Invoice Counters"

    @classmethod
    def next_invoice_number(cls, year: int | None = None) -> str:
        """Atomically increment and return the next invoice number."""
        if year is None:
            year = timezone.now().year
        from django.db import transaction
        with transaction.atomic():
            counter, _ = cls.objects.select_for_update().get_or_create(year=year, defaults={'last_number': 0})
            counter.last_number += 1
            counter.save(update_fields=['last_number'])
            return f"TAX-INV-{year}-{counter.last_number:05d}"


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
        ('Wallet', 'Wallet'),
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
    pride_limit_used = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    manual_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Manual discount % applied")
    manual_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Manual discount amount in ₹")
    discount_reason = models.TextField(blank=True, help_text="Reason for manual discount")
    discount_applied_by = models.ForeignKey(
        PosEmployee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='discounted_transactions',
        help_text="Employee who authorized the manual discount",
    )
    surcharge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rounding_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Rounding amount added to total (positive = round up)")
    total = models.DecimalField(max_digits=10, decimal_places=2)
    receipt_delivery = models.CharField(max_length=20, choices=RECEIPT_CHOICES, blank=True)
    is_anonymous = models.BooleanField(default=False, help_text="Transaction without customer identification")
    is_b2b = models.BooleanField(default=False, help_text="B2B / company purchase with GST invoice")
    company = models.ForeignKey(
        CompanyProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
    )
    invoice_number = models.CharField(max_length=30, blank=True, db_index=True, help_text="Sequential tax invoice ID")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"POS Txn {self.id} — ₹{self.total} ({self.method})"

    def clean(self):
        super().clean()
        # Validate manual discount limits against settings
        settings = PosSettings.get()
        max_pct = float(settings.max_manual_discount_pct)
        if float(self.manual_discount_percentage) > max_pct:
            # Allow manager override
            if not (self.discount_applied_by and self.discount_applied_by.is_manager):
                raise ValidationError(
                    f"Manual discount cannot exceed {max_pct}% without manager authorization."
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

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
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'), help_text="GST % at time of sale")

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
