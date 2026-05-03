from rest_framework import serializers
from .models import CustomerPreferences, CustomerSettings

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
