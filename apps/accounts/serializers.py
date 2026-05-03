from rest_framework import serializers

from .models import CustomerPreferences, CustomerSettings, UserAddress


class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = ["id", "name", "phone", "line1", "area", "landmark", "is_default"]
        read_only_fields = ["id", "is_default"]


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
