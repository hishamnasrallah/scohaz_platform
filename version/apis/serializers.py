from rest_framework import serializers
from version.models import LocalVersion


class LocalVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalVersion
        fields = ['lang', 'version_number', 'active_ind']
