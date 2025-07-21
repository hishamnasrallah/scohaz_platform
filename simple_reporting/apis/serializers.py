# reporting_templates/serializers.py - WITH FULL CRUD
import re

from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from simple_reporting.models import PDFTemplate, PDFElement


class PDFElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = PDFElement
        fields = ['id', 'template', 'element_type', 'x_position', 'y_position',
                  'text_content', 'is_dynamic', 'font_size', 'image_field_path',
                  'image_filter_type', 'image_index', 'image_width', 'image_height',
                  'image_maintain_aspect']
        read_only_fields = ['id']

    def validate(self, data):
        # Validate position is within page bounds
        if data.get('x_position', 0) < 0 or data.get('x_position', 0) > 595:
            raise serializers.ValidationError("X position must be between 0 and 595 (A4 width)")
        if data.get('y_position', 0) < 0 or data.get('y_position', 0) > 842:
            raise serializers.ValidationError("Y position must be between 0 and 842 (A4 height)")

        # Element type specific validation
        element_type = data.get('element_type', 'text')

        if element_type == 'text':
            if not data.get('text_content'):
                raise serializers.ValidationError("Text content is required for text elements")
        elif element_type == 'image':
            if not data.get('image_field_path'):
                raise serializers.ValidationError("Image field path is required for image elements")

        return data


class PDFTemplateSerializer(serializers.ModelSerializer):
    elements = PDFElementSerializer(many=True, read_only=True)
    content_type_display = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    element_count = serializers.SerializerMethodField()
    page_dimensions_display = serializers.SerializerMethodField()

    class Meta:
        model = PDFTemplate
        fields = ['id', 'name', 'code', 'page_size', 'page_orientation',
                  'custom_width', 'custom_height', 'ratio_base_width',
                  'content_type', 'content_type_display', 'query_filter',
                  'created_by', 'created_by_name', 'created_at', 'active',
                  'elements', 'element_count', 'background_type',
                  'background_color', 'background_image', 'background_pdf',
                  'background_opacity']
        read_only_fields = ['id', 'created_by', 'created_at']
        extra_kwargs = {
            'code': {'required': True},
            'name': {'required': True},
            'content_type': {'required': True},
            'background_color': {'required': False, 'allow_null': True},
            'background_image': {'required': False, 'allow_null': True},
            'background_pdf': {'required': False, 'allow_null': True}
        }

    def get_content_type_display(self, obj):
        if obj.content_type:
            return f"{obj.content_type.app_label}.{obj.content_type.model}"
        return None

    def get_element_count(self, obj):
        return obj.elements.count()

    def get_page_dimensions_display(self, obj):
        """Display calculated page dimensions"""
        width, height = obj.get_page_dimensions()
        return {
            'width_points': round(width, 2),
            'height_points': round(height, 2),
            'width_pixels': round(width / 0.75),
            'height_pixels': round(height / 0.75),
            'width_inches': round(width / 72, 2),
            'height_inches': round(height / 72, 2),
            'width_mm': round(width * 0.352778, 2),
            'height_mm': round(height * 0.352778, 2)
        }
    def validate_code(self, value):
        # Ensure code is unique (excluding current instance on update)
        qs = PDFTemplate.objects.filter(code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A template with this code already exists")
        return value

    def validate_query_filter(self, value):
        # Ensure it's a valid dict
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("Query filter must be a valid JSON object")
        return value
    def validate_background_color(self, value):
        """Validate hex color format"""
        if value and not re.match(r'^#[0-9A-Fa-f]{6}$', value):
            raise serializers.ValidationError("Color must be in hex format (e.g., #FFFFFF)")
        return value

    def validate(self, data):
        """Validate page setup and background settings"""
        # Existing background validation...

        # Page size validation
        page_size = data.get('page_size', self.instance.page_size if self.instance else 'A4')

        if page_size == 'custom':
            if not data.get('custom_width') and (not self.instance or not self.instance.custom_width):
                raise serializers.ValidationError("Custom width is required for custom page size")
            if not data.get('custom_height') and (not self.instance or not self.instance.custom_height):
                raise serializers.ValidationError("Custom height is required for custom page size")

        # Validate custom dimensions
        if data.get('custom_width') and data.get('custom_width') < 100:
            raise serializers.ValidationError("Custom width must be at least 100 pixels")
        if data.get('custom_height') and data.get('custom_height') < 100:
            raise serializers.ValidationError("Custom height must be at least 100 pixels")

        return data


class PDFTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating templates with elements"""
    elements = PDFElementSerializer(many=True, required=False)

    class Meta:
        model = PDFTemplate
        fields = ['name', 'code', 'page_size', 'content_type',
                  'query_filter', 'active', 'elements', 'background_type',
                  'background_color', 'background_image', 'background_pdf',
                  'background_opacity']

    def create(self, validated_data):
        elements_data = validated_data.pop('elements', [])
        template = PDFTemplate.objects.create(**validated_data)

        # Create elements
        for element_data in elements_data:
            PDFElement.objects.create(template=template, **element_data)

        return template


class ContentTypeSerializer(serializers.ModelSerializer):
    """For listing available content types"""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model', 'display_name']

    def get_display_name(self, obj):
        return f"{obj.app_label}.{obj.model}"


class GeneratePDFSerializer(serializers.Serializer):
    template_id = serializers.IntegerField()
    object_id = serializers.IntegerField(required=False)

    def validate_template_id(self, value):
        try:
            PDFTemplate.objects.get(id=value, active=True)
        except PDFTemplate.DoesNotExist:
            raise serializers.ValidationError("Template not found or inactive")
        return value