# reporting_templates/apis/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from reporting_templates.models import (
    PDFTemplate, PDFTemplateElement, PDFTemplateVariable,
    PDFTemplateParameter, PDFTemplateDataSource, PDFGenerationLog
)

User = get_user_model()


class PDFTemplateParameterSerializer(serializers.ModelSerializer):
    """Serializer for template parameters"""
    choices = serializers.SerializerMethodField()
    widget_config_display = serializers.SerializerMethodField()

    class Meta:
        model = PDFTemplateParameter
        fields = [
            'id', 'parameter_key', 'display_name', 'display_name_ara',
            'description', 'description_ara', 'parameter_type', 'is_required',
            'default_value', 'widget_type', 'widget_config', 'widget_config_display',
            'validation_rules', 'query_field', 'query_operator',
            'allow_user_override', 'restricted_to_groups', 'order',
            'active_ind', 'choices'
        ]

    def get_choices(self, obj):
        """Get choices for select/radio widgets"""
        if obj.widget_type in ['select', 'radio'] and obj.widget_config:
            return obj.widget_config.get('choices', [])
        return None

    def get_widget_config_display(self, obj):
        """Get display-friendly widget configuration"""
        config = obj.widget_config or {}

        # Add type-specific configurations
        if obj.parameter_type == 'integer' or obj.parameter_type == 'float':
            config['type'] = 'number'
            if 'min' in obj.validation_rules:
                config['min'] = obj.validation_rules['min']
            if 'max' in obj.validation_rules:
                config['max'] = obj.validation_rules['max']
        elif obj.parameter_type == 'date':
            config['type'] = 'date'
        elif obj.parameter_type == 'datetime':
            config['type'] = 'datetime-local'
        elif obj.parameter_type == 'model_id' and obj.widget_type == 'model_search':
            # Add model information for search widget
            if 'model' in config:
                try:
                    ct = ContentType.objects.get(
                        app_label=config['model'].split('.')[0],
                        model=config['model'].split('.')[1]
                    )
                    config['model_id'] = ct.id
                    config['model_name'] = ct.name
                except ContentType.DoesNotExist:
                    pass

        return config

    def validate_parameter_key(self, value):
        """Ensure parameter key is valid Python identifier"""
        if not value.replace('_', '').isalnum():
            raise serializers.ValidationError(
                "Parameter key must contain only letters, numbers, and underscores"
            )
        return value


class PDFTemplateDataSourceSerializer(serializers.ModelSerializer):
    """Serializer for additional data sources"""

    class Meta:
        model = PDFTemplateDataSource
        fields = [
            'id', 'source_key', 'display_name', 'fetch_method',
            'content_type', 'query_path', 'filter_config',
            'custom_function_path', 'raw_sql', 'post_process_function',
            'cache_timeout', 'order', 'active_ind'
        ]

    def validate_source_key(self, value):
        """Ensure source key is valid Python identifier"""
        if not value.replace('_', '').isalnum():
            raise serializers.ValidationError(
                "Source key must contain only letters, numbers, and underscores"
            )
        return value


class PDFTemplateVariableSerializer(serializers.ModelSerializer):
    """Serializer for template variables"""
    resolved_value = serializers.SerializerMethodField()

    class Meta:
        model = PDFTemplateVariable
        fields = [
            'id', 'variable_key', 'display_name', 'display_name_ara',
            'description', 'data_type', 'data_source', 'default_value',
            'format_string', 'transform_function', 'is_required',
            'resolved_value'
        ]

    def get_resolved_value(self, obj):
        """Get example of resolved value (for preview)"""
        # This would be populated during actual generation
        return obj.default_value

    def validate_variable_key(self, value):
        """Ensure variable key is valid Python identifier"""
        if not value.replace('_', '').isalnum():
            raise serializers.ValidationError(
                "Variable key must contain only letters, numbers, and underscores"
            )
        return value


