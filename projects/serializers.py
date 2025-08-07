# File: projects/serializers.py

from rest_framework import serializers
from .models import (
    FlutterProject, ComponentTemplate, Screen,
    CanvasState, ProjectAsset, WidgetTemplate, StylePreset
)
from authentication.models import CustomUser
from version.apis.serializers import LocalVersionSerializer
from version.models import LocalVersion


class ComponentTemplateBuilderSerializer(serializers.ModelSerializer):
    """Optimized serializer for Angular builder toolbox"""

    # Extract common properties from default_properties
    display_order = serializers.SerializerMethodField()
    widget_group = serializers.SerializerMethodField()
    show_in_builder = serializers.SerializerMethodField()

    class Meta:
        model = ComponentTemplate
        fields = [
            'id', 'name', 'category', 'flutter_widget', 'icon',
            'description', 'default_properties', 'can_have_children',
            'max_children', 'display_order', 'widget_group', 'show_in_builder'
        ]

    def get_display_order(self, obj):
        """Extract display_order from default_properties"""
        return obj.default_properties.get('display_order', 999)

    def get_widget_group(self, obj):
        """Extract widget_group from default_properties"""
        return obj.default_properties.get('widget_group', 'Other')

    def get_show_in_builder(self, obj):
        """Extract show_in_builder from default_properties"""
        return obj.default_properties.get('show_in_builder', True)


class OrganizedComponentsSerializer(serializers.Serializer):
    """Serializer for organized components response"""

    def to_representation(self, components_dict):
        """
        Convert organized components dictionary to API response format
        Expected format:
        {
            "Basic Layout": [component_objects...],
            "Input Controls": [component_objects...],
            ...
        }
        """
        result = {}
        for group_name, components in components_dict.items():
            result[group_name] = ComponentTemplateBuilderSerializer(
                components, many=True, context=self.context
            ).data
        return result


# Keep existing serializers unchanged
class FlutterProjectSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    supported_languages = LocalVersionSerializer(many=True, read_only=True)
    supported_language_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=LocalVersion.objects.all(),
        write_only=True,
        source='supported_languages'
    )

    class Meta:
        model = FlutterProject
        fields = [
            'id', 'name', 'description', 'package_name',
            'user', 'app_version', 'supported_languages',
            'supported_language_ids', 'default_language',
            'app_icon', 'primary_color', 'secondary_color',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

    def validate_package_name(self, value):
        # Check if package name is unique for this user
        user = self.context['request'].user
        qs = FlutterProject.objects.filter(package_name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Package name already exists")
        return value


class ComponentTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComponentTemplate
        fields = '__all__'


class ScreenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Screen
        fields = ['id', 'project', 'name', 'route', 'is_home',
                  'ui_structure', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_ui_structure(self, value):
        """Validate UI structure format"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("UI structure must be a dictionary")

        if 'type' not in value:
            raise serializers.ValidationError("UI structure must have a 'type' field")

        # Recursive validation could be added here
        return value


class CanvasStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CanvasState
        fields = '__all__'


class ProjectAssetSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ProjectAsset
        fields = '__all__'

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return obj.url


class WidgetTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WidgetTemplate
        fields = '__all__'
        read_only_fields = ['user']


class StylePresetSerializer(serializers.ModelSerializer):
    class Meta:
        model = StylePreset
        fields = '__all__'
        read_only_fields = ['user']