from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, FarmerProfile

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