class PDFTemplateElementSerializer(serializers.ModelSerializer):
    """Serializer for template elements"""
    child_elements = serializers.SerializerMethodField()

    class Meta:
        model = PDFTemplateElement
        fields = [
            'id', 'element_type', 'element_key', 'x_position', 'y_position',
            'width', 'height', 'rotation', 'text_content', 'text_content_ara',
            'font_family', 'font_size', 'font_color', 'is_bold', 'is_italic',
            'is_underline', 'text_align', 'line_height', 'fill_color',
            'stroke_color', 'stroke_width', 'image_source',
            'maintain_aspect_ratio', 'table_config', 'loop_config',
            'data_source', 'condition', 'parent_element', 'child_elements',
            'z_index', 'is_repeatable', 'page_number', 'active_ind'
        ]

    def get_child_elements(self, obj):
        """Get child elements for containers"""
        if obj.element_type in ['loop', 'conditional']:
            children = obj.child_elements.filter(active_ind=True)
            return PDFTemplateElementSerializer(children, many=True).data
        return []

    def validate_font_color(self, value):
        """Validate hex color format"""
        if value and not value.startswith('#'):
            raise serializers.ValidationError("Color must be in hex format (#RRGGBB)")
        return value


class PDFTemplateSerializer(serializers.ModelSerializer):
    """Main template serializer"""
    elements = PDFTemplateElementSerializer(many=True, read_only=True)
    variables = PDFTemplateVariableSerializer(many=True, read_only=True)
    parameters = PDFTemplateParameterSerializer(many=True, read_only=True)
    data_sources = PDFTemplateDataSourceSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    content_type_display = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    can_generate_self = serializers.SerializerMethodField()
    can_generate_others = serializers.SerializerMethodField()
    parameter_schema = serializers.SerializerMethodField()

    class Meta:
        model = PDFTemplate
        fields = [
            'id', 'name', 'name_ara', 'description', 'description_ara',
            'code', 'primary_language', 'supports_bilingual', 'page_size',
            'orientation', 'margin_top', 'margin_bottom', 'margin_left',
            'margin_right', 'header_enabled', 'footer_enabled',
            'watermark_enabled', 'watermark_text', 'data_source_type',
            'content_type', 'content_type_display', 'query_filter',
            'custom_function_path', 'raw_sql_query', 'created_by',
            'created_by_name', 'groups', 'requires_parameters',
            'allow_self_generation', 'allow_other_generation',
            'related_models', 'is_system_template', 'active_ind',
            'created_at', 'updated_at', 'elements', 'variables',
            'parameters', 'data_sources', 'can_edit', 'can_delete',
            'can_generate_self', 'can_generate_others', 'parameter_schema'
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

    def get_can_generate_self(self, obj):
        """Check if user can generate for themselves"""
        return obj.allow_self_generation

    def get_can_generate_others(self, obj):
        """Check if user can generate for others"""
        request = self.context.get('request')
        if not request or not request.user:
            return False

        if not obj.allow_other_generation:
            return False

        # Check special permission
        return request.user.has_perm('reporting_templates.can_generate_others_pdf')

    def get_parameter_schema(self, obj):
        """Get parameter schema for frontend"""
        schema = {
            'required': [],
            'properties': {}
        }

        for param in obj.parameters.filter(active_ind=True):
            param_schema = {
                'type': self._get_json_type(param.parameter_type),
                'title': param.display_name,
                'description': param.description,
            }

            if param.default_value:
                param_schema['default'] = param.default_value

            if param.validation_rules:
                if 'min' in param.validation_rules:
                    param_schema['minimum'] = param.validation_rules['min']
                if 'max' in param.validation_rules:
                    param_schema['maximum'] = param.validation_rules['max']
                if 'pattern' in param.validation_rules:
                    param_schema['pattern'] = param.validation_rules['pattern']
                if 'choices' in param.validation_rules:
                    param_schema['enum'] = param.validation_rules['choices']

            schema['properties'][param.parameter_key] = param_schema

            if param.is_required:
                schema['required'].append(param.parameter_key)

        return schema

    def _get_json_type(self, param_type):
        """Convert parameter type to JSON schema type"""
        type_map = {
            'integer': 'integer',
            'float': 'number',
            'string': 'string',
            'boolean': 'boolean',
            'date': 'string',
            'datetime': 'string',
            'uuid': 'string',
            'model_id': 'integer',
            'user_id': 'integer',
        }
        return type_map.get(param_type, 'string')


class PDFTemplateCreateSerializer(serializers.ModelSerializer):
    elements = PDFTemplateElementSerializer(many=True, required=False)
    variables = PDFTemplateVariableSerializer(many=True, required=False)
    parameters = PDFTemplateParameterSerializer(many=True, required=False)
    data_sources = PDFTemplateDataSourceSerializer(many=True, required=False)

    class Meta:
        model = PDFTemplate
        fields = [
            'name', 'name_ara', 'description', 'description_ara', 'code',
            'primary_language', 'supports_bilingual', 'page_size',
            'orientation', 'margin_top', 'margin_bottom', 'margin_left',
            'margin_right', 'header_enabled', 'footer_enabled',
            'watermark_enabled', 'watermark_text', 'data_source_type',
            'content_type', 'query_filter', 'custom_function_path',
            'raw_sql_query', 'groups', 'requires_parameters',
            'allow_self_generation', 'allow_other_generation',
            'related_models', 'elements', 'variables', 'parameters',
            'data_sources'
        ]

    def create(self, validated_data):
        elements_data = validated_data.pop('elements', [])
        variables_data = validated_data.pop('variables', [])
        parameters_data = validated_data.pop('parameters', [])
        data_sources_data = validated_data.pop('data_sources', [])

        # Pop ManyToMany fields
        groups_data = validated_data.pop('groups', [])

        # Set created_by from context
        validated_data['created_by'] = self.context['request'].user

        with transaction.atomic():
            # Create template without ManyToMany fields
            template = PDFTemplate.objects.create(**validated_data)

            # Now set the ManyToMany relationships
            if groups_data:
                template.groups.set(groups_data)

            # Create related objects
            self._create_parameters(template, parameters_data)
            self._create_data_sources(template, data_sources_data)
            self._create_variables(template, variables_data)
            self._create_elements(template, elements_data)

        return template

    def update(self, instance, validated_data):
        elements_data = validated_data.pop('elements', None)
        variables_data = validated_data.pop('variables', None)
        parameters_data = validated_data.pop('parameters', None)
        data_sources_data = validated_data.pop('data_sources', None)

        # Pop ManyToMany fields
        groups_data = validated_data.pop('groups', None)

        with transaction.atomic():
            # Update template fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # Update ManyToMany relationships if provided
            if groups_data is not None:
                instance.groups.set(groups_data)

            # Update related objects if provided
            if parameters_data is not None:
                instance.parameters.all().delete()
                self._create_parameters(instance, parameters_data)

            if data_sources_data is not None:
                instance.data_sources.all().delete()
                self._create_data_sources(instance, data_sources_data)

            if variables_data is not None:
                instance.variables.all().delete()
                self._create_variables(instance, variables_data)

            if elements_data is not None:
                instance.elements.all().delete()
                self._create_elements(instance, elements_data)

        return instance

    def _create_parameters(self, template, parameters_data):
        """Create template parameters"""
        for param_data in parameters_data:
            # Handle any nested ManyToMany fields in parameters
            restricted_groups = param_data.pop('restricted_to_groups', [])
            param = PDFTemplateParameter.objects.create(template=template, **param_data)
            if restricted_groups:
                param.restricted_to_groups.set(restricted_groups)

    def _create_data_sources(self, template, data_sources_data):
        """Create data sources"""
        for source_data in data_sources_data:
            PDFTemplateDataSource.objects.create(template=template, **source_data)

    def _create_variables(self, template, variables_data):
        """Create template variables"""
        for var_data in variables_data:
            PDFTemplateVariable.objects.create(template=template, **var_data)

    def _create_elements(self, template, elements_data, parent=None):
        """Create template elements recursively"""
        for element_data in elements_data:
            child_elements_data = element_data.pop('child_elements', [])
            element = PDFTemplateElement.objects.create(
                template=template,
                parent_element=parent,
                **element_data
            )

            # Create child elements if any
            if child_elements_data:
                self._create_elements(template, child_elements_data, element)

class PDFGenerationLogSerializer(serializers.ModelSerializer):
    """Serializer for generation logs"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    generated_by_name = serializers.CharField(
        source='generated_by.get_full_name',
        read_only=True
    )
    generated_for_name = serializers.CharField(
        source='generated_for.get_full_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = PDFGenerationLog
        fields = [
            'id', 'template', 'template_name', 'generated_by',
            'generated_by_name', 'generated_for', 'generated_for_name',
            'content_type', 'object_id', 'parameters', 'file_name',
            'file_size', 'status', 'error_message', 'created_at',
            'completed_at', 'generation_time'
        ]


class PDFGenerateSerializer(serializers.Serializer):
    """Serializer for PDF generation request"""
    template_id = serializers.IntegerField()
    parameters = serializers.JSONField(required=False, default=dict)
    language = serializers.ChoiceField(
        choices=[('en', 'English'), ('ar', 'Arabic')],
        required=False
    )
    filename = serializers.CharField(required=False, max_length=255)
    generate_for_user_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        """Validate the generation request"""
        template_id = attrs.get('template_id')
        parameters = attrs.get('parameters', {})
        generate_for_user_id = attrs.get('generate_for_user_id')

        # Get template
        try:
            template = PDFTemplate.objects.get(id=template_id, active_ind=True)
        except PDFTemplate.DoesNotExist:
            raise serializers.ValidationError("Template not found or inactive")

        # Check permissions
        user = self.context['request'].user

        # Basic permission check
        if not user.is_superuser:
            user_groups = user.groups.all()
            if template.groups.exists() and not template.groups.filter(
                    id__in=user_groups
            ).exists():
                raise serializers.ValidationError(
                    "You don't have permission to use this template"
                )

        # Check self/other generation
        if generate_for_user_id and generate_for_user_id != user.id:
            if not template.allow_other_generation:
                raise serializers.ValidationError(
                    "This template does not allow generating reports for other users"
                )
            if not user.has_perm('reporting_templates.can_generate_others_pdf'):
                raise serializers.ValidationError(
                    "You don't have permission to generate reports for other users"
                )
        elif not template.allow_self_generation:
            raise serializers.ValidationError(
                "This template does not allow self-generation"
            )

        # Validate required parameters
        if template.requires_parameters:
            required_params = template.parameters.filter(
                is_required=True,
                active_ind=True
            )
            for param in required_params:
                if param.parameter_key not in parameters and not param.default_value:
                    raise serializers.ValidationError(
                        f"Required parameter '{param.parameter_key}' is missing"
                    )

        # Store template for use in view
        self.template = template

        return attrs


class TemplatePreviewSerializer(serializers.Serializer):
    """Serializer for template preview"""
    elements = PDFTemplateElementSerializer(many=True)
    parameters = serializers.JSONField(required=False, default=dict)
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


class ParameterSchemaSerializer(serializers.Serializer):
    """Serializer for getting parameter schema"""
    template_id = serializers.IntegerField()
    include_sample_data = serializers.BooleanField(default=False)


class ContentTypeSerializer(serializers.ModelSerializer):
    """Serializer for content types"""
    display_name = serializers.SerializerMethodField()
    model_fields = serializers.SerializerMethodField()

    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model', 'display_name', 'model_fields']

    def get_display_name(self, obj):
        return f"{obj.app_label}.{obj.model}"

    def get_model_fields(self, obj):
        """Get model fields for query building"""
        model_class = obj.model_class()
        if not model_class:
            return []

        fields = []
        for field in model_class._meta.fields:
            fields.append({
                'name': field.name,
                'type': field.__class__.__name__,
                'verbose_name': str(field.verbose_name),
                'is_relation': field.is_relation,
                'related_model': field.related_model._meta.label if field.related_model else None
            })

        return fields