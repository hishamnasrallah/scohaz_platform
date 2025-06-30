import re
import uuid
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.functions import Upper

from .models import ApplicationDefinition, ModelDefinition, FieldDefinition, RelationshipDefinition
from .utils.erd_converter import convert_erd_to_django

# A helper function to map the JSON "type" to your internal field_type
FIELD_TYPE_MAP = {
    # --------------------------------------------------------------------------------
    # Numeric Types
    # --------------------------------------------------------------------------------
    "smallint": "SmallIntegerField",
    "integer": "IntegerField",
    "int": "IntegerField",  # generic
    "bigint": "BigIntegerField",
    "decimal": "DecimalField",
    "numeric": "DecimalField",
    "real": "FloatField",
    "float": "FloatField",
    "double_precision": "FloatField",

    # Serial / Auto-incrementing
    "smallserial": "AutoField",          # Django doesn’t have a distinct SmallAutoField
    "serial": "AutoField",
    "bigserial": "BigAutoField",

    # Money
    "money": "DecimalField",

    # --------------------------------------------------------------------------------
    # Character / Text
    # --------------------------------------------------------------------------------
    "char": "CharField",
    "varchar": "CharField",
    "character_varying": "CharField",
    "text": "TextField",
    "bytea": "BinaryField",  # Stores raw binary data

    # --------------------------------------------------------------------------------
    # Date / Time / Interval
    # --------------------------------------------------------------------------------
    "date": "DateField",
    "datetime": "DateTimeField",
    "timestamp": "DateTimeField",
    "timestamp_with_time_zone": "DateTimeField",
    "timestamp_without_time_zone": "DateTimeField",
    "time": "TimeField",
    "time_with_time_zone": "TimeField",
    "time_without_time_zone": "TimeField",
    "interval": "DurationField",  # Django’s DurationField uses an INTERVAL column

    # --------------------------------------------------------------------------------
    # Boolean
    # --------------------------------------------------------------------------------
    "boolean": "BooleanField",

    # --------------------------------------------------------------------------------
    # Enumerations
    # --------------------------------------------------------------------------------
    "enum": "CharField",  # Could be mapped to a CharField (or a custom solution)

    # --------------------------------------------------------------------------------
    # Geometric Types (PostgreSQL-specific)
    # --------------------------------------------------------------------------------
    "point": "CharField",
    "line": "CharField",
    "lseg": "CharField",
    "box": "CharField",
    "path": "CharField",
    "polygon": "CharField",
    "circle": "CharField",

    # --------------------------------------------------------------------------------
    # Network Address Types (PostgreSQL-specific)
    # --------------------------------------------------------------------------------
    "cidr": "GenericIPAddressField",
    "inet": "GenericIPAddressField",
    "macaddr": "CharField",
    "macaddr8": "CharField",

    # --------------------------------------------------------------------------------
    # Bit Strings (PostgreSQL-specific)
    # --------------------------------------------------------------------------------
    "bit": "CharField",
    "bit_varying": "CharField",

    # --------------------------------------------------------------------------------
    # Text Search
    # --------------------------------------------------------------------------------
    "tsvector": "TextField",
    "tsquery": "TextField",

    # --------------------------------------------------------------------------------
    # UUID
    # --------------------------------------------------------------------------------
    "uuid": "UUIDField",

    # --------------------------------------------------------------------------------
    # FILE
    # --------------------------------------------------------------------------------
    "file": "FileField",

    # --------------------------------------------------------------------------------
    # XML
    # --------------------------------------------------------------------------------
    "xml": "TextField",

    # --------------------------------------------------------------------------------
    # JSON
    # --------------------------------------------------------------------------------
    "json": "JSONField",
    "jsonb": "JSONField",
    "array": "JSONField",  # Sometimes arrays can be mapped as JSON lists

    # --------------------------------------------------------------------------------
    # Range Types (PostgreSQL-specific)
    # --------------------------------------------------------------------------------
    "int4range": "CharField",
    "int8range": "CharField",
    "numrange": "CharField",
    "tsrange": "CharField",
    "tstzrange": "CharField",
    "daterange": "CharField",

    # --------------------------------------------------------------------------------
    # OID and System Identifier Types
    # --------------------------------------------------------------------------------
    "oid": "CharField",
    "regproc": "CharField",
    "regprocedure": "CharField",
    "regoper": "CharField",
    "regoperator": "CharField",
    "regclass": "CharField",
    "regtype": "CharField",
    "regrole": "CharField",
    "regnamespace": "CharField",
    "regconfig": "CharField",
    "regdictionary": "CharField",

    # --------------------------------------------------------------------------------
    # User-defined / Unknown
    # --------------------------------------------------------------------------------
    "user-defined": "CharField",
}

