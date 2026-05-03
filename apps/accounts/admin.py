from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomerPreferences, CustomerSettings, FarmerProfile, User, UserAddress

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_verified", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Profile Info", {"fields": ("role", "phone_number", "is_verified")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Profile Info", {"fields": ("role", "phone_number", "is_verified")}),
    )

@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "location", "rating", "speciality")


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "phone", "area", "is_default", "updated_at")
    list_filter = ("is_default", "area")
    search_fields = ("user__username", "name", "phone", "line1", "area")


@admin.register(CustomerPreferences)
class CustomerPreferencesAdmin(admin.ModelAdmin):
    list_display = ("user", "organic_only", "vegetarian", "avoid_plastic", "updated_at")
    search_fields = ("user__username", "allergens")


@admin.register(CustomerSettings)
class CustomerSettingsAdmin(admin.ModelAdmin):
    list_display = ("user", "order_updates", "offers", "weekly_summary", "private_profile", "updated_at")
    search_fields = ("user__username",)
