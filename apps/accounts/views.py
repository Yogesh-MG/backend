# apps/accounts/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import authenticate
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import User


def _set_auth_cookies(response, access_token: str, refresh_token: str):
    """Helper: attach both JWT cookies to a response."""
    cookie_kwargs = dict(
        secure=settings.JWT_AUTH_COOKIE_SECURE,
        httponly=settings.JWT_AUTH_COOKIE_HTTP_ONLY,
        samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
        path=settings.JWT_AUTH_COOKIE_PATH,
    )
    response.set_cookie(
        key=settings.JWT_AUTH_COOKIE,
        value=access_token,
        max_age=3600,  # 1 hour — mirrors SIMPLE_JWT ACCESS_TOKEN_LIFETIME
        **cookie_kwargs,
    )
    response.set_cookie(
        key=settings.JWT_AUTH_REFRESH_COOKIE,
        value=refresh_token,
        max_age=86400,  # 1 day — mirrors SIMPLE_JWT REFRESH_TOKEN_LIFETIME
        **cookie_kwargs,
    )


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    """Registration endpoint for new customers."""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Username already exists'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='CUSTOMER',
        )

        return Response(
            {
                'message': 'User registered successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                },
            },
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name='dispatch')
class CookieTokenObtainView(APIView):
    """Login — validates credentials and sets JWT tokens as HttpOnly cookies."""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user is None:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = Response({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
            },
            # Included in body for explicit non-cookie clients, including the
            # Tauri APK. Web clients can still use the HttpOnly cookie below.
            'access': access_token,
            'refresh': refresh_token,
        })

        _set_auth_cookies(response, access_token, refresh_token)
        return response


@method_decorator(csrf_exempt, name='dispatch')
class CookieTokenRefreshView(APIView):
    """
    Refresh — reads the refresh token from cookie, issues a new access token,
    and (because ROTATE_REFRESH_TOKENS=True) also rotates the refresh token.
    The old refresh token is automatically blacklisted by simplejwt.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # Cookie-first, body fallback for explicit non-cookie clients.
        raw_refresh = (
            request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
            or request.data.get('refresh')
        )

        if not raw_refresh:
            return Response(
                {'error': 'Refresh token not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh = RefreshToken(raw_refresh)

            # Calling refresh.access_token triggers rotation when
            # ROTATE_REFRESH_TOKENS=True — simplejwt blacklists the old token.
            new_access = str(refresh.access_token)
            # After rotation, `refresh` now represents the *new* refresh token.
            new_refresh = str(refresh)

            response = Response({
                'message': 'Token refreshed',
                # Return new tokens in body so explicit non-cookie clients can
                # stay in sync with refresh-token rotation.
                'access': new_access,
                'refresh': new_refresh,
            })
            _set_auth_cookies(response, new_access, new_refresh)
            return response

        except (TokenError, InvalidToken):
            return Response(
                {'error': 'Invalid or expired refresh token'},
                status=status.HTTP_401_UNAUTHORIZED,
            )


@method_decorator(csrf_exempt, name='dispatch')
class CookieLogoutView(APIView):
    """
    Logout — blacklists the refresh token so it cannot be reused,
    then clears both auth cookies from the client.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = (
            request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
            or request.data.get('refresh')
        )

        if raw_refresh:
            try:
                token = RefreshToken(raw_refresh)
                token.blacklist()  # Adds to OutstandingToken / BlacklistedToken tables
            except (TokenError, InvalidToken):
                # Already invalid/blacklisted — treat as successful logout
                pass

        response = Response({'message': 'Logged out successfully'})
        response.delete_cookie(settings.JWT_AUTH_COOKIE, path=settings.JWT_AUTH_COOKIE_PATH)
        response.delete_cookie(settings.JWT_AUTH_REFRESH_COOKIE, path=settings.JWT_AUTH_COOKIE_PATH)
        return response


@method_decorator(csrf_exempt, name='dispatch')
class CurrentUserView(APIView):
    """Return the authenticated user's profile — used by the useMe hook."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'is_verified': user.is_verified,
        })
