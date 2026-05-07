"""POS app admin registration."""
from django.contrib import admin
from .models import (
    PosEmployee, PosCustomer, PosShift,
    PosTransaction, PosTransactionItem, PosTender, PosWastageLog,
)


@admin.register(PosEmployee)
class PosEmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('employee_id', 'user__username')


@admin.register(PosCustomer)
class PosCustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'tier', 'points', 'is_pride')
    list_filter = ('tier', 'is_pride')
    search_fields = ('name', 'phone')


class PosTransactionItemInline(admin.TabularInline):
    model = PosTransactionItem
    extra = 0


class PosTenderInline(admin.TabularInline):
    model = PosTender
    extra = 0


@admin.register(PosShift)
class PosShiftAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'is_open', 'opening_cash', 'total_sales', 'txn_count', 'started_at')
    list_filter = ('is_open',)
    readonly_fields = ('id',)


@admin.register(PosTransaction)
class PosTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'shift', 'customer', 'method', 'total', 'created_at')
    list_filter = ('method',)
    inlines = [PosTransactionItemInline, PosTenderInline]
    readonly_fields = ('id',)


@admin.register(PosWastageLog)
class PosWastageLogAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'reason', 'unit_price', 'shift', 'created_at')
    list_filter = ('reason',)
    search_fields = ('name', 'pid')
