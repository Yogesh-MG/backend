"""
Reusable role-based permission classes for POS endpoints.
"""
from rest_framework.permissions import BasePermission


class IsPosOperator(BasePermission):
    """Only authenticated POS_OPERATOR or ADMIN users."""
    allowed_roles = ["POS_OPERATOR"]
    message = "Only POS operators can access this endpoint."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == "ADMIN":
            return True
        return request.user.role in self.allowed_roles
