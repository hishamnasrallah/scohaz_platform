import logging
from django.apps import apps
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.db import models, connection, NotSupportedError
from dynamic_models.utils.database import disable_foreign_keys, enable_foreign_keys
from dynamic_models.models import DynamicField

logger = logging.getLogger(__name__)

def create_dynamic_model(dynamic_model):
    """
    Create or retrieve a Django model dynamically based on the DynamicModel definition.
    """
    app_label = 'dynamic_models'
    model_name = dynamic_model.name

    # Check if the model is already registered
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        pass

    fields = {'__module__': app_label}
    for field in dynamic_model.fields.all():
        field_class = getattr(models, field.field_type)
        field_kwargs = generate_field_kwargs(field)
        fields[field.name] = field_class(**field_kwargs)

    fields['Meta'] = type('Meta', (), {'app_label': app_label})
    return type(model_name, (models.Model,), fields)

def generate_field_kwargs(dynamic_field):
    """
    Generate field keyword arguments from a DynamicField object.
    """
    kwargs = {'null': dynamic_field.null, 'blank': dynamic_field.blank, 'unique': dynamic_field.unique}

    # Handle CharField and TextField
    if dynamic_field.field_type in ['CharField', 'TextField']:
        kwargs['max_length'] = dynamic_field.max_length or 255

    # Handle DecimalField
    if dynamic_field.field_type == 'DecimalField':
        kwargs.update({
            'max_digits': dynamic_field.max_digits,
            'decimal_places': dynamic_field.decimal_places,
        })

    # Handle relationships
    if dynamic_field.field_type in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
        if not dynamic_field.related_model:
            raise ValidationError(f"Field '{dynamic_field.name}' requires 'related_model'.")
        kwargs['to'] = dynamic_field.related_model
        if dynamic_field.field_type in ['ForeignKey', 'OneToOneField']:
            kwargs['on_delete'] = getattr(models, dynamic_field.on_delete or 'CASCADE')

    return kwargs

def create_table_for_model(model):
    """
    Create the database table for the dynamically generated model.
    """
    disable_foreign_keys()
    try:
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(model)
    finally:
        enable_foreign_keys()

def delete_table_for_model(model):
    """
    Drop the database table for a dynamically generated model.
    """
    disable_foreign_keys()
    try:
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(model)
    finally:
        enable_foreign_keys()

def table_exists(table_name):
    """
    Check if a table exists in the database.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=%s", [table_name])
        return cursor.fetchone() is not None

def handle_column_rename(schema_editor, table_name, old_name, new_name):
    """
    Handles column renaming for SQLite and PostgreSQL.
    """
    if connection.vendor == 'sqlite':
        schema_editor.execute(f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {new_name};")
    elif connection.vendor == 'postgresql':
        schema_editor.execute(f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {new_name};")

def reload_database_schema():
    """
    Force SQLite to reload the database schema.
    """
    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA schema_version;")

def compare_columns(existing_fields, dynamic_fields):
    """
    Compare existing model fields with dynamic fields and categorize the differences.
    """
    dynamic_field_map = {field.name: field for field in dynamic_fields}
    dynamic_field_names = set(dynamic_field_map.keys())
    existing_field_names = set(existing_fields.keys())

    to_add = dynamic_field_names - existing_field_names
    to_remove = existing_field_names - dynamic_field_names - {'id'}  # Keep 'id' intact
    to_modify = {}
    to_rename = {}

    for field_name, existing_field in existing_fields.items():
        if field_name in dynamic_field_map:
            dynamic_field = dynamic_field_map[field_name]
            dynamic_field_class = getattr(models, dynamic_field.field_type)
            dynamic_field_kwargs = generate_field_kwargs(dynamic_field)

            if not isinstance(existing_field, dynamic_field_class) or dynamic_field_kwargs != existing_field.deconstruct()[3]:
                to_modify[field_name] = dynamic_field
        else:
            for dynamic_name, dynamic_field in dynamic_field_map.items():
                if (
                        dynamic_name not in existing_fields and
                        isinstance(existing_field, getattr(models, dynamic_field.field_type)) and
                        generate_field_kwargs(dynamic_field) == existing_field.deconstruct()[3]
                ):
                    to_rename[field_name] = dynamic_name
                    break

    return {
        'add': [dynamic_field_map[name] for name in to_add],
        'remove': [existing_fields[name] for name in to_remove],
        'modify': to_modify,
        'rename': to_rename,
    }

def sync_model_fields(model, dynamic_fields):
    """
    Synchronize the model fields with the database table for the selected model.
    """
    if connection.vendor == 'sqlite':
        disable_foreign_keys()

    try:
        with connection.schema_editor() as schema_editor:
            # Get the existing fields of the model
            existing_fields = {field.name: field for field in model._meta.fields}

            # Compare columns for operations
            comparison = compare_columns(existing_fields, dynamic_fields)

            # Add new fields
            for dynamic_field in comparison['add']:
                new_field = getattr(models, dynamic_field.field_type)(**generate_field_kwargs(dynamic_field))
                new_field.set_attributes_from_name(dynamic_field.name)
                schema_editor.add_field(model, new_field)

            # Remove deprecated fields
            for old_field in comparison['remove']:
                schema_editor.remove_field(model, old_field)

            # Modify existing fields
            for field_name, dynamic_field in comparison['modify'].items():
                existing_field = existing_fields[field_name]
                new_field = getattr(models, dynamic_field.field_type)(**generate_field_kwargs(dynamic_field))
                new_field.set_attributes_from_name(dynamic_field.name)
                schema_editor.alter_field(model, existing_field, new_field)

            # Rename fields
            for old_name, new_name in comparison['rename'].items():
                handle_column_rename(schema_editor, model._meta.db_table, old_name, new_name)

    except NotSupportedError as e:
        raise Exception(f"Schema editing failed: {e}")

    finally:
        if connection.vendor == 'sqlite':
            enable_foreign_keys()

def apply_schema_changes_for_model(dynamic_model):
    """
    Apply schema changes for a specific DynamicModel.
    """
    model_class = dynamic_model.get_dynamic_model_class()
    dynamic_fields = DynamicField.objects.filter(model=dynamic_model)
    sync_model_fields(model_class, dynamic_fields)
