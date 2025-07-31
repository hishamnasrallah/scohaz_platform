from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import FlutterProject, Screen, ComponentTemplate
from version.models import Version, LocalVersion
import re

User = get_user_model()


class LocalVersionSerializer(serializers.ModelSerializer):
    """Serializer for LocalVersion model from version app"""
    class Meta:
        model = LocalVersion
        fields = ['id', 'lang', 'active_ind']


class ScreenSerializer(serializers.ModelSerializer):
    """Serializer for Screen model"""
    class Meta:
        model = Screen
        fields = ['id', 'name', 'route', 'is_home', 'ui_structure', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_ui_structure(self, value):
        """Validate UI structure JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("UI structure must be a JSON object")

        # Validate required fields
        if 'type' not in value:
            raise serializers.ValidationError("UI structure must have a 'type' field")

        return value

    def validate_route(self, value):
        """Validate route format"""
        if not value.startswith('/'):
            raise serializers.ValidationError("Route must start with '/'")

        # Check for valid route characters
        if not re.match(r'^/[a-zA-Z0-9_/-]*$', value):
            raise serializers.ValidationError("Route contains invalid characters")

        return value


class FlutterProjectSerializer(serializers.ModelSerializer):
    """Main serializer for FlutterProject model"""
    screens = ScreenSerializer(many=True, read_only=True, source='screen_set')
    supported_languages = LocalVersionSerializer(many=True, read_only=True)
    app_version = serializers.SerializerMethodField()
    user = serializers.StringRelatedField(read_only=True)
    screen_count = serializers.SerializerMethodField()
    build_count = serializers.SerializerMethodField()

    class Meta:
        model = FlutterProject
        fields = [
            'id', 'name', 'package_name', 'description', 'user',
            'app_version', 'supported_languages', 'default_language',
            'ui_structure', 'screens', 'screen_count', 'build_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_app_version(self, obj):
        """Get version information"""
        if obj.app_version:
            return {
                'id': obj.app_version.id,
                'version_number': obj.app_version.version_number,
                'operating_system': obj.app_version.operating_system
            }
        return None

    def get_screen_count(self, obj):
        """Get number of screens in project"""
        return obj.screen_set.count()

    def get_build_count(self, obj):
        """Get number of builds for project"""
        return obj.build_set.count()

    def validate_package_name(self, value):
        """Validate package name follows reverse domain format"""
        pattern = r'^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*)+$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Package name must follow reverse domain format (e.g., com.example.app)"
            )
        return value

    def validate_ui_structure(self, value):
        """Validate project-level UI structure"""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("UI structure must be a JSON object")
        return value or {}


class FlutterProjectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for project lists"""
    screen_count = serializers.SerializerMethodField()
    build_count = serializers.SerializerMethodField()
    latest_build_status = serializers.SerializerMethodField()

    class Meta:
        model = FlutterProject
        fields = [
            'id', 'name', 'package_name', 'description',
            'screen_count', 'build_count', 'latest_build_status',
            'created_at', 'updated_at'
        ]

    def get_screen_count(self, obj):
        return obj.screen_set.count()

    def get_build_count(self, obj):
        return obj.build_set.count()

    def get_latest_build_status(self, obj):
        latest_build = obj.build_set.order_by('-created_at').first()
        if latest_build:
            return {
                'status': latest_build.status,
                'created_at': latest_build.created_at
            }
        return None


class ComponentTemplateSerializer(serializers.ModelSerializer):
    """Serializer for ComponentTemplate model"""
    class Meta:
        model = ComponentTemplate
        fields = [
            'id', 'name', 'category', 'flutter_widget',
            'properties_schema', 'preview_image', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SetVersionSerializer(serializers.Serializer):
    """Serializer for setting project version"""
    version_number = serializers.CharField(max_length=20)
    operating_system = serializers.CharField(max_length=50, default='Android')

    def validate_version_number(self, value):
        """Validate version number format"""
        pattern = r'^\d+\.\d+\.\d+$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Version number must follow semantic versioning (e.g., 1.0.0)"
            )
        return value


class AddLanguageSerializer(serializers.Serializer):
    """Serializer for adding language support"""
    language = serializers.CharField(max_length=10)

    def validate_language(self, value):
        """Validate language code exists in LocalVersion"""
        if not LocalVersion.objects.filter(lang=value, active_ind=True).exists():
            raise serializers.ValidationError(
                f"Language '{value}' is not available or not active"
            )
        return value


class GeneratePreviewSerializer(serializers.Serializer):
    """Serializer for code preview generation"""
    ui_structure = serializers.JSONField()
    screen_name = serializers.CharField(max_length=100, default='PreviewScreen')

    def validate_ui_structure(self, value):
        """Validate UI structure for preview"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("UI structure must be a JSON object")

        if 'type' not in value:
            raise serializers.ValidationError("UI structure must have a 'type' field")

        return value