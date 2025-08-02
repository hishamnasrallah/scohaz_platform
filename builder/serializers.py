# File: builder/serializers.py

from rest_framework import serializers
from .models import WidgetMapping


class WidgetMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = WidgetMapping
        fields = '__all__'