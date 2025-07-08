# reporting_templates/serializers.py - WITH FULL CRUD

from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from simple_reporting.models import PDFTemplate, PDFElement


class PDFElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = PDFElement
        fields = ['id', 'template', 'x_position', 'y_position',
                  'text_content', 'is_dynamic', 'font_size']
        read_only_fields = ['id']

    def validate(self, data):
        # Validate position is within page bounds
        if data.get('x_position', 0) < 0 or data.get('x_position', 0) > 595:
            raise serializers.ValidationError("X position must be between 0 and 595 (A4 width)")
        if data.get('y_position', 0) < 0 or data.get('y_position', 0) > 842:
            raise serializers.ValidationError("Y position must be between 0 and 842 (A4 height)")
        return data


class PDFTemplateSerializer(serializers.ModelSerializer):
    elements = PDFElementSerializer(many=True, read_only=True)
    content_type_display = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    element_count = serializers.SerializerMethodField()

    class Meta:
        model = PDFTemplate
        fields = ['id', 'name', 'code', 'page_size', 'content_type',
                  'content_type_display', 'query_filter', 'created_by',
                  'created_by_name', 'created_at', 'active', 'elements',
                  'element_count']
        read_only_fields = ['id', 'created_by', 'created_at']
        extra_kwargs = {
            'code': {'required': True},
            'name': {'required': True},
            'content_type': {'required': True}
        }

    def get_content_type_display(self, obj):
        if obj.content_type:
            return f"{obj.content_type.app_label}.{obj.content_type.model}"
        return None

    def get_element_count(self, obj):
        return obj.elements.count()

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


class PDFTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating templates with elements"""
    elements = PDFElementSerializer(many=True, required=False)

    class Meta:
        model = PDFTemplate
        fields = ['name', 'code', 'page_size', 'content_type',
                  'query_filter', 'active', 'elements']

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