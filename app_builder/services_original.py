import uuid
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import ApplicationDefinition, ModelDefinition, FieldDefinition, RelationshipDefinition

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
    Convert a string like 'max_length=100,unique=True'
    into a dict: {'max_length': '100', 'unique': 'True'}.
    """
    if not options_str.strip():
        return {}
    pairs = [p.strip() for p in options_str.split(",") if p.strip()]
    result = {}
    for pair in pairs:
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        result[k.strip()] = v.strip()
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
def create_application_from_diagram(diagram_data):
    """
    Creates a new ApplicationDefinition and all related ModelDefinitions,
    FieldDefinitions, and RelationshipDefinitions from the given diagram JSON.
    """

    # -----------------
    # 1) Create the Application
    # -----------------

    app_name = diagram_data.get("name", "untitled_app")
    # Potentially sanitize the name to be a valid Python identifier:
    # e.g. replace spaces, uppercase first letter, etc.
    safe_app_name = app_name.lower().replace(" ", "_")
    unique_suffix = str(uuid.uuid4())[:8]
    safe_app_name += f"_{unique_suffix}"
    application = ApplicationDefinition.objects.create(
        app_name=safe_app_name,
        erd_json = diagram_data,
        overwrite=False,
        skip_admin=False,
        skip_tests=False,
        skip_urls=False
    )

    # We'll keep a dict to map: table_json_id -> ModelDefinition instance
    table_id_to_modeldef = {}
    # We'll keep another dict to map: field_json_id -> FieldDefinition instance
    field_id_to_fielddef = {}


    # A mapping to store relational field names by their IDs
    relationship_field_names = {}

    # -----------------
    # 2.1) Preprocess Relational Fields
    # -----------------
    # Identify all field IDs that are used as part of relationships to exclude them from regular fields.
    relational_field_ids = set()
    for rel in diagram_data.get("relationships", []):
        source_field_id = rel["sourceFieldId"]
        target_field_id = rel["targetFieldId"]

        # Add field IDs to the relational field set
        relational_field_ids.add(source_field_id)
        relational_field_ids.add(target_field_id)

        # Capture the field names for relational fields
        for table in diagram_data.get("tables", []):
            for field in table.get("fields", []):
                if field["id"] == source_field_id or field["id"] == target_field_id:
                    field_name = field.get("name", "unnamed_field").replace(" ", "_")
                    relationship_field_names[field["id"]] = field_name


    # -----------------
    # 2.1) Create ModelDefinitions & Fields
    # -----------------
    for table in diagram_data.get("tables", []):
        table_id = table["id"]
        table_name = table["name"].replace(" ", "_")

        # Skip creation if table name has a dot, e.g. "lookup.Lookups"
        if "." in table_name:
            # We do NOT create a ModelDefinition for such tables
            print(f"Skipping table '{table_name}' because it contains '.' (external model).")
            continue

        # Create the model definition
        model_def = ModelDefinition.objects.create(
            application=application,
            model_name=table_name,
            db_table="",
            verbose_name=table_name.capitalize(),
            verbose_name_plural=table_name.capitalize() + "s",
            ordering="",
            unique_together=None,
            indexes=None,
            constraints=None
        )
        table_id_to_modeldef[table_id] = model_def

        # 2A) Create fields
        for field in table.get("fields", []):
            field_id = field["id"]

            # If the field is relational, store its name and skip its creation in the fields list
            if field_id in relational_field_ids:
                continue

            field_name = field.get("name", "unnamed_field").replace(" ", "_")

            # Map the diagram's type to a Django field type
            raw_pg_type = field["type"]["id"].lower()  # e.g. "bigint"
            mapped_field_type = FIELD_TYPE_MAP.get(raw_pg_type, "CharField")

            # Build the "options" string based on unique/nullable, etc.
            # For example:
            options_list = []

            # If not nullable => do nothing (Django default is null=False, blank=False)
            # If it is nullable => add "null=True, blank=True"
            if field.get("nullable") is True:
                if mapped_field_type not in ("AutoField", "BigAutoField"):
                    options_list.append("null=True")

            if field.get("blank") is True:
                if mapped_field_type not in ("AutoField", "BigAutoField"):
                    options_list.append("blank=True")

            if field.get("max_length"):
                if mapped_field_type not in ("AutoField", "BigAutoField"):
                    options_list.append(f'max_length={int(field["max_length"])}')

            if field.get("max_digits") is not None and field.get("decimal_places") is not None:
                if mapped_field_type in ("DecimalField", "FloatField"):
                    try:
                        options_list.append(f'max_digits={int(field["max_digits"])}')
                        options_list.append(f'decimal_places={int(field["decimal_places"])}')
                    except:
                        pass

            # If "unique": True and it's only a single field, we can place "unique=True"
            if field.get("unique") is True:
                if mapped_field_type not in ("AutoField", "BigAutoField"):
                    options_list.append("unique=True")

            # If "primaryKey": True => store "primary_key=True"
            if field.get("primaryKey") is True:
                options_list.append("primary_key=True")

            # Build a comma-separated string from options_list
            options_str = ','.join(options_list)

            # --- Parse to inject default values for CharField/DecimalField ---
            opt_dict = parse_options_str(options_str)

            if mapped_field_type == "CharField":
                if "max_length" not in opt_dict:
                    opt_dict["max_length"] = "255"

            elif mapped_field_type == "DecimalField":
                if "max_digits" not in opt_dict:
                    opt_dict["max_digits"] = "10"
                if "decimal_places" not in opt_dict:
                    opt_dict["decimal_places"] = "2"

            # Rebuild the final options string
            final_options_str = build_options_str(opt_dict)

            field_def = FieldDefinition.objects.create(
                model_definition=model_def,
                field_name=field_name,
                field_type=mapped_field_type,
                options=final_options_str,
                has_choices=False,
                choices_json=None
            )
            field_id_to_fielddef[field_id] = field_def

    # -----------------
    # 3) Handle Indexes
    # -----------------
    # If your diagram JSON includes indexes for each table, you can store
    # them in ModelDefinition.indexes (JSONField on your model).
    #     # -----------------
    #     # 4) Handle Indexes
    #     # -----------------
    for table in diagram_data.get("tables", []):
        table_id = table["id"]
        if table_id not in table_id_to_modeldef:
            continue

        model_def = table_id_to_modeldef[table_id]
        indexes_json = []

        for index_data in table.get("indexes", []):
            field_ids = index_data.get("fieldIds", [])
            fields_names = [
                field_id_to_fielddef[fid].field_name for fid in field_ids if fid in field_id_to_fielddef
            ]
            if not fields_names:
                continue
            indexes_json.append({
                "name": index_data["name"],
                "fields": fields_names,
                "unique": index_data.get("unique", False)
            })

        if indexes_json:
            model_def.indexes = indexes_json
            model_def.save()
    # for table in diagram_data.get("tables", []):
    #     table_id = table["id"]
    #     table_name = table["name"].replace(" ", "_")
    #
    #     # If we skipped this table earlier, don't do indexes for it
    #     if "." in table_name:
    #         continue
    #
    #     model_def = table_id_to_modeldef[table_id]
    #     indexes_json = []
    #
    #     for index_data in table.get("indexes", []):
    #         # "index_data" might look like:
    #         # {
    #         #   "id": "74",
    #         #   "name": "index_1",
    #         #   "fieldIds": ["70","71"],
    #         #   "unique": true,
    #         #   "createdAt": 1737971159389
    #         # }
    #         field_ids = index_data.get("fieldIds", [])
    #         # We must convert these IDs to field names:
    #         fields_names = []
    #         for fid in field_ids:
    #             if fid in field_id_to_fielddef:
    #                 fields_names.append(field_id_to_fielddef[fid].field_name)
    #             else:
    #                 # We can either ignore or raise an error if we can't find the field.
    #                 raise ValidationError(
    #                     f"Index references unknown field id={fid} in table {table['name']}"
    #                 )
    #
    #         # Now append this index definition to the model's index list
    #         indexes_json.append({
    #             "name": index_data["name"],
    #             "fields": fields_names,
    #             "unique": index_data.get("unique", False)
    #         })
    #
    #     # Store the indexes in ModelDefinition.indexes
    #     if indexes_json:
    #         model_def.indexes = indexes_json
    #         model_def.save()

    # -----------------
    # 4) Create RelationshipDefinitions
    # -----------------
    # For relationships, you have:
    #  {
    #    "id": "85",
    #    "name": "table_2_field_2_fk",
    #    "sourceTableId": "68",
    #    "targetTableId": "77",
    #    "sourceFieldId": "70",
    #    "targetFieldId": "78",
    #    "sourceCardinality": "one",
    #    "targetCardinality": "many"
    #  }
    # We'll interpret cardinalities as:
    #  - one-to-many => ForeignKey on the "many" side referencing "one"
    #  - many-to-many => ManyToManyField
    #  - one-to-one => OneToOneField

    for rel in diagram_data.get("relationships", []):
        source_table_id = rel["sourceTableId"]
        target_table_id = rel["targetTableId"]

        if source_table_id not in table_id_to_modeldef:
            continue
        # If the source or target table was skipped, interpret that as an external model
        if source_table_id in table_id_to_modeldef:
            source_model_def = table_id_to_modeldef[source_table_id]
            source_name = source_model_def.model_name
        else:
            # We skip creation for that table => get the actual table name from the JSON
            source_table_json = next(
                (t for t in diagram_data["tables"] if t["id"] == source_table_id),
                None
            )
            if source_table_json:
                source_name = source_table_json["name"].replace(" ", "_")
            else:
                source_name = f"unknown_source_{source_table_id}"
            source_model_def = None

        if target_table_id in table_id_to_modeldef:
            target_model_def = table_id_to_modeldef[target_table_id]
            target_name = target_model_def.model_name
        else:
            # Also interpret it as external model
            target_table_json = next(
                (t for t in diagram_data["tables"] if t["id"] == target_table_id),
                None
            )
            if target_table_json:
                target_name = target_table_json["name"].replace(" ", "_")
            else:
                target_name = f"unknown_target_{target_table_id}"
            target_model_def = None

        source_card = rel.get("sourceCardinality", "many")
        target_card = rel.get("targetCardinality", "many")

        if source_card == "one" and target_card == "many":
            relation_type = "ForeignKey"
            model_with_fk = target_model_def
            related_model = f"{application.app_name}.{source_name}"

        elif source_card == "many" and target_card == "one":
            relation_type = "ForeignKey"
            model_with_fk = source_model_def
            related_model = f"{application.app_name}.{target_name}"

        elif source_card == "one" and target_card == "one":
            relation_type = "OneToOneField"
            model_with_fk = source_model_def  # or target_model_def, your logic
            related_model = f"{application.app_name}.{target_name}"

        elif source_card == "many" and target_card == "many":
            relation_type = "ManyToManyField"
            model_with_fk = source_model_def
            related_model = f"{application.app_name}.{target_name}"

        else:
            # If there's some unrecognized combination, default to ManyToMany
            relation_type = "ManyToManyField"
            model_with_fk = source_model_def
            related_model = f"{application.app_name}.{target_name}"

        # If either side is an external model (with dot name), use that dotted name
        if target_model_def is None and "." in target_name:
            related_model = target_name
        if source_model_def is None and "." in source_name:
            related_model = source_name
            model_with_fk = target_model_def

        # Build the "options" string. Handle "onDelete" and "limitedTo".
        if relation_type in ("ForeignKey", "OneToOneField"):
            on_delete_action = rel.get("onDelete", "CASCADE").upper()  # Default to "CASCADE"
            if on_delete_action not in ["CASCADE", "SET_NULL", "RESTRICT", "DO_NOTHING", "PROTECT"]:
                raise ValidationError(f"Invalid onDelete action: {on_delete_action}")
            options_str = f'on_delete=models.{on_delete_action}'
            if on_delete_action == 'SET_NULL':
                options_str += f', null=True'

        else:
            options_str = ''

        # Add limitedTo to options if provided
        limited_to = rel.get("limitedTo")
        if limited_to:
            if options_str:
                options_str += f', limit_choices_to={limited_to}'
            else:
                options_str = f'limit_choices_to={limited_to}'
        # Only create RelationshipDefinition if we have a local model_with_fk
        if model_with_fk:
            RelationshipDefinition.objects.create(
                model_definition=model_with_fk,
                relation_name = relationship_field_names.get(rel["sourceFieldId"], rel["name"]),
                relation_type=relation_type,
                related_model=related_model,
                options=options_str
            )
        else:
            print(
                f"Skipping Relationship '{rel['name']}' because the local model was skipped. "
                f"(External relation to '{related_model}')"
            )

    # Return the top-level Application so you can reference it
    return application
