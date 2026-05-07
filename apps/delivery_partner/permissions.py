"""
Reusable role-based permission classes for delivery partner endpoints.
"""
from rest_framework.permissions import BasePermission


class IsDeliveryPartner(BasePermission):
    """Only authenticated DELIVERY or ADMIN users."""
    allowed_roles = ["DELIVERY"]
    message = "Only delivery partners can access this endpoint."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == "ADMIN":
            return True
        return request.user.role in self.allowed_roles
