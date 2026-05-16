"""POS app admin registration."""
from django.contrib import admin
from .models import (
    PosEmployee, PosCustomer, PosShift,
    PosTransaction, PosTransactionItem, PosTender, PosWastageLog,
    PosSettings, CompanyProfile, PosInvoiceCounter,
)


@admin.register(PosEmployee)
class PosEmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'is_active', 'is_manager', 'created_at')
    list_filter = ('is_active', 'is_manager')
    search_fields = ('employee_id', 'user__username')


@admin.register(PosCustomer)
class PosCustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'tier', 'points', 'is_pride')
    list_filter = ('tier', 'is_pride')
    search_fields = ('name', 'phone')


@admin.register(PosSettings)
class PosSettingsAdmin(admin.ModelAdmin):
    list_display = ('pride_discount_pct', 'rounding_enabled', 'rounding_slab', 'max_manual_discount_pct', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'gstin', 'pan', 'email', 'created_at')
    search_fields = ('name', 'gstin', 'pan')


@admin.register(PosInvoiceCounter)
class PosInvoiceCounterAdmin(admin.ModelAdmin):
    list_display = ('year', 'last_number')
    readonly_fields = ('year', 'last_number')


class PosTransactionItemInline(admin.TabularInline):
    model = PosTransactionItem
    extra = 0


class PosTenderInline(admin.TabularInline):
    model = PosTender
    extra = 0


@admin.register(PosShift)
class PosShiftAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'is_open', 'opening_cash', 'total_sales', 'txn_count', 'rounding_loss', 'started_at')
    list_filter = ('is_open',)
    readonly_fields = ('id',)


@admin.register(PosTransaction)
class PosTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'shift', 'customer', 'method', 'total', 'manual_discount_amount', 'rounding_adjustment', 'is_anonymous', 'is_b2b', 'invoice_number', 'created_at')
    list_filter = ('method', 'is_anonymous', 'is_b2b', 'transaction_type')
    inlines = [PosTransactionItemInline, PosTenderInline]
    readonly_fields = ('id',)
    search_fields = ('invoice_number', 'id')


@admin.register(PosWastageLog)
class PosWastageLogAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'reason', 'unit_price', 'shift', 'created_at')
    list_filter = ('reason',)
    search_fields = ('name', 'pid')
