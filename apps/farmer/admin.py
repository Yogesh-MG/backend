"""Farmer app admin registration."""
from django.contrib import admin
from .models import FarmerMedia, FarmerPayout, FarmerOTP


@admin.register(FarmerMedia)
class FarmerMediaAdmin(admin.ModelAdmin):
    list_display = ('farmer', 'type', 'is_approved', 'created_at')
    list_filter = ('type', 'is_approved')
    search_fields = ('farmer__user__username',)


@admin.register(FarmerPayout)
class FarmerPayoutAdmin(admin.ModelAdmin):
    list_display = ('farmer', 'amount', 'status', 'created_at', 'completed_at')
    list_filter = ('status',)
    search_fields = ('farmer__user__username',)


@admin.register(FarmerOTP)
class FarmerOTPAdmin(admin.ModelAdmin):
    list_display = ('phone', 'otp', 'is_verified', 'created_at', 'expires_at')
    list_filter = ('is_verified',)
    search_fields = ('phone',)
