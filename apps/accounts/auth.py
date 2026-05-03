# apps/accounts/auth.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings


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
