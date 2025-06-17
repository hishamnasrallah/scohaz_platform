from rest_framework import serializers
from version.models import LocalVersion, Version


class LocalVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalVersion
        fields = ['lang', 'version_number', 'active_ind']


class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Version
        fields = '__all__'  # Include all fields