from django.apps import apps
from django.db import models
from django.conf import settings
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DynamicModelInspector:
    """
    Inspects dynamically created models and provides metadata for report building.
    Works with models created by the app_builder system.
    """

    def __init__(self):
        self.cache = {}

    def get_all_apps_and_models(self, include_system_apps: bool = False) -> Dict[str, Any]:
        """
        Returns all available apps and their models.
        
        Args:
            include_system_apps: Whether to include Django system apps
            
        Returns:
            Dictionary with app names as keys and model information as values
        """
        result = {}

        # Get custom apps from settings
        custom_apps = getattr(settings, 'CUSTOM_APPS', [])

        for app_config in apps.get_app_configs():
            # Skip system apps if not requested
            if not include_system_apps:
                if app_config.name.startswith('django.'):
                    continue
                if app_config.name in ['admin', 'auth', 'contenttypes', 'sessions']:
                    continue

            app_models = []

            for model in app_config.get_models():
                # Skip abstract models and proxies
                if model._meta.abstract or model._meta.proxy:
                    continue

                model_info = {
                    'name': model.__name__,
                    'db_table': model._meta.db_table,
                    'verbose_name': str(model._meta.verbose_name),
                    'verbose_name_plural': str(model._meta.verbose_name_plural),
                    'fields': self.get_model_fields(model),
                    'relationships': self.get_model_relationships(model),
                    'permissions': self.get_model_permissions(model),
                    'is_managed': model._meta.managed,
                    'ordering': model._meta.ordering or [],
                    'indexes': self.get_model_indexes(model),
                }
                app_models.append(model_info)

            if app_models:  # Only include apps with models
                result[app_config.name] = {
                    'label': app_config.label,
                    'verbose_name': app_config.verbose_name,
                    'is_custom': app_config.name in custom_apps,
                    'models': app_models
                }

        return result

    def get_model_fields(self, model: models.Model) -> List[Dict[str, Any]]:
        """
        Extract field information from a model.
        
        Args:
            model: Django model class
            
        Returns:
            List of field information dictionaries
        """
        fields = []

        for field in model._meta.get_fields():
            # Skip reverse relations and many-to-many through fields
            if field.auto_created and not field.concrete:
                continue

            field_info = {
                'name': field.name,
                'verbose_name': str(field.verbose_name),
                'type': field.get_internal_type(),
                'python_type': field.__class__.__name__,
                'db_column': getattr(field, 'db_column', field.name),
                'nullable': getattr(field, 'null', False),
                'blank': getattr(field, 'blank', False),
                'unique': getattr(field, 'unique', False),
                'primary_key': getattr(field, 'primary_key', False),
                'editable': getattr(field, 'editable', True),
                'help_text': str(getattr(field, 'help_text', '')),
                'default': self._serialize_default(field),
                'choices': self._get_field_choices(field),
                'is_relation': field.is_relation,
                'is_foreign_key': isinstance(field, models.ForeignKey),
                'is_many_to_many': field.many_to_many,
                'is_one_to_one': field.one_to_one,
            }

            # Add field-specific attributes
            if hasattr(field, 'max_length'):
                field_info['max_length'] = field.max_length

            if isinstance(field, models.DecimalField):
                field_info['max_digits'] = field.max_digits
                field_info['decimal_places'] = field.decimal_places

            if isinstance(field, (models.DateField, models.DateTimeField)):
                field_info['auto_now'] = getattr(field, 'auto_now', False)
                field_info['auto_now_add'] = getattr(field, 'auto_now_add', False)

            if field.is_relation:
                field_info['related_model'] = {
                    'app_label': field.related_model._meta.app_label,
                    'model_name': field.related_model.__name__,
                    'db_table': field.related_model._meta.db_table,
                }

                if hasattr(field, 'on_delete'):
                    field_info['on_delete'] = field.on_delete.__name__

            fields.append(field_info)

        return fields

    def get_model_relationships(self, model: models.Model) -> List[Dict[str, Any]]:
        """
        Extract relationship information from a model.
        
        Args:
            model: Django model class
            
        Returns:
            List of relationship information dictionaries
        """
        relationships = []

        for field in model._meta.get_fields():
            if not field.is_relation:
                continue

            # Skip auto-created reverse relations for now
            if field.auto_created and not field.concrete:
                continue

            rel_info = {
                'name': field.name,
                'verbose_name': str(field.verbose_name),
                'type': self._get_relationship_type(field),
                'related_model': {
                    'app_label': field.related_model._meta.app_label,
                    'model_name': field.related_model.__name__,
                    'db_table': field.related_model._meta.db_table,
                },
                'related_name': getattr(field, 'related_name', None),
                'related_query_name': getattr(field, 'related_query_name', None),
            }

            # Add relationship-specific attributes
            if hasattr(field, 'on_delete'):
                rel_info['on_delete'] = field.on_delete.__name__

            if hasattr(field, 'through'):
                if field.through and not field.through._meta.auto_created:
                    rel_info['through_model'] = {
                        'app_label': field.through._meta.app_label,
                        'model_name': field.through.__name__,
                        'db_table': field.through._meta.db_table,
                    }

            relationships.append(rel_info)

        # Add reverse relationships
        for field in model._meta.get_fields():
            if field.auto_created and not field.concrete and field.is_relation:
                # This is a reverse relation
                rel_info = {
                    'name': field.get_accessor_name(),
                    'verbose_name': f"{field.related_model._meta.verbose_name} set",
                    'type': f"reverse_{self._get_relationship_type(field.remote_field)}",
                    'related_model': {
                        'app_label': field.related_model._meta.app_label,
                        'model_name': field.related_model.__name__,
                        'db_table': field.related_model._meta.db_table,
                    },
                    'is_reverse': True,
                    'field_name': field.remote_field.name,
                }
                relationships.append(rel_info)

        return relationships

    def get_model_by_name(self, app_name: str, model_name: str) -> Optional[models.Model]:
        """
        Get a model class by app and model name.
        
        Args:
            app_name: Name of the Django app
            model_name: Name of the model
            
        Returns:
            Model class or None if not found
        """
        try:
            return apps.get_model(app_name, model_name)
        except LookupError:
            logger.warning(f"Model {app_name}.{model_name} not found")
            return None

    def get_field_choices(self, model: models.Model, field_name: str) -> List[tuple]:
        """
        Get choices for a specific field if available.
        
        Args:
            model: Django model class
            field_name: Name of the field
            
        Returns:
            List of (value, display) tuples
        """
        try:
            field = model._meta.get_field(field_name)
            return self._get_field_choices(field)
        except models.FieldDoesNotExist:
            return []

    def get_model_permissions(self, model: models.Model) -> List[Dict[str, str]]:
        """
        Get permissions for a model.
        
        Args:
            model: Django model class
            
        Returns:
            List of permission dictionaries
        """
        permissions = []

        # Default permissions
        for action in ['add', 'change', 'delete', 'view']:
            permissions.append({
                'codename': f"{action}_{model._meta.model_name}",
                'name': f"Can {action} {model._meta.verbose_name}",
                'action': action,
            })

        # Custom permissions
        for codename, name in model._meta.permissions:
            permissions.append({
                'codename': codename,
                'name': name,
                'action': 'custom',
            })

        return permissions

    def get_model_indexes(self, model: models.Model) -> List[Dict[str, Any]]:
        """
        Get indexes for a model.
        
        Args:
            model: Django model class
            
        Returns:
            List of index information
        """
        indexes = []

        for index in model._meta.indexes:
            index_info = {
                'name': index.name,
                'fields': list(index.fields),
                'unique': getattr(index, 'unique', False),
            }

            if hasattr(index, 'condition'):
                index_info['condition'] = str(index.condition)

            indexes.append(index_info)

        return indexes

    def get_field_lookups(self, field_type: str) -> List[str]:
        """
        Get available lookups for a field type.
        
        Args:
            field_type: Django field type (e.g., 'CharField', 'IntegerField')
            
        Returns:
            List of lookup names
        """
        # Common lookups available for most fields
        common_lookups = ['exact', 'isnull', 'in']

        # Type-specific lookups
        type_lookups = {
            'CharField': ['iexact', 'contains', 'icontains', 'startswith',
                          'istartswith', 'endswith', 'iendswith', 'regex', 'iregex'],
            'TextField': ['iexact', 'contains', 'icontains', 'startswith',
                          'istartswith', 'endswith', 'iendswith', 'regex', 'iregex'],
            'IntegerField': ['gt', 'gte', 'lt', 'lte', 'range'],
            'FloatField': ['gt', 'gte', 'lt', 'lte', 'range'],
            'DecimalField': ['gt', 'gte', 'lt', 'lte', 'range'],
            'DateField': ['year', 'month', 'day', 'week', 'week_day',
                          'quarter', 'gt', 'gte', 'lt', 'lte', 'range'],
            'DateTimeField': ['year', 'month', 'day', 'week', 'week_day',
                              'hour', 'minute', 'second', 'quarter',
                              'gt', 'gte', 'lt', 'lte', 'range'],
            'BooleanField': [],
            'ForeignKey': ['in', 'gt', 'gte', 'lt', 'lte'],
        }

        lookups = common_lookups.copy()
        lookups.extend(type_lookups.get(field_type, []))

        return list(set(lookups))  # Remove duplicates

    def _serialize_default(self, field) -> Any:
        """Serialize field default value for JSON."""
        if not hasattr(field, 'default'):
            return None

        default = field.default

        if default == models.NOT_PROVIDED:
            return None

        if callable(default):
            return f"<function: {default.__name__}>"

        # Handle special Django defaults
        if hasattr(default, '__class__'):
            class_name = default.__class__.__name__
            if class_name in ['datetime', 'date', 'time']:
                return str(default)
            if class_name == 'Decimal':
                return float(default)

        return default

    def _get_field_choices(self, field) -> List[List]:
        """Get field choices if available."""
        if hasattr(field, 'choices') and field.choices:
            return list(field.choices)
        return []

    def _get_relationship_type(self, field) -> str:
        """Determine the relationship type of a field."""
        if field.many_to_many:
            return 'ManyToManyField'
        elif field.one_to_one:
            return 'OneToOneField'
        elif field.many_to_one:
            return 'ForeignKey'
        elif field.one_to_many:
            return 'OneToManyField'
        else:
            return 'Unknown'

    def validate_field_path(self, model: models.Model, path: str) -> tuple[bool, str]:
        """
        Validate a field path (e.g., 'customer__name') is valid.
        
        Args:
            model: Starting model class
            path: Field path with __ separators
            
        Returns:
            Tuple of (is_valid, field_type_or_error_message)
        """
        parts = path.split('__')
        current_model = model

        for i, part in enumerate(parts):
            try:
                field = current_model._meta.get_field(part)

                if i < len(parts) - 1:
                    # Not the last part, must be a relation
                    if not field.is_relation:
                        return False, f"'{part}' is not a relation field"
                    current_model = field.related_model
                else:
                    # Last part, return the field type
                    return True, field.get_internal_type()

            except models.FieldDoesNotExist:
                return False, f"Field '{part}' does not exist on {current_model.__name__}"

        return True, "Unknown"