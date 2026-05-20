from django.db import models
from django.conf import settings
from decimal import Decimal


class Wallet(models.Model):
    """User's wallet balance and metadata."""
    TIER_CHOICES = [
        ('STANDARD', 'Standard'),
        ('PRIDE_1', 'PRIDE Tier 1 (₹1.5L)'),
        ('PRIDE_2', 'PRIDE Tier 2 (₹3L)'),
        ('PRIDE_3', 'PRIDE Tier 3 (₹5L)'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='STANDARD')
    
    # PRIDE limit tracking — accumulates monthly, never resets
    accumulated_pride_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        help_text="Total MRP value the user can buy at PRIDE discount"
    )
    
    last_monthly_credit_date = models.DateTimeField(null=True, blank=True)
    last_loyalty_bonus_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_monthly_pride_limit(self):
        """Return the monthly PRIDE limit addition based on partnership tier."""
        try:
            partnership = self.user.partnership
            if partnership.refund_requested:
                return Decimal('0.00')
            tier_limits = {
                'TIER_1': Decimal('3000.00'),
                'TIER_2': Decimal('6000.00'),
                'TIER_3': Decimal('10000.00'),
            }
            return tier_limits.get(partnership.tier, Decimal('0.00'))
        except:
            return Decimal('0.00')

    def __str__(self):
        return f"{self.user.username}'s Wallet - ₹{self.balance}"

    class Meta:
        ordering = ['-updated_at']


class WalletTransaction(models.Model):
    """Immutable audit trail of all wallet changes."""
    REASON_CHOICES = [
        ('TOPUP', 'Top-up via Card/UPI'),
        ('ORDER_PAYMENT', 'Order Payment'),
        ('ORDER_REFUND', 'Order Refund'),
        ('MONTHLY_CREDIT', 'Monthly Partnership Credit'),
        ('LOYALTY_BONUS', 'Annual Loyalty Bonus'),
        ('REFERRAL_BONUS', 'Referral Bonus'),
        ('SYSTEM_ADJUSTMENT', 'System Adjustment'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Foreign keys for context
    related_order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True)
    related_topup = models.ForeignKey('WalletTopup', on_delete=models.SET_NULL, null=True, blank=True)
    related_referral = models.ForeignKey('Referral', on_delete=models.SET_NULL, null=True, blank=True)
    
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wallet.user.username} - {self.reason} - ₹{self.amount}"

    class Meta:
        ordering = ['-created_at']


class WalletTopup(models.Model):
    """Record of wallet top-up transactions via Razorpay."""
    STATUS_CHOICES = [
        ('INITIATED', 'Initiated'),
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='topups')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INITIATED')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.wallet.user.username} - ₹{self.amount} - {self.status}"

    class Meta:
        ordering = ['-created_at']


class Partnership(models.Model):
    """PRIDE Partnership tier tracking."""
    TIER_CHOICES = [
        ('TIER_1', 'Tier 1 (₹1.5L - 30% discount + 10% monthly credit)'),
        ('TIER_2', 'Tier 2 (₹3L - Same + 5% annual bonus)'),
        ('TIER_3', 'Tier 3 (₹5L - Same + Premium perks)'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='partnership')
    tier = models.CharField(max_length=20, choices=TIER_CHOICES)
    invested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    monthly_credit_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.00'))
    annual_loyalty_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('5.00'))
    
    start_date = models.DateTimeField(auto_now_add=True)
    refund_requested = models.BooleanField(default=False)
    refund_approved_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.tier}"

    class Meta:
        ordering = ['-created_at']


class Referral(models.Model):
    """Referral tracking for bonus distribution."""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('CREDITED', 'Credited'),
        ('FAILED', 'Failed'),
    ]

    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referrals_given')
    referee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referrals_received')
    
    referral_code = models.CharField(max_length=20, unique=True)
    bonus_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    first_order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True)
    bonus_credited_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.referrer.username} -> {self.referee.username} ({self.status})"

    class Meta:
        ordering = ['-created_at']
        unique_together = ['referrer', 'referee']


class CustomerImpact(models.Model):
    """Cumulative, lifetime positive impact metrics for a conscious consumer."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='impact')
    total_water = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_soil = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_chemical = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_farmer = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_orders = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Impact (Water: {self.total_water}L, Orders: {self.total_orders})"

    class Meta:
        ordering = ['-updated_at']
