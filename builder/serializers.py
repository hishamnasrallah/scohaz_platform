from rest_framework import serializers
from .models import WidgetMapping, GenerationConfig
from projects.models import FlutterProject


class WidgetMappingSerializer(serializers.ModelSerializer):
    """Serializer for WidgetMapping model"""
    class Meta:
        model = WidgetMapping
        fields = [
            'id', 'ui_type', 'flutter_widget', 'properties_mapping',
            'import_statements', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GenerationConfigSerializer(serializers.ModelSerializer):
    """Serializer for GenerationConfig model"""
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = GenerationConfig
        fields = [
            'id', 'project', 'project_name', 'config_data',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'project_name', 'created_at', 'updated_at']

    def validate_config_data(self, value):
        """Validate configuration data structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Config data must be a JSON object")

        # Validate required config fields
        required_fields = ['theme', 'dependencies', 'assets']
        for field in required_fields:
            if field not in value:
                value[field] = {}  # Set defaults

        return value


class CodePreviewSerializer(serializers.Serializer):
    """Serializer for code preview generation"""
    project_id = serializers.IntegerField(required=False)
    screen_data = serializers.JSONField()
    include_imports = serializers.BooleanField(default=True)

    def validate_screen_data(self, value):
        """Validate screen data structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Screen data must be a JSON object")

        required_fields = ['name', 'ui_structure']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Screen data must contain '{field}' field")

        # Validate UI structure
        ui_structure = value.get('ui_structure', {})
        if not isinstance(ui_structure, dict) or 'type' not in ui_structure:
            raise serializers.ValidationError("Invalid UI structure format")

        return value

    def validate_project_id(self, value):
        """Validate project exists and belongs to user"""
        if value:
            request = self.context.get('request')
            if not FlutterProject.objects.filter(
                    id=value,
                    user=request.user
            ).exists():
                raise serializers.ValidationError("Project not found or access denied")

        return value


class GeneratedCodeSerializer(serializers.Serializer):
    """Serializer for generated code response"""
    dart_code = serializers.CharField()
    imports = serializers.ListField(child=serializers.CharField())
    widget_tree = serializers.JSONField()
    translations_used = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


class FlutterProjectStructureSerializer(serializers.Serializer):
    """Serializer for complete Flutter project structure"""
    project_id = serializers.IntegerField()
    include_translations = serializers.BooleanField(default=True)
    build_config = serializers.JSONField(required=False)

    def validate_project_id(self, value):
        """Validate project exists and has screens"""
        request = self.context.get('request')
        project = FlutterProject.objects.filter(
            id=value,
            user=request.user
        ).first()

        if not project:
            raise serializers.ValidationError("Project not found or access denied")

        if not project.screen_set.exists():
            raise serializers.ValidationError("Project has no screens to generate")

        return value


class ProjectFileSerializer(serializers.Serializer):
    """Serializer for individual project file"""
    path = serializers.CharField()
    content = serializers.CharField()
    is_binary = serializers.BooleanField(default=False)