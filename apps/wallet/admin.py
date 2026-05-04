from django.contrib import admin
from .models import Wallet, WalletTransaction, WalletTopup, Partnership, Referral


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'tier', 'created_at')
    list_filter = ('tier', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Balance', {'fields': ('balance', 'tier')}),
        ('Partnership Tracking', {'fields': ('last_monthly_credit_date', 'last_loyalty_bonus_date')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'reason', 'balance_before', 'balance_after', 'created_at')
    list_filter = ('reason', 'created_at')
    search_fields = ('wallet__user__username',)
    readonly_fields = ('created_at', 'wallet', 'amount', 'reason', 'balance_before', 'balance_after')
    
    fieldsets = (
        ('Wallet', {'fields': ('wallet',)}),
        ('Transaction', {'fields': ('amount', 'reason', 'balance_before', 'balance_after')}),
        ('Related Records', {'fields': ('related_order', 'related_topup', 'related_referral')}),
        ('Notes', {'fields': ('notes',)}),
        ('Timestamp', {'fields': ('created_at',)}),
    )
    
    def has_delete_permission(self, request):
        # Prevent deletion of transaction records (immutable ledger)
        return False


@admin.register(WalletTopup)
class WalletTopupAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'status', 'razorpay_payment_id', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('wallet__user__username', 'razorpay_order_id', 'razorpay_payment_id')
    readonly_fields = ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Wallet', {'fields': ('wallet',)}),
        ('Amount', {'fields': ('amount',)}),
        ('Status', {'fields': ('status',)}),
        ('Razorpay', {'fields': ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(Partnership)
class PartnershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'tier', 'invested_amount', 'start_date', 'refund_requested')
    list_filter = ('tier', 'refund_requested', 'start_date')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'start_date')
    
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Partnership Details', {'fields': ('tier', 'invested_amount')}),
        ('Credit Configuration', {'fields': ('monthly_credit_percentage', 'annual_loyalty_percentage')}),
        ('Refund', {'fields': ('refund_requested', 'refund_approved_date')}),
        ('Timestamps', {'fields': ('start_date', 'created_at', 'updated_at')}),
    )


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'referee', 'bonus_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('referrer__username', 'referee__username', 'referral_code')
    readonly_fields = ('referral_code', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Referral', {'fields': ('referrer', 'referee', 'referral_code')}),
        ('Bonus', {'fields': ('bonus_amount', 'bonus_credited_date')}),
        ('Status', {'fields': ('status', 'first_order')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
