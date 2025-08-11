from rest_framework import serializers
from .models import FlutterProject, Screen
from version.models import LocalVersion


class FlutterProjectSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    supported_language_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=LocalVersion.objects.all(),
        write_only=True,
        source='supported_languages'
    )

    class Meta:
        model = FlutterProject
        fields = [
            'id', 'name', 'description', 'package_name', 'user',
            'app_version', 'supported_languages', 'supported_language_ids',
            'default_language', 'app_icon', 'primary_color', 'secondary_color',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

    def validate_package_name(self, value):
        user = self.context['request'].user
        qs = FlutterProject.objects.filter(package_name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Package name already exists")
        return value


class ScreenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Screen
        fields = [
            'id', 'project', 'name', 'route', 'is_home',
            'ui_structure', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_ui_structure(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("UI structure must be a dictionary")
        if value and 'type' not in value:
            raise serializers.ValidationError("UI structure must have a 'type' field")
        return value