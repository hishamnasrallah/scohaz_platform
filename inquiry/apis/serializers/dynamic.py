from rest_framework import serializers
from rest_framework.fields import empty
from django.db import models
from jsonpath_ng import parse
import importlib
from datetime import datetime

class DynamicFieldMixin:
    """Mixin to handle dynamic field creation"""

    def create_field_for_model_field(self, model_field, field_config=None):
        """Create appropriate serializer field based on model field type"""
        field_kwargs = {}

        if field_config:
            field_kwargs['label'] = field_config.display_name
            if not field_config.is_visible:
                field_kwargs['write_only'] = True

        if isinstance(model_field, models.CharField):
            return serializers.CharField(**field_kwargs)
        elif isinstance(model_field, models.IntegerField):
            return serializers.IntegerField(**field_kwargs)
        elif isinstance(model_field, models.FloatField):
            return serializers.FloatField(**field_kwargs)
        elif isinstance(model_field, models.BooleanField):
            return serializers.BooleanField(**field_kwargs)
        elif isinstance(model_field, models.DateTimeField):
            return serializers.DateTimeField(**field_kwargs)
        elif isinstance(model_field, models.DateField):
            return serializers.DateField(**field_kwargs)
        elif isinstance(model_field, models.JSONField):
            return serializers.JSONField(**field_kwargs)
        elif isinstance(model_field, models.ForeignKey):
            return serializers.PrimaryKeyRelatedField(
                queryset=model_field.related_model.objects.all(),
                **field_kwargs
            )
        elif isinstance(model_field, models.ManyToManyField):
            return serializers.PrimaryKeyRelatedField(
                queryset=model_field.related_model.objects.all(),
                many=True,
                **field_kwargs
            )
        else:
            return serializers.Field(**field_kwargs)


