from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from reporting_templates.models import (
    PDFTemplate, PDFTemplateElement,
    PDFTemplateVariable, PDFGenerationLog
)

User = get_user_model()


class PDFTemplateVariableSerializer(serializers.ModelSerializer):
    """Serializer for template variables"""

    class Meta:
        model = PDFTemplateVariable
        fields = [
            'id', 'variable_key', 'display_name', 'display_name_ara',
            'description', 'data_type', 'data_source', 'default_value',
            'format_string', 'is_required'
        ]

    def validate_variable_key(self, value):
        """Ensure variable key is valid Python identifier"""
        if not value.replace('_', '').isalnum():
            raise serializers.ValidationError(
                "Variable key must contain only letters, numbers, and underscores"
            )
        return value


class PDFTemplateElementSerializer(serializers.ModelSerializer):
    """Serializer for template elements"""

    class Meta:
        model = PDFTemplateElement
        fields = [
            'id', 'element_type', 'element_key', 'x_position', 'y_position',
            'width', 'height', 'rotation', 'text_content', 'text_content_ara',
            'font_family', 'font_size', 'font_color', 'is_bold', 'is_italic',
            'is_underline', 'text_align', 'line_height', 'fill_color',
            'stroke_color', 'stroke_width', 'image_source',
            'maintain_aspect_ratio', 'table_config', 'data_source',
            'condition', 'z_index', 'is_repeatable', 'page_number', 'active_ind'
        ]

    def validate_font_color(self, value):
        """Validate hex color format"""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError("Invalid hex color format")
        return value


class PDFTemplateSerializer(serializers.ModelSerializer):
    """Main template serializer"""
    elements = PDFTemplateElementSerializer(many=True, read_only=True)
    variables = PDFTemplateVariableSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    content_type_display = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = PDFTemplate
        fields = [
            'id', 'name', 'name_ara', 'description', 'description_ara',
            'code', 'primary_language', 'supports_bilingual', 'page_size',
            'orientation', 'margin_top', 'margin_bottom', 'margin_left',
            'margin_right', 'header_enabled', 'footer_enabled',
            'watermark_enabled', 'watermark_text', 'created_by',
            'created_by_name', 'groups', 'content_type', 'content_type_display',
            'is_system_template', 'active_ind', 'created_at', 'updated_at',
            'elements', 'variables', 'can_edit', 'can_delete'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_content_type_display(self, obj):
        """Get readable content type name"""
        if obj.content_type:
            return f"{obj.content_type.app_label}.{obj.content_type.model}"
        return None

    def get_can_edit(self, obj):
        """Check if current user can edit"""
        request = self.context.get('request')
        if not request or not request.user:
            return False

        if request.user.is_superuser:
            return True

        if obj.created_by == request.user:
            return True

        return request.user.groups.filter(
            id__in=obj.groups.values_list('id', flat=True)
        ).exists()

    def get_can_delete(self, obj):
        """Check if current user can delete"""
        if obj.is_system_template:
            return False
        return self.get_can_edit(obj)


class PDFTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating templates"""
    elements = PDFTemplateElementSerializer(many=True, required=False)
    variables = PDFTemplateVariableSerializer(many=True, required=False)

    class Meta:
        model = PDFTemplate
        fields = [
            'name', 'name_ara', 'description', 'description_ara', 'code',
            'primary_language', 'supports_bilingual', 'page_size',
            'orientation', 'margin_top', 'margin_bottom', 'margin_left',
            'margin_right', 'header_enabled', 'footer_enabled',
            'watermark_enabled', 'watermark_text', 'groups', 'content_type',
            'elements', 'variables'
        ]

    def create(self, validated_data):
        elements_data = validated_data.pop('elements', [])
        variables_data = validated_data.pop('variables', [])

        # Set created_by from context
        validated_data['created_by'] = self.context['request'].user

        # Create template
        template = PDFTemplate.objects.create(**validated_data)

        # Create elements
        for element_data in elements_data:
            PDFTemplateElement.objects.create(template=template, **element_data)

        # Create variables
        for variable_data in variables_data:
            PDFTemplateVariable.objects.create(template=template, **variable_data)

        return template

    def update(self, instance, validated_data):
        elements_data = validated_data.pop('elements', None)
        variables_data = validated_data.pop('variables', None)

        # Update template
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update elements if provided
        if elements_data is not None:
            # Remove existing elements
            instance.elements.all().delete()

            # Create new elements
            for element_data in elements_data:
                PDFTemplateElement.objects.create(
                    template=instance,
                    **element_data
                )

        # Update variables if provided
        if variables_data is not None:
            # Remove existing variables
            instance.variables.all().delete()

            # Create new variables
            for variable_data in variables_data:
                PDFTemplateVariable.objects.create(
                    template=instance,
                    **variable_data
                )

        return instance


class PDFGenerationLogSerializer(serializers.ModelSerializer):
    """Serializer for generation logs"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    generated_by_name = serializers.CharField(
        source='generated_by.get_full_name',
        read_only=True
    )

    class Meta:
        model = PDFGenerationLog
        fields = [
            'id', 'template', 'template_name', 'generated_by',
            'generated_by_name', 'content_type', 'object_id',
            'file_name', 'file_size', 'status', 'error_message',
            'created_at', 'completed_at', 'generation_time'
        ]


class PDFGenerateSerializer(serializers.Serializer):
    """Serializer for PDF generation request"""
    template_id = serializers.IntegerField()
    context_data = serializers.JSONField()
    language = serializers.ChoiceField(
        choices=[('en', 'English'), ('ar', 'Arabic')],
        required=False
    )
    filename = serializers.CharField(required=False, max_length=255)

    def validate_template_id(self, value):
        """Validate template exists and user has access"""
        try:
            template = PDFTemplate.objects.get(id=value, active_ind=True)

            # Check permissions
            user = self.context['request'].user
            if not user.is_superuser:
                # Check if user has access through groups
                user_groups = user.groups.all()
                if template.groups.exists() and not template.groups.filter(
                        id__in=user_groups
                ).exists():
                    raise serializers.ValidationError(
                        "You don't have permission to use this template"
                    )

        except PDFTemplate.DoesNotExist:
            raise serializers.ValidationError("Template not found")

        return value


class TemplatePreviewSerializer(serializers.Serializer):
    """Serializer for template preview"""
    elements = PDFTemplateElementSerializer(many=True)
    context_data = serializers.JSONField(required=False, default=dict)
    page_size = serializers.ChoiceField(
        choices=['A4', 'A3', 'letter', 'legal'],
        default='A4'
    )
    orientation = serializers.ChoiceField(
        choices=['portrait', 'landscape'],
        default='portrait'
    )
    language = serializers.ChoiceField(
        choices=[('en', 'English'), ('ar', 'Arabic')],
        default='en'
    )


class ContentTypeSerializer(serializers.ModelSerializer):
    """Serializer for content types"""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model', 'display_name']

    def get_display_name(self, obj):
        return f"{obj.app_label}.{obj.model}"