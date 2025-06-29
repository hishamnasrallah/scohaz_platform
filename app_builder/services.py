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

def parse_options_str(options_str):
    """
    Convert a string like 'max_length=100,unique=True,choices=[('test1','Test1'),('test2','test2')]'
    into a dict: {'max_length': '100', 'unique': 'True', 'choices': "[('test1','Test1'),('test2','test2')]"}.
    """
    if not options_str.strip():
        return {}

    result = {}
    key_value_pairs = []

    # Use regex to split while keeping values in brackets intact
    pattern = r'(\w+)=((?:\[[^\]]*\])|(?:[^,]+))'
    matches = re.findall(pattern, options_str)

    for key, value in matches:
        result[key.strip()] = value.strip()

    return result

def build_options_str(options_dict):
    """
    Convert a dict like {'max_length': '100', 'unique': 'True'}
    back into a string 'max_length=100,unique=True'.
    """
    return ",".join(f"{k}={v}" for k, v in options_dict.items())

# def create_application_from_diagram(diagram_data):
#     """
#     Creates a new ApplicationDefinition and all relaservices.pyted ModelDefinitions,
#     FieldDefinitions, and RelationshipDefinitions from the given diagram JSON.
#     """
#
#     # -----------------
#     # 1) Create the Application
#     # -----------------
#     # Extract the application name from the diagram data or use a default name.
#     app_name = diagram_data.get("name", "untitled_app")
#     # Sanitize the name to ensure it is a valid Python identifier.
#     safe_app_name = app_name.lower().replace(" ", "_")
#     # Add a unique suffix to avoid name collisions.
#     unique_suffix = str(uuid.uuid4())[:8]
#     safe_app_name += f"_{unique_suffix}"
#
#     # Create the ApplicationDefinition object.
#     application = ApplicationDefinition.objects.create(
#         app_name=safe_app_name,
#         overwrite=False,
#         skip_admin=False,
#         skip_tests=False,
#         skip_urls=False
#     )
#
#     # Maps to track relationships between table IDs and model definitions, and field IDs and field definitions.
#     table_id_to_modeldef = {}
#     field_id_to_fielddef = {}
#
#     # -----------------
#     # 2) Preprocess Relational Fields
#     # -----------------
#     # Identify all field IDs that are used as part of relationships to exclude them from regular fields.
#     relational_field_ids = set()
#     for rel in diagram_data.get("relationships", []):
#         relational_field_ids.add(rel["sourceFieldId"])
#         relational_field_ids.add(rel["targetFieldId"])
#
#     # -----------------
#     # 3) Create ModelDefinitions & Fields
#     # -----------------
#     for table in diagram_data.get("tables", []):
#         table_id = table["id"]
#         table_name = table["name"].replace(" ", "_")
#
#         # Skip tables that have a dot in their name (e.g., external models).
#         if "." in table_name:
#             print(f"Skipping table '{table_name}' because it contains '.' (external model).")
#             continue
#
#         # Create the ModelDefinition for this table.
#         model_def = ModelDefinition.objects.create(
#             application=application,
#             model_name=table_name,
#             db_table="",
#             verbose_name=table_name.capitalize(),
#             verbose_name_plural=table_name.capitalize() + "s",
#             ordering="",
#             unique_together=None,
#             indexes=None,
#             constraints=None
#         )
#         table_id_to_modeldef[table_id] = model_def
#
#         # Process fields for this table.
#         for field in table.get("fields", []):
#             field_id = field["id"]
#
#             # Skip relational fields as they are handled separately in relationships.
#             if field_id in relational_field_ids:
#                 continue
#
#             field_name = field.get("name", "unnamed_field").replace(" ", "_")
#             raw_pg_type = field["type"]["id"].lower()
#             mapped_field_type = FIELD_TYPE_MAP.get(raw_pg_type, "CharField")
#
#             # Build the "options" string based on field attributes.
#             options_list = []
#             if field.get("nullable"):
#                 options_list.append("null=True")
#                 options_list.append("blank=True")
#             if field.get("unique"):
#                 options_list.append("unique=True")
#             if field.get("primaryKey"):
#                 options_list.append("primary_key=True")
#
#             options_str = ",".join(options_list)
#             opt_dict = parse_options_str(options_str)
#
#             # Add default values for specific field types.
#             if mapped_field_type == "CharField" and "max_length" not in opt_dict:
#                 opt_dict["max_length"] = "255"
#             if mapped_field_type == "DecimalField":
#                 opt_dict.setdefault("max_digits", "10")
#                 opt_dict.setdefault("decimal_places", "2")
#
#             final_options_str = build_options_str(opt_dict)
#
#             # Create the FieldDefinition for this field.
#             field_def = FieldDefinition.objects.create(
#                 model_definition=model_def,
#                 field_name=field_name,
#                 field_type=mapped_field_type,
#                 options=final_options_str,
#                 has_choices=False,
#                 choices_json=None
#             )
#             field_id_to_fielddef[field_id] = field_def
#
#     # -----------------
#     # 4) Handle Indexes
#     # -----------------
#     for table in diagram_data.get("tables", []):
#         table_id = table["id"]
#         if table_id not in table_id_to_modeldef:
#             continue
#
#         model_def = table_id_to_modeldef[table_id]
#         indexes_json = []
#
#         for index_data in table.get("indexes", []):
#             field_ids = index_data.get("fieldIds", [])
#             fields_names = [
#                 field_id_to_fielddef[fid].field_name for fid in field_ids if fid in field_id_to_fielddef
#             ]
#             if not fields_names:
#                 continue
#             indexes_json.append({
#                 "name": index_data["name"],
#                 "fields": fields_names,
#                 "unique": index_data.get("unique", False)
#             })
#
#         if indexes_json:
#             model_def.indexes = indexes_json
#             model_def.save()
#
#     # -----------------
#     # 5) Create RelationshipDefinitions
#     # -----------------
#     for rel in diagram_data.get("relationships", []):
#         source_table_id = rel["sourceTableId"]
#         target_table_id = rel["targetTableId"]
#         source_field_id = rel["sourceFieldId"]
#
#         if source_table_id not in table_id_to_modeldef:
#             continue
#
#         source_model_def = table_id_to_modeldef[source_table_id]
#         target_model_def = table_id_to_modeldef.get(target_table_id)
#
#         # Use the field name from FieldDefinition if it exists, otherwise use the relationship name.
#         field_name = field_id_to_fielddef[source_field_id].field_name if source_field_id in field_id_to_fielddef else rel["name"]
#
#         source_card = rel.get("sourceCardinality", "many")
#         target_card = rel.get("targetCardinality", "many")
#
#         # Determine the relationship type and options.
#         if source_card == "one" and target_card == "many":
#             relation_type = "ForeignKey"
#             options_str = "on_delete=models.CASCADE"
#         elif source_card == "one" and target_card == "one":
#             relation_type = "OneToOneField"
#             options_str = "on_delete=models.CASCADE"
#         else:
#             relation_type = "ManyToManyField"
#             options_str = ""
#
#         related_model = f"{application.app_name}.{target_model_def.model_name}" if target_model_def else "unknown"
#
#         # Create the RelationshipDefinition for this relationship.
#         RelationshipDefinition.objects.create(
#             model_definition=source_model_def,
#             relation_name=field_name,
#             relation_type=relation_type,
#             related_model=related_model,
#             options=options_str
#         )
#
#     # Return the top-level Application so you can reference it.
#     return application


@transaction.atomic

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


# Keep the original helper functions for backward compatibility
def parse_options_str(options_str):
    """
    Convert a string like 'max_length=100,unique=True,choices=[('test1','Test1'),('test2','test2')]'
    into a dict: {'max_length': '100', 'unique': 'True', 'choices': "[('test1','Test1'),('test2','test2')]"}.
    """
    if not options_str.strip():
        return {}

    result = {}
    # Use regex to split while keeping values in brackets intact
    pattern = r'(\w+)=((?:\[[^\]]*\])|(?:[^,]+))'
    matches = re.findall(pattern, options_str)

    for key, value in matches:
        result[key.strip()] = value.strip()

    return result


def build_options_str(options_dict):
    """
    Convert a dict like {'max_length': '100', 'unique': 'True'}
    back into a string 'max_length=100,unique=True'.
    """
    return ",".join(f"{k}={v}" for k, v in options_dict.items())