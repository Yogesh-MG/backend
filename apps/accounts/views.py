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
from django.utils import timezone
from datetime import timedelta
from .models import CustomerPreferences, CustomerSettings, User, OtpCode, DeviceAuthKey
from apps.delivery.models import DeliveryAddress
from apps.delivery.serializers import DeliveryAddressSerializer
from .serializers import (
    CustomerPreferencesSerializer, CustomerSettingsSerializer, UserSerializer,
    SendOtpSerializer, VerifyOtpSerializer, OtpResponseSerializer, AuthResponseSerializer,
    CompleteProfileSerializer
)


def _set_auth_cookies(response, access_token: str, refresh_token: str, is_app_request: bool = False):
    """Helper: attach both JWT cookies to a response."""
    cookie_kwargs = dict(
        secure=settings.JWT_AUTH_COOKIE_SECURE,
        httponly=settings.JWT_AUTH_COOKIE_HTTP_ONLY,
        samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
        path=settings.JWT_AUTH_COOKIE_PATH,
    )
    
    # Set expiration based on whether the request came from the mobile/desktop App
    if is_app_request:
        access_max_age = 30 * 24 * 3600  # 30 days
        refresh_max_age = 90 * 24 * 3600 # 90 days
    else:
        access_max_age = 3600            # 1 hour
        refresh_max_age = 86400          # 1 day

    response.set_cookie(
        key=settings.JWT_AUTH_COOKIE,
        value=access_token,
        max_age=access_max_age,
        **cookie_kwargs,
    )
    response.set_cookie(
        key=settings.JWT_AUTH_REFRESH_COOKIE,
        value=refresh_token,
        max_age=refresh_max_age,
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

        # Detect platform from custom header
        platform = request.headers.get('X-App-Platform')
        is_app_request = platform in ['PickerApp', 'DeliveryApp', 'FarmerApp']
        
        refresh = RefreshToken.for_user(user)
        
        # Override token lifetime if request comes from the operational App
        if is_app_request:
            refresh.set_exp(lifetime=timedelta(days=90))
            refresh.access_token.set_exp(lifetime=timedelta(days=30))

        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        is_profile_complete = hasattr(user, 'delivery_partner_profile') or user.first_name

        response = Response({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'is_profile_complete': is_profile_complete,
            },
            'access': access_token,
            'refresh': refresh_token,
        })

        _set_auth_cookies(response, access_token, refresh_token, is_app_request=is_app_request)
        return response


@method_decorator(csrf_exempt, name='dispatch')
class CookieTokenRefreshView(APIView):
    """
    Refresh — reads the refresh token from cookie, issues a new access token,
    and rotates the refresh token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # Detect platform from custom header
        platform = request.headers.get('X-App-Platform')
        is_app_request = platform in ['PickerApp', 'DeliveryApp', 'FarmerApp']

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
            
            # Maintain the long lifetime if this is an App request
            if is_app_request:
                refresh.set_exp(lifetime=timedelta(days=90))
                refresh.access_token.set_exp(lifetime=timedelta(days=30))

            new_access = str(refresh.access_token)
            new_refresh = str(refresh)

            response = Response({
                'message': 'Token refreshed',
                'access': new_access,
                'refresh': new_refresh,
            })
            _set_auth_cookies(response, new_access, new_refresh, is_app_request=is_app_request)
            return response

        except (TokenError, InvalidToken):
            return Response(
                {'error': 'Invalid or expired refresh token'},
                status=status.HTTP_401_UNAUTHORIZED,
            )


@method_decorator(csrf_exempt, name='dispatch')
class CookieLogoutView(APIView):
    """Logout — clears auth cookies."""
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = (
            request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
            or request.data.get('refresh')
        )

        if raw_refresh:
            try:
                token = RefreshToken(raw_refresh)
                token.blacklist()
            except (TokenError, InvalidToken):
                pass

        response = Response({'message': 'Logged out successfully'})
        response.delete_cookie(settings.JWT_AUTH_COOKIE, path=settings.JWT_AUTH_COOKIE_PATH)
        response.delete_cookie(settings.JWT_AUTH_REFRESH_COOKIE, path=settings.JWT_AUTH_COOKIE_PATH)
        return response


@method_decorator(csrf_exempt, name='dispatch')
class CurrentUserView(APIView):
    """Return the authenticated user's profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class CustomerProfileDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get_profile_parts(self, user):
        address = user.delivery_addresses.filter(is_default=True).first() or user.delivery_addresses.first()
        preferences, _ = CustomerPreferences.objects.get_or_create(user=user)
        customer_settings, _ = CustomerSettings.objects.get_or_create(user=user)
        return address, preferences, customer_settings

    def get(self, request):
        address, preferences, customer_settings = self.get_profile_parts(request.user)
        return Response({
            "address": DeliveryAddressSerializer(address).data if address else {
                "title": "",
                "address_line": "",
                "address_type": "HOME",
                "is_default": False,
            },
            "preferences": CustomerPreferencesSerializer(preferences).data,
            "settings": CustomerSettingsSerializer(customer_settings).data,
        })

    def patch(self, request):
        user = request.user
        response_data = {}

        if "address" in request.data:
            address = user.delivery_addresses.filter(is_default=True).first()
            if not address:
                address = DeliveryAddress(user=user, is_default=True)

            serializer = DeliveryAddressSerializer(address, data=request.data["address"], partial=True)
            serializer.is_valid(raise_exception=True)
            user.delivery_addresses.exclude(pk=address.pk).update(is_default=False)
            serializer.save(user=user, is_default=True)
            response_data["address"] = serializer.data

        if "preferences" in request.data:
            preferences, _ = CustomerPreferences.objects.get_or_create(user=user)
            serializer = CustomerPreferencesSerializer(preferences, data=request.data["preferences"], partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=user)
            response_data["preferences"] = serializer.data

        if "settings" in request.data:
            customer_settings, _ = CustomerSettings.objects.get_or_create(user=user)
            serializer = CustomerSettingsSerializer(customer_settings, data=request.data["settings"], partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=user)
            response_data["settings"] = serializer.data

        if not response_data:
            return Response({"detail": "Send address, preferences, or settings to update."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(response_data)


@method_decorator(csrf_exempt, name='dispatch')
class SendOtpView(APIView):
    """Send OTP to a phone number for delivery partner authentication."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOtpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.validated_data['phone'].strip()

        # Invalidate old OTPs
        OtpCode.objects.filter(phone_number=phone, is_verified=False).update(is_verified=True)

        # Create new OTP
        otp = OtpCode.create_otp(phone)

        # In production, integrate with SMS service (Twilio, AWS SNS, etc.)
        # For now, log it for development
        print(f"DEBUG: OTP for {phone}: {otp.code}")

        response_data = {
            'phone': phone,
            'message': f'OTP sent to {phone}. Valid for 10 minutes.'
        }
        if settings.DEBUG:
            response_data['otp'] = otp.code

        serializer = OtpResponseSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class VerifyOtpView(APIView):
    """Verify OTP and issue device auth key for delivery partner."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.validated_data['phone'].strip()
        otp_code = serializer.validated_data['otp'].strip()
        device_name = serializer.validated_data.get('device_name', '').strip()
        device_identifier = serializer.validated_data.get('device_identifier', '').strip()

        # Get the latest OTP for this phone
        otp = OtpCode.objects.filter(phone_number=phone, is_verified=False).order_by('-created_at').first()

        if not otp:
            return Response(
                {'error': 'No OTP found for this phone number'},
                status=status.HTTP_404_NOT_FOUND
            )

        if otp.is_expired():
            return Response(
                {'error': 'OTP has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not otp.is_valid():
            return Response(
                {'error': 'OTP is no longer valid or too many attempts'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp.code != otp_code:
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
            print(f"DEBUG: OTP mismatch for {phone}. Expected: '{otp.code}', Got: '{otp_code}'")
            return Response(
                {'error': 'Invalid OTP'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # OTP is valid, mark as verified
        otp.is_verified = True
        otp.save(update_fields=['is_verified'])

        # Find or create user with this phone number
        user = User.objects.filter(phone_number=phone).first()

        platform = request.headers.get('X-App-Platform', 'DeliveryApp')
        is_consumer = platform == 'ConsumerApp'

        if not user:
            # Create new user
            import secrets
            role = 'CUSTOMER' if is_consumer else 'DELIVERY'
            username_base = f"{role.lower()}_{phone}"
            username = username_base
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{username_base}_{counter}"
                counter += 1

            temp_password = secrets.token_urlsafe(12)
            user = User.objects.create_user(
                username=username,
                phone_number=phone,
                role=role,
                is_verified=True
            )
            user.set_password(temp_password)
            user.save()

        # Create device auth key (useful for persistence)
        device_key = DeviceAuthKey.create_device_key(
            user=user,
            device_name=device_name,
            device_identifier=device_identifier,
            validity_days=90
        )

        # Also issue standard JWT tokens for the web/consumer app
        refresh = RefreshToken.for_user(user)
        
        # Override token lifetime if request comes from an operational App
        if not is_consumer:
            refresh.set_exp(lifetime=timedelta(days=90))
            refresh.access_token.set_exp(lifetime=timedelta(days=30))

        response_data = {
            'device_auth_key': device_key.key,
            'device_auth_key_expires': device_key.expires_at.isoformat(),
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        }

        # Use _set_auth_cookies to handle browser-based session
        response = Response(response_data, status=status.HTTP_200_OK)
        _set_auth_cookies(response, str(refresh.access_token), str(refresh), is_app_request=not is_consumer)
        
        return response


@method_decorator(csrf_exempt, name='dispatch')
class CompleteProfileView(APIView):
    """First-time profile completion — collect name, DOB, email after OTP login."""
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = CompleteProfileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        data = serializer.validated_data

        user.first_name = data['first_name']
        user.last_name = data.get('last_name', '')
        if data.get('email'):
            user.email = data['email']
        if data.get('date_of_birth'):
            user.date_of_birth = data['date_of_birth']

        user.save(update_fields=['first_name', 'last_name', 'email', 'date_of_birth'])

        return Response({
            'message': 'Profile completed successfully',
            'user': UserSerializer(user).data,
        })
