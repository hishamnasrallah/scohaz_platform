from rest_framework import serializers

from license_subscription_manager.models import Subscription, License


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['id', 'client', 'plan', 'start_date', 'end_date', 'status']


class LicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = License
        fields = ['id', 'project_id', 'client', 'license_key', 'status', 'valid_until']
