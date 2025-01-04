import logging

from django.apps import apps
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.db import models, connection
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db.transaction import TransactionManagementError, get_connection
from dynamic_models.utils.database import disable_foreign_keys, enable_foreign_keys

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

    fields = {
        '__module__': app_label,
    }

    for field in dynamic_model.fields.all():
        field_class = getattr(models, field.field_type)
        field_kwargs = generate_field_kwargs(field)
        fields[field.name] = field_class(**field_kwargs)

    fields['Meta'] = type('Meta', (), {'app_label': app_label})

    # Dynamically create and return the model
    return type(model_name, (models.Model,), fields)



def generate_field_kwargs(dynamic_field):
    """
    Generate field keyword arguments from a DynamicField object.
    """
    kwargs = {
        'null': dynamic_field.null,
        'blank': dynamic_field.blank,
        'unique': dynamic_field.unique,
    }

    # Handle CharField and TextField
    if dynamic_field.field_type in ['CharField', 'TextField']:
        kwargs['max_length'] = dynamic_field.max_length or 255  # Default to 255 if not provided

    # Handle DecimalField
    if dynamic_field.field_type == 'DecimalField':
        if dynamic_field.max_digits is None or dynamic_field.decimal_places is None:
            raise ValidationError(
                f"DecimalField '{dynamic_field.name}' requires both 'max_digits' and 'decimal_places'."
            )
        kwargs['max_digits'] = dynamic_field.max_digits
        kwargs['decimal_places'] = dynamic_field.decimal_places

    # Handle ForeignKey, OneToOneField, and ManyToManyField relationships
    if dynamic_field.field_type in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
        if not dynamic_field.related_model:
            raise ValidationError(
                f"Field '{dynamic_field.name}' requires 'related_model' for {dynamic_field.field_type}."
            )

        # Resolve related model
        try:
            kwargs['to'] = apps.get_model(dynamic_field.related_model)
        except LookupError:
            raise ImproperlyConfigured(
                f"Related model '{dynamic_field.related_model}' for field '{dynamic_field.name}' cannot be resolved. "
                "Ensure it is in the format '<app_label>.<model_name>'."
            )

        # Add on_delete for ForeignKey and OneToOneField
        if dynamic_field.field_type in ['ForeignKey', 'OneToOneField']:
            kwargs['on_delete'] = getattr(models, dynamic_field.on_delete or 'CASCADE')

    # Add default values for other field types if needed (e.g., FileField)
    # Example: FileField, ImageField
    if dynamic_field.field_type in ['FileField', 'ImageField']:
        if not dynamic_field.upload_to:
            raise ValidationError(f"{dynamic_field.field_type} '{dynamic_field.name}' requires 'upload_to'.")
        kwargs['upload_to'] = dynamic_field.upload_to

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




def sync_model_fields(model, dynamic_fields):
    """
    Synchronize the model fields with the database table.
    - Add missing fields.
    - Remove deprecated fields.
    - Update existing fields, including handling type changes.
    """
    if get_connection().in_atomic_block:
        # Exit the atomic block explicitly if inside one
        get_connection().commit()

    disable_foreign_keys()  # Scoped disabling for SQLite foreign key constraints
    try:
        with connection.schema_editor() as schema_editor:
            existing_fields = {field.name: field for field in model._meta.fields}

            for dynamic_field in dynamic_fields:
                field_name = dynamic_field.name
                field_class = getattr(models, dynamic_field.field_type)
                field_kwargs = generate_field_kwargs(dynamic_field)

                # Create a new field instance for comparison and schema operations
                new_field = field_class(**field_kwargs)
                new_field.set_attributes_from_name(field_name)

                if field_name in existing_fields:
                    existing_field = existing_fields[field_name]

                    # Alter the field if type or attributes differ
                    if not isinstance(existing_field, field_class) or field_kwargs != existing_field.deconstruct()[3]:
                        schema_editor.alter_field(model, existing_field, new_field)
                else:
                    # Add the new field
                    schema_editor.add_field(model, new_field)

            # Remove fields that are no longer present
            dynamic_field_names = {field.name for field in dynamic_fields}
            for field_name, existing_field in existing_fields.items():
                if field_name not in dynamic_field_names and field_name != 'id':  # Keep 'id' intact
                    schema_editor.remove_field(model, existing_field)
    finally:
        enable_foreign_keys()