@transaction.atomic
def create_application_from_diagram(diagram_data):
    """
    Creates ApplicationDefinition and related models using the intelligent ERD converter.
    This replaces the old basic conversion with smart pattern detection.
    """

    # 1) Extract app name
    app_name = diagram_data.get("name", "untitled_app")
    safe_app_name = re.sub(r'[^a-zA-Z0-9_]', '_', app_name.lower())

    # Add unique suffix to avoid collisions
    unique_suffix = str(uuid.uuid4())[:8]
    safe_app_name = f"{safe_app_name}_{unique_suffix}"

    # 2) Use the intelligent converter
    conversion_result = convert_erd_to_django(diagram_data, app_name=safe_app_name)

    # Check for conversion errors
    if not conversion_result["is_valid"]:
        error_msg = "ERD conversion failed:\n" + "\n".join(conversion_result["errors"])
        raise ValidationError(error_msg)

    # Log warnings if any
    if conversion_result["warnings"]:
        print("Conversion warnings:")
        for warning in conversion_result["warnings"]:
            print(f"  - {warning}")

    # 3) Create ApplicationDefinition
    application = ApplicationDefinition.objects.create(
        app_name=safe_app_name,
        erd_json=diagram_data,
        overwrite=False,
        skip_admin=False,
        skip_tests=False,
        skip_urls=False
    )

    # 4) Create Django model definitions from converted data
    django_models = conversion_result["models"]

    for model_data in django_models:
        # Create ModelDefinition
        model_def = ModelDefinition.objects.create(
            application=application,
            model_name=model_data["name"],
            db_table=model_data.get("meta", {}).get("db_table", ""),
            verbose_name=model_data.get("meta", {}).get("verbose_name", ""),
            verbose_name_plural=model_data.get("meta", {}).get("verbose_name_plural", ""),
            ordering=",".join(model_data.get("meta", {}).get("ordering", [])) if model_data.get("meta", {}).get("ordering") else "",
            unique_together=model_data.get("meta", {}).get("unique_together"),
            indexes=model_data.get("meta", {}).get("indexes"),
            constraints=model_data.get("meta", {}).get("constraints")
        )

        # Create FieldDefinitions
        for field_data in model_data.get("fields", []):
            field_def = FieldDefinition.objects.create(
                model_definition=model_def,
                field_name=field_data["name"],
                field_type=field_data["type"],
                options=field_data.get("options", ""),
                has_choices=bool(field_data.get("choices")),
                choices_json=field_data.get("choices") if field_data.get("choices") else None
            )

        # Create RelationshipDefinitions
        for rel_data in model_data.get("relationships", []):
            # Fix related_model references for internal models
            related_model = rel_data["related_model"]
            if "." not in related_model:
                # It's an internal model, add app prefix
                related_model = f"{safe_app_name}.{related_model}"

            RelationshipDefinition.objects.create(
                model_definition=model_def,
                relation_name=rel_data["name"],
                relation_type=rel_data["type"],
                related_model=related_model,
                options=rel_data.get("options", "")
            )

    # Log summary
    print(f"\nSuccessfully created application '{safe_app_name}':")
    print(f"  - Models: {conversion_result['model_count']}")
    print(f"  - Fields: {conversion_result['field_count']}")
    print(f"  - Relationships: {conversion_result['relationship_count']}")

    return application


def build_options_str(options_dict):
    """
    Convert a dict like {'max_length': '100', 'unique': 'True'}
    back into a string 'max_length=100,unique=True'.
    """
    return ",".join(f"{k}={v}" for k, v in options_dict.items())


def compile_application_programmatically(application_id):
    """
    Compile application without using Django admin/messages framework.
    Returns a dict with success status and any messages.
    """
    import json
    import os
    from django.conf import settings

    result = {
        'success': False,
        'messages': [],
        'errors': [],
        'file_path': None
    }

    try:
        app = ApplicationDefinition.objects.get(id=application_id)
        app_name = app.app_name

        # Check if this was imported from ERD
        if app.erd_json:
            result['messages'].append(f"Converting ERD for '{app_name}' using intelligent converter...")

            conversion_result = convert_erd_to_django(app.erd_json, app_name=app_name)

            if not conversion_result["is_valid"]:
                result['errors'].extend(conversion_result["errors"][:3])
                return result

            schema_data = conversion_result["models"]

            # Collect warnings
            if conversion_result["warnings"]:
                result['messages'].extend([f"[{app_name}] {w}" for w in conversion_result["warnings"]])

            # Show statistics
            result['messages'].append(
                f"Converted '{app_name}': {conversion_result['model_count']} models, "
                f"{conversion_result['field_count']} fields, {conversion_result['relationship_count']} relationships"
            )
        else:
            # Use original compile_schema for manually created definitions
            result['messages'].append(f"Compiling schema for '{app_name}' (manual definition)...")
            schema_data = app.compile_schema()

            # Apply the limit_choices_to fix
            from app_builder.admin import fix_limited_to_keys
            fix_limited_to_keys(schema_data)

        # Write JSON file
        output_dir = os.path.join(settings.BASE_DIR, "generated_application_source")
        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, f"{app_name}.json")
        with open(file_path, "w", encoding="utf-8") as json_file:
            json.dump(schema_data, json_file, indent=4, ensure_ascii=False)

        result['messages'].append(f"Generated JSON for '{app_name}' at {file_path}")
        result['file_path'] = file_path
        result['success'] = True

        # Also save a detailed report for ERD imports
        if app.erd_json:
            report_path = os.path.join(output_dir, f"{app_name}_conversion_report.json")
            with open(report_path, "w", encoding="utf-8") as report_file:
                json.dump(conversion_result, report_file, indent=4, ensure_ascii=False)
            result['messages'].append(f"Saved conversion report at {report_path}")

    except ApplicationDefinition.DoesNotExist:
        result['errors'].append(f"Application with ID {application_id} not found")
    except Exception as e:
        result['errors'].append(f"Failed to process application: {str(e)}")
        import traceback
        result['errors'].append(traceback.format_exc())

    return result