"""
Reusable role-based permission classes for the FreshOn ecosystem.
Usage:
    from apps.picker.permissions import IsPickerUser
    permission_classes = [IsPickerUser]
"""
from rest_framework.permissions import BasePermission


class RolePermission(BasePermission):
    """Base class for role-gated permissions."""
    allowed_roles: list[str] = []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Admins always have access
        if request.user.role == "ADMIN":
            return True
        return request.user.role in self.allowed_roles


class IsPickerUser(RolePermission):
    """Only authenticated PICKER or ADMIN users."""
    allowed_roles = ["PICKER"]
    message = "Only picker users can access this endpoint."
