"""
Reusable role-based permission classes for farmer endpoints.
"""
from rest_framework.permissions import BasePermission


class IsFarmerUser(BasePermission):
    """Only authenticated FARMER or ADMIN users."""
    allowed_roles = ["FARMER"]
    message = "Only farmer users can access this endpoint."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == "ADMIN":
            return True
        return request.user.role in self.allowed_roles