class DynamicModelSerializer(serializers.ModelSerializer, DynamicFieldMixin):
    """Serializer that dynamically includes fields based on configuration"""

    def __init__(self, *args, **kwargs):
        # Get inquiry configuration from context
        context = kwargs.get('context', {})
        self.inquiry = context.get('inquiry')
        self.user = context.get('request', {}).user if 'request' in context else None

        # Initialize with model meta
        if self.inquiry:
            self.Meta.model = self.inquiry.content_type.model_class()

        super().__init__(*args, **kwargs)

        if self.inquiry:
            self.configure_fields()
            self.add_computed_fields()
            self.add_relation_fields()

    def configure_fields(self):
        """Configure which fields to include based on inquiry configuration"""
        # Get configured fields
        configured_fields = {}
        visible_fields = set()

        # Get field configurations
        for field_config in self.inquiry.fields.filter(is_visible=True).order_by('order'):
            field_path = field_config.field_path

            # Handle nested fields
            if '__' in field_path:
                # This is a related field, handle it in add_relation_fields
                continue

            visible_fields.add(field_path)

            # Try to get the model field
            try:
                model_field = self.Meta.model._meta.get_field(field_path)
                configured_fields[field_path] = self.create_field_for_model_field(
                    model_field,
                    field_config
                )
            except:
                # Field doesn't exist on model, might be computed
                pass

        # Remove fields not in configuration
        for field_name in list(self.fields.keys()):
            if field_name not in visible_fields:
                self.fields.pop(field_name)

        # Add configured fields
        for field_name, field in configured_fields.items():
            self.fields[field_name] = field

    def add_computed_fields(self):
        """Add computed/transformed fields"""
        for field_config in self.inquiry.fields.filter(
                transform_function__isnull=False
        ):
            field_name = f"computed_{field_config.field_path}"
            self.fields[field_name] = serializers.SerializerMethodField()

            # Dynamically create the method
            def make_method(fc):
                def method(obj):
                    return self.apply_transform(obj, fc)
                return method

            setattr(self, f"get_{field_name}", make_method(field_config))

    def add_relation_fields(self):
        """Add fields for configured relations"""
        for relation in self.inquiry.relations.all():
            relation_name = relation.relation_path.replace('__', '_')

            # Determine relation type and create appropriate field
            if relation.relation_type in ['one_to_one', 'foreign_key']:
                self.fields[relation_name] = self.create_nested_serializer(relation)
            elif relation.relation_type == 'one_to_many':
                self.fields[relation_name] = self.create_nested_serializer(
                    relation,
                    many=True
                )
            elif relation.relation_type == 'many_to_many':
                self.fields[relation_name] = self.create_nested_serializer(
                    relation,
                    many=True
                )

            if relation.include_count:
                count_field_name = f"{relation_name}_count"
                self.fields[count_field_name] = serializers.SerializerMethodField()

                def make_count_method(rel_path):
                    def method(obj):
                        try:
                            related_obj = getattr(obj, rel_path)
                            if hasattr(related_obj, 'count'):
                                return related_obj.count()
                            return 0
                        except AttributeError:
                            return 0
                    return method

                setattr(
                    self,
                    f"get_{count_field_name}",
                    make_count_method(relation.relation_path)
                )

    def create_nested_serializer(self, relation, many=False):
        """Create a nested serializer for a relation"""
        # Get the related model
        path_parts = relation.relation_path.split('__')
        model = self.Meta.model

        for part in path_parts:
            field = model._meta.get_field(part)
            model = field.related_model

        # Create dynamic serializer class
        class_name = f"Dynamic{model.__name__}Serializer"

        # Determine fields to include
        if relation.include_fields:
            fields = relation.include_fields
        elif relation.exclude_fields:
            fields = '__all__'
        else:
            # Default fields
            fields = ['id', 'name'] if hasattr(model, 'name') else ['id']

        # Create serializer class dynamically
        attrs = {
            'Meta': type('Meta', (), {
                'model': model,
                'fields': fields,
                'exclude': relation.exclude_fields if relation.exclude_fields else None
            })
        }

        serializer_class = type(class_name, (serializers.ModelSerializer,), attrs)

        return serializer_class(many=many, read_only=True)

    def apply_transform(self, obj, field_config):
        """Apply transformation function to field value"""
        try:
            # Get the value
            value = obj
            for part in field_config.field_path.split('__'):
                value = getattr(value, part)

            # Apply transform if configured
            if field_config.transform_function:
                module_path, func_name = field_config.transform_function.rsplit('.', 1)
                module = importlib.import_module(module_path)
                transform_func = getattr(module, func_name)
                value = transform_func(value)

            # Apply formatting if configured
            if field_config.format_template and value is not None:
                if isinstance(value, datetime):
                    value = value.strftime(field_config.format_template)
                else:
                    value = field_config.format_template.format(value=value)

            return value
        except:
            return None

    def to_representation(self, instance):
        """Handle JSON field extraction and permissions"""
        data = super().to_representation(instance)

        # Handle JSON field extraction
        for field_config in self.inquiry.fields.filter(
                json_extract_path__isnull=False
        ):
            if field_config.field_path in data:
                json_data = data[field_config.field_path]
                if json_data and field_config.json_extract_path:
                    try:
                        jsonpath_expr = parse(field_config.json_extract_path)
                        matches = jsonpath_expr.find(json_data)
                        if matches:
                            data[field_config.field_path] = matches[0].value
                    except:
                        pass

        # Apply field-level permissions
        if self.user and not self.user.is_superuser:
            user_groups = self.user.groups.all()
            permission = self.inquiry.permissions.filter(
                group__in=user_groups
            ).first()

            if permission:
                # Remove hidden fields
                for field in permission.hidden_fields:
                    data.pop(field, None)

                # Keep only visible fields if specified
                if permission.visible_fields:
                    data = {k: v for k, v in data.items()
                            if k in permission.visible_fields}

        return data

    class Meta:
        model = None  # Will be set dynamically
        fields = '__all__'