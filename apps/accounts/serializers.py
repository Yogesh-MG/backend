from rest_framework import serializers
from .models import CustomerPreferences, CustomerSettings, User, OtpCode, DeviceAuthKey
from apps.wallet.serializers import PartnershipSerializer

class CustomerPreferencesSerializer(serializers.ModelSerializer):
    organicOnly = serializers.BooleanField(source="organic_only", required=False)
    avoidPlastic = serializers.BooleanField(source="avoid_plastic", required=False)

    class Meta:
        model = CustomerPreferences
        fields = ["organicOnly", "vegetarian", "avoidPlastic", "allergens", "notes"]


class CustomerSettingsSerializer(serializers.ModelSerializer):
    orderUpdates = serializers.BooleanField(source="order_updates", required=False)
    weeklySummary = serializers.BooleanField(source="weekly_summary", required=False)
    privateProfile = serializers.BooleanField(source="private_profile", required=False)

    class Meta:
        model = CustomerSettings
        fields = ["orderUpdates", "offers", "weeklySummary", "privateProfile"]


class UserSerializer(serializers.ModelSerializer):
    partnership = PartnershipSerializer(read_only=True)
    is_profile_complete = serializers.SerializerMethodField()
    remaining_pride_limit = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "is_verified", "partnership", "is_profile_complete", "first_name", "last_name", "date_of_birth", "phone_number", "remaining_pride_limit"]

    def get_is_profile_complete(self, obj):
        return hasattr(obj, 'delivery_partner_profile') or bool(obj.first_name)

    def get_remaining_pride_limit(self, obj):
        from apps.wallet.models import Wallet
        try:
            wallet = Wallet.objects.get(user=obj)
            # Use getattr and catch broad exceptions to handle cases where database columns aren't migrated
            return str(getattr(wallet, 'accumulated_pride_limit', '0.00'))
        except Exception:
            return '0.00'


class SendOtpSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)

    def validate_phone(self, value):
        # Validate Indian phone number (10 digits starting with 6-9)
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Phone must be 10 digits")
        if value[0] not in ['6', '7', '8', '9']:
            raise serializers.ValidationError("Invalid Indian phone number")
        return value


class VerifyOtpSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6, min_length=6)
    device_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    device_identifier = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_phone(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Phone must be 10 digits")
        return value

    def validate_otp(self, value):
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("OTP must be 6 digits")
        return value


class OtpResponseSerializer(serializers.Serializer):
    phone = serializers.CharField()
    message = serializers.CharField()
    otp = serializers.CharField(required=False)


class DeviceAuthKeyResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceAuthKey
        fields = ['key', 'device_name', 'created_at', 'expires_at']


class AuthResponseSerializer(serializers.Serializer):
    device_auth_key = serializers.CharField()
    device_auth_key_expires = serializers.CharField()
    user = UserSerializer()


class CompleteProfileSerializer(serializers.Serializer):
    """Validates first-time profile completion data."""
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
