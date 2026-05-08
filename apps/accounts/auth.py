# apps/accounts/auth.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from django.utils import timezone
from .models import DeviceAuthKey, User


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads the access token from an HttpOnly
    cookie before falling back to the standard Authorization header.

    This enables seamless browser-based auth (cookie) while still supporting
    direct API calls or mobile clients that send a Bearer token in the header.
    """

    def authenticate(self, request):
        access_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)

        if access_token:
            try:
                validated_token = self.get_validated_token(access_token)
                user = self.get_user(validated_token)
                return (user, validated_token)
            except Exception:
                # Cookie token is invalid/expired — fall through so the
                # interceptor can call /token/refresh/ and retry.
                return None

        # Fall back to standard Bearer token header (for direct API / CLI calls)
        return super().authenticate(request)


class DeviceAuthKeyAuthentication(TokenAuthentication):
    """
    Device-based authentication for delivery partners using long-lived device auth keys.
    
    Reads the device auth key from the Authorization header (Bearer token format)
    and validates that it exists, hasn't expired, and belongs to a DELIVERY user.
    """
    keyword = 'Bearer'

    def authenticate(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', '').split()
        
        if len(auth) != 2 or auth[0].lower() != self.keyword.lower():
            return None

        try:
            device_key_str = auth[1]
        except (IndexError, ValueError):
            raise AuthenticationFailed('Invalid token header.')

        return self.authenticate_credentials(device_key_str)

    def authenticate_credentials(self, key):
        try:
            device_key = DeviceAuthKey.objects.select_related('user').get(key=key, is_active=True)
        except DeviceAuthKey.DoesNotExist:
            raise AuthenticationFailed('Invalid or inactive device key.')

        if device_key.is_expired():
            raise AuthenticationFailed('Device key has expired.')

        user = device_key.user

        if user.role != 'DELIVERY':
            raise AuthenticationFailed('This device key is not for a delivery partner.')

        if not user.is_active:
            raise AuthenticationFailed('User account is inactive.')

        # Update last_used timestamp
        device_key.mark_used()

        return (user, device_key)

