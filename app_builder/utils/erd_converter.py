# app_builder/utils/erd_converter.py

import json
import re
from typing import Dict, List, Any, Optional, Tuple, Set
import uuid
from collections import defaultdict

class ERDToDjangoConverter:
    """
    Intelligent converter that transforms any ERD-generated JSON to Django-compatible format.
    Uses pattern recognition and smart detection for dynamic conversion.
    """

    # Reserved Django model method names and Python keywords
    RESERVED_KEYWORDS = {
        # Django model methods
        'save', 'delete', 'clean', 'full_clean', 'validate_unique',
        'prepare_database_save', 'natural_key', 'get_absolute_url',
        'get_deferred_fields', 'refresh_from_db', 'serializable_value',
        'check', 'clean_fields', 'date_error_message', 'get_constraints',
        'get_indexes', 'validate_constraints', 'unique_error_message',
        'pk', 'objects', 'DoesNotExist', 'MultipleObjectsReturned',
        '_meta', '_state', '__module__', '__qualname__', '__doc__',

        # Python built-ins
        'class', 'def', 'return', 'if', 'else', 'elif', 'while', 'for',
        'in', 'is', 'not', 'and', 'or', 'True', 'False', 'None',
        'import', 'from', 'as', 'try', 'except', 'finally', 'raise',
        'with', 'yield', 'lambda', 'global', 'nonlocal', 'del',
        'pass', 'break', 'continue', 'assert',
    }

    # Comprehensive field type mapping with fallbacks
    FIELD_TYPE_MAP = {
        # Integer types
        "tinyint": "SmallIntegerField",  # Will be overridden for boolean detection
        "smallint": "SmallIntegerField",
        "mediumint": "IntegerField",
        "int": "IntegerField",
        "integer": "IntegerField",
        "bigint": "BigIntegerField",
        "serial": "AutoField",
        "bigserial": "BigAutoField",
        "smallserial": "SmallAutoField",

        # Decimal/Float types
        "decimal": "DecimalField",
        "numeric": "DecimalField",
        "float": "FloatField",
        "real": "FloatField",
        "double": "FloatField",
        "double precision": "FloatField",
        "money": "DecimalField",

        # String types
        "char": "CharField",
        "varchar": "CharField",
        "character": "CharField",
        "character varying": "CharField",
        "nchar": "CharField",
        "nvarchar": "CharField",
        "text": "TextField",
        "tinytext": "TextField",
        "mediumtext": "TextField",
        "longtext": "TextField",
        "ntext": "TextField",
        "clob": "TextField",

        # Binary types
        "binary": "BinaryField",
        "varbinary": "BinaryField",
        "blob": "BinaryField",
        "tinyblob": "BinaryField",
        "mediumblob": "BinaryField",
        "longblob": "BinaryField",
        "bytea": "BinaryField",

        # Date/Time types
        "date": "DateField",
        "datetime": "DateTimeField",
        "datetime2": "DateTimeField",
        "timestamp": "DateTimeField",
        "timestamp with time zone": "DateTimeField",
        "timestamp without time zone": "DateTimeField",
        "timestamptz": "DateTimeField",
        "time": "TimeField",
        "time with time zone": "TimeField",
        "time without time zone": "TimeField",
        "timetz": "TimeField",
        "year": "IntegerField",
        "interval": "DurationField",

        # Boolean type
        "boolean": "BooleanField",
        "bool": "BooleanField",
        "bit": "BooleanField",

        # Special types
        "uuid": "UUIDField",
        "guid": "UUIDField",
        "json": "JSONField",
        "jsonb": "JSONField",
        "xml": "TextField",
        "array": "JSONField",
        "inet": "GenericIPAddressField",
        "cidr": "GenericIPAddressField",
        "macaddr": "CharField",
        "macaddr8": "CharField",

        # Geometric types (PostGIS) - fallback to text
        "point": "TextField",
        "line": "TextField",
        "polygon": "TextField",
        "geometry": "TextField",
        "geography": "TextField",
    }

    # Pattern-based field type detection
    FIELD_PATTERNS = {
        # Boolean patterns
        r'^(is_|has_|can_|should_|was_|will_|did_|does_|are_|were_)': 'BooleanField',
        r'_(active|enabled|disabled|deleted|verified|confirmed|approved|published|draft|archived|locked|public|private)$': 'BooleanField',
        r'^(active|enabled|disabled|deleted|verified|confirmed|approved|published|visible)$': 'BooleanField',

        # Email patterns
        r'(email|e_mail|mail)': 'EmailField',

        # URL patterns
        r'(url|link|website|homepage|site)': 'URLField',

        # Slug patterns
        r'slug': 'SlugField',

        # UUID patterns
        r'(uuid|guid|unique_id)': 'UUIDField',

        # File patterns
        r'(file|attachment|document)': 'FileField',
        r'(image|photo|picture|avatar|logo|icon)': 'ImageField',

        # IP patterns
        r'(ip_address|ip|ipv4|ipv6|remote_addr)': 'GenericIPAddressField',

        # JSON patterns
        r'(data|metadata|config|settings|options|preferences|properties|attributes|params|extra)$': 'JSONField',
    }

    # Patterns to detect lookup-related fields
    LOOKUP_FIELD_PATTERNS = [
        r'_type$', r'_status$', r'_category$', r'_kind$', r'_class$',
        r'^type$', r'^status$', r'^category$', r'^kind$', r'^class$',
        r'_lookup$', r'^lookup$'
    ]

    def __init__(self):
        self.warnings = []
        self.field_id_mapping = {}  # Maps field IDs to field info
        self.table_id_mapping = {}  # Maps table IDs to table info
        self.model_name_mapping = {}  # Maps table names to model names
        self.processed_relationships = set()  # Track processed relationships
        self.lookup_categories = {}  # Track lookup categories by table/field

    def convert(self, erd_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Main conversion method with intelligent detection and mapping.
        """
        self.warnings = []
        self.field_id_mapping = {}
        self.table_id_mapping = {}
        self.model_name_mapping = {}
        self.processed_relationships = set()
        self.lookup_categories = {}

        # First pass: Build mappings
        self._build_mappings(erd_json)

        # Second pass: Convert tables to models
        django_models = []
        for table in erd_json.get("tables", []):
            if self._should_skip_table(table):
                continue

            model = self._convert_table_to_model(table, erd_json)
            if model:
                django_models.append(model)

        # Third pass: Process relationships
        self._process_relationships(django_models, erd_json.get("relationships", []))

        # Fourth pass: Clean up and optimize
        self._optimize_models(django_models)

        return django_models

    def _build_mappings(self, erd_json: Dict[str, Any]) -> None:
        """Build comprehensive mappings for all entities."""
        # Map tables
        for table in erd_json.get("tables", []):
            table_id = table.get("id")
            table_name = table.get("name", "")

            # Handle external tables (with dots)
            if "." in table_name:
                app_name, model_name = table_name.split(".", 1)
                sanitized_name = self._sanitize_name(model_name, is_model=True)
                full_name = f"{app_name}.{sanitized_name}"
            else:
                sanitized_name = self._sanitize_name(table_name, is_model=True)
                full_name = sanitized_name

            self.table_id_mapping[table_id] = {
                "original_name": table_name,
                "model_name": sanitized_name,
                "full_name": full_name,
                "is_external": "." in table_name,
                "table": table
            }
            self.model_name_mapping[table_name] = full_name

            # Map fields
            for field in table.get("fields", []):
                field_id = field.get("id")
                self.field_id_mapping[field_id] = {
                    "table_id": table_id,
                    "field": field,
                    "original_name": field.get("name", ""),
                    "sanitized_name": self._sanitize_name(field.get("name", ""))
                }

    def _should_skip_table(self, table: Dict[str, Any]) -> bool:
        """Intelligently determine if a table should be skipped."""
        table_name = table.get("name", "").lower()

        # Skip Django internal tables
        django_prefixes = ['django_', 'auth_', 'admin_', 'contenttypes_', 'sessions_']
        if any(table_name.startswith(prefix) for prefix in django_prefixes):
            self.warnings.append(f"Skipping Django internal table: {table_name}")
            return True

        # Convert views to proxy models instead of skipping
        if table.get("isView") or table.get("isMaterializedView"):
            # We'll handle views differently - create as proxy models
            return False

        # Skip external tables (handled in relationships)
        if "." in table.get("name", ""):
            return True

        return False

    def _sanitize_name(self, name: str, is_model: bool = False) -> str:
        """Sanitize names with intelligent rules."""
        if not name:
            return "unnamed_field" if not is_model else "UnnamedModel"

        original = name

        # Remove schema prefix
        if "." in name:
            parts = name.split(".")
            name = parts[-1]

        # Replace special characters
        name = re.sub(r'[^\w]', '_', name)

        # Remove consecutive underscores
        name = re.sub(r'_+', '_', name)

        # Remove leading/trailing underscores
        name = name.strip('_')

        # Handle empty result
        if not name:
            name = "field" if not is_model else "Model"

        # Ensure starts with letter
        if name[0].isdigit():
            name = f"{'field' if not is_model else 'Model'}_{name}"

        # Handle reserved words
        if name.lower() in self.RESERVED_KEYWORDS:
            if is_model:
                name = f"{name}Model"
            else:
                name = f"{name}_field"
            self.warnings.append(f"Renamed '{original}' to '{name}' (reserved keyword)")

        # Apply proper casing
        if is_model:
            # Convert to PascalCase
            parts = name.split('_')
            name = ''.join(part.capitalize() for part in parts if part)
        else:
            # Keep as snake_case but lowercase
            name = name.lower()

        return name

    def _detect_field_type_by_pattern(self, field_name: str, db_type: str) -> Optional[str]:
        """Detect field type based on naming patterns."""
        field_name_lower = field_name.lower()

        # Check patterns
        for pattern, django_type in self.FIELD_PATTERNS.items():
            if re.search(pattern, field_name_lower):
                return django_type

        # Special case for tinyint(1) as boolean
        if db_type == "tinyint" and "(" in str(db_type):
            match = re.search(r'\((\d+)\)', str(db_type))
            if match and match.group(1) == "1":
                return "BooleanField"

        return None

    def _is_lookup_field(self, field_name: str, table_name: str) -> bool:
        """Detect if a field is likely a lookup field based on patterns."""
        field_name_lower = field_name.lower()

        # Check if field name matches lookup patterns
        for pattern in self.LOOKUP_FIELD_PATTERNS:
            if re.search(pattern, field_name_lower):
                return True

        return False

    def _derive_lookup_category(self, field_name: str, table_name: str) -> str:
        """Derive lookup category name from field and table names."""
        field_name_lower = field_name.lower()
        table_name_parts = table_name.split('_')

        # Clean field name by removing common suffixes
        cleaned_field = re.sub(r'(_type|_status|_category|_kind|_class|_lookup)$', '', field_name_lower)

        # Create category name
        if cleaned_field in ['type', 'status', 'category', 'kind', 'class']:
            # Generic field names - use table name for context
            category_parts = []
            for part in table_name_parts:
                category_parts.append(part.capitalize())
            category_parts.append(field_name.capitalize())
            return ' '.join(category_parts)
        else:
            # Specific field names - use the field name itself
            parts = cleaned_field.split('_')
            return ' '.join(part.capitalize() for part in parts) + ' Type'

    def _convert_table_to_model(self, table: Dict[str, Any], erd_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert table to Django model with intelligent field detection."""
        table_info = self.table_id_mapping.get(table.get("id"))
        if not table_info:
            return None

        model = {
            "name": table_info["model_name"],
            "fields": [],
            "relationships": [],
            "meta": {}
        }

        # Handle views as unmanaged models
        is_view = table.get("isView") or table.get("isMaterializedView")
        if is_view:
            model["meta"]["managed"] = False
            view_type = "materialized view" if table.get("isMaterializedView") else "view"
            self.warnings.append(
                f"Table '{table.get('name')}' is a {view_type} - creating as unmanaged model"
            )

        # Set db_table if different from model name
        original_table_name = table.get("name", "")
        if original_table_name and original_table_name != table_info["model_name"]:
            model["meta"]["db_table"] = original_table_name

        # Track which fields are used in relationships
        relationship_field_ids = set()
        for rel in erd_json.get("relationships", []):
            relationship_field_ids.add(rel.get("sourceFieldId"))
            relationship_field_ids.add(rel.get("targetFieldId"))

        # Process fields
        for field in table.get("fields", []):
            field_id = field.get("id")

            # Skip if used in relationship (will be handled later)
            if field_id in relationship_field_ids:
                # But store lookup category info if it's a lookup field
                field_name = field.get("name", "")
                if self._is_lookup_field(field_name, original_table_name):
                    self.lookup_categories[field_id] = self._derive_lookup_category(field_name, original_table_name)
                continue

            django_field = self._convert_field(field, table)
            if django_field:
                model["fields"].append(django_field)

        # Process indexes
        indexes = self._convert_indexes(table.get("indexes", []), model["fields"])
        if indexes:
            model["meta"]["indexes"] = indexes

        # Add other meta options
        if table.get("comment"):
            model["meta"]["verbose_name"] = table["comment"]
            model["meta"]["verbose_name_plural"] = f"{table['comment']}s"

        return model

    def _convert_field(self, field: Dict[str, Any], table: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert field with intelligent type detection and auto-fixing."""
        field_info = self.field_id_mapping.get(field.get("id"))
        if not field_info:
            return None

        field_name = field_info["sanitized_name"]
        original_name = field.get("name", "")

        # Skip auto-generated ID fields
        if (field_name.lower() == "id" and field.get("primaryKey") and
                field.get("type", {}).get("name", "").lower() in ["int", "bigint", "serial"]):
            return None

        # Get database type
        db_type = field.get("type", {})
        if isinstance(db_type, dict):
            db_type_name = db_type.get("name", db_type.get("id", "varchar")).lower()
        else:
            db_type_name = str(db_type).lower()

        # Try pattern-based detection first
        django_type = self._detect_field_type_by_pattern(field_name, db_type_name)

        # Fall back to type mapping
        if not django_type:
            django_type = self.FIELD_TYPE_MAP.get(db_type_name)

        # If still unknown, make intelligent guess
        if not django_type:
            # Try to guess based on the type name
            if any(x in db_type_name for x in ["int", "num", "serial"]):
                django_type = "IntegerField"
            elif any(x in db_type_name for x in ["char", "text", "string"]):
                django_type = "CharField"
            elif any(x in db_type_name for x in ["date", "time"]):
                django_type = "DateTimeField"
            elif any(x in db_type_name for x in ["bool", "bit"]):
                django_type = "BooleanField"
            elif any(x in db_type_name for x in ["dec", "float", "real", "double"]):
                django_type = "DecimalField"
            else:
                # Last resort: CharField
                django_type = "CharField"
                self.warnings.append(
                    f"Unknown field type '{db_type_name}' for field '{original_name}' - using CharField"
                )

        # Build field definition
        django_field = {
            "name": field_name,
            "type": django_type,
            "options": self._build_field_options(field, django_type, db_type_name)
        }

        # Handle choices
        if "choices" in field and field["choices"]:
            self._process_choices(django_field, field)

        # Handle collation (just note it, can't fix automatically)
        if field.get("collation") and django_type in ["CharField", "TextField"]:
            # Don't warn for common collations
            if field["collation"] not in ["utf8mb4_0900_ai_ci", "utf8mb4_unicode_ci", "utf8_general_ci"]:
                self.warnings.append(
                    f"Field '{original_name}' has collation '{field['collation']}' - "
                    f"configure in database settings if needed"
                )

        return django_field

    def _build_field_options(self, field: Dict[str, Any], django_type: str, db_type: str) -> str:
        """Build field options with intelligent defaults."""
        options = []
        options_dict = {}

        # Required field type options
        if django_type == "CharField":
            # Extract max_length from various sources
            max_length = None

            # From field definition
            if "maxLength" in field:
                max_length = field["maxLength"]
            elif "max_length" in field:
                max_length = field["max_length"]
            elif "length" in field:
                max_length = field["length"]

            # From type definition (e.g., varchar(255))
            if not max_length and "(" in str(field.get("type", {})):
                match = re.search(r'\((\d+)\)', str(field.get("type", {})))
                if match:
                    max_length = int(match.group(1))

            options_dict["max_length"] = max_length or 255

        elif django_type == "DecimalField":
            # Extract precision and scale
            max_digits = field.get("precision") or field.get("max_digits") or 10
            decimal_places = field.get("scale") or field.get("decimal_places") or 2

            # Try to extract from type (e.g., decimal(10,2))
            type_str = str(field.get("type", {}))
            match = re.search(r'\((\d+),\s*(\d+)\)', type_str)
            if match:
                max_digits = int(match.group(1))
                decimal_places = int(match.group(2))

            options_dict["max_digits"] = max_digits
            options_dict["decimal_places"] = decimal_places

        elif django_type in ["FileField", "ImageField"]:
            # Intelligent upload_to path
            field_name = field.get("name", "file").lower()
            if "image" in field_name or "photo" in field_name:
                upload_to = "images/"
            elif "document" in field_name:
                upload_to = "documents/"
            elif "avatar" in field_name:
                upload_to = "avatars/"
            else:
                upload_to = "uploads/"
            options_dict["upload_to"] = f"'{upload_to}'"

        # Nullable handling
        is_nullable = field.get("nullable", True)
        is_primary = field.get("primaryKey", False)

        if not is_primary:
            if is_nullable:
                options_dict["null"] = True
                if django_type not in ["BooleanField", "ManyToManyField"]:
                    options_dict["blank"] = True
            else:
                # Non-nullable fields might need defaults
                if django_type == "BooleanField":
                    options_dict["default"] = False

        # Unique constraint
        if field.get("unique") and not is_primary:
            options_dict["unique"] = True

        # Default values
        if "default" in field and field["default"] is not None:
            default = field["default"]
            if isinstance(default, str):
                # Handle special defaults
                if default.lower() in ["current_timestamp", "now()"]:
                    if django_type == "DateTimeField":
                        options_dict["auto_now_add"] = True
                    elif django_type == "DateField":
                        options_dict["auto_now_add"] = True
                else:
                    options_dict["default"] = f"'{default}'"
            else:
                options_dict["default"] = default

        # Auto timestamps
        field_name_lower = field.get("name", "").lower()
        if django_type in ["DateTimeField", "DateField"]:
            if field_name_lower in ["created_at", "created", "created_on", "date_created"]:
                options_dict["auto_now_add"] = True
            elif field_name_lower in ["updated_at", "updated", "modified", "modified_at", "last_modified"]:
                options_dict["auto_now"] = True

        # Collation for text fields
        if "collation" in field and django_type in ["CharField", "TextField"]:
            # Store as comment, Django doesn't directly support collation in field definition
            self.warnings.append(f"Field '{field.get('name')}' has collation '{field['collation']}' - may need manual configuration")

        # Build options string
        for key, value in options_dict.items():
            if isinstance(value, bool):
                options.append(f"{key}={value}")
            elif isinstance(value, (int, float)):
                options.append(f"{key}={value}")
            elif isinstance(value, str) and value.startswith("'"):
                options.append(f"{key}={value}")
            else:
                options.append(f"{key}='{value}'")

        return ", ".join(options)

    def _process_choices(self, django_field: Dict[str, Any], field: Dict[str, Any]) -> None:
        """Process field choices."""
        choices = field.get("choices")

        # Handle different choice formats
        if isinstance(choices, str):
            # Try to parse string representation of choices
            try:
                # Handle format: "[('key1', 'value1'), ('key2', 'value2')]"
                if choices.startswith("[") and choices.endswith("]"):
                    django_field["choices"] = eval(choices)  # Be careful with eval in production
                else:
                    # Handle format: "key1:value1,key2:value2"
                    choice_list = []
                    for item in choices.split(","):
                        if ":" in item:
                            key, value = item.split(":", 1)
                            choice_list.append([key.strip(), value.strip()])
                    if choice_list:
                        django_field["choices"] = choice_list
            except:
                self.warnings.append(f"Could not parse choices for field '{field.get('name')}'")
        elif isinstance(choices, list):
            django_field["choices"] = choices

    def _convert_indexes(self, indexes: List[Dict[str, Any]], fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert indexes with field name resolution."""
        django_indexes = []
        field_names = {f["name"] for f in fields}

        for idx in indexes:
            # Skip primary key indexes
            if idx.get("name", "").upper() in ["PRIMARY", "PRIMARY KEY"]:
                continue

            index_fields = []
            for field_id in idx.get("fieldIds", []):
                field_info = self.field_id_mapping.get(field_id)
                if field_info and field_info["sanitized_name"] in field_names:
                    index_fields.append(field_info["sanitized_name"])

            if index_fields:
                django_indexes.append({
                    "name": self._sanitize_index_name(idx.get("name", "")),
                    "fields": index_fields,
                    "unique": idx.get("unique", False)
                })

        return django_indexes

    def _sanitize_index_name(self, name: str) -> str:
        """Sanitize index names for Django."""
        if not name:
            return "idx_unnamed"

        # Remove schema prefix
        name = name.split(".")[-1]

        # Replace invalid characters
        name = re.sub(r'[^\w]', '_', name)

        # Ensure valid length (Django limit is 63 characters for PostgreSQL)
        if len(name) > 60:
            name = name[:60]

        return name.lower()

    def _process_relationships(self, models: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> None:
        """Process relationships with intelligent detection."""
        # Build model lookup
        model_lookup = {}
        for model in models:
            table_id = None
            for tid, info in self.table_id_mapping.items():
                if info["model_name"] == model["name"]:
                    table_id = tid
                    break
            if table_id:
                model_lookup[table_id] = model

        # Process each relationship
        for rel in relationships:
            rel_id = f"{rel.get('sourceTableId')}_{rel.get('targetTableId')}_{rel.get('id')}"
            if rel_id in self.processed_relationships:
                continue

            self.processed_relationships.add(rel_id)
            self._process_single_relationship(rel, model_lookup, models)

    def _process_single_relationship(self, rel: Dict[str, Any], model_lookup: Dict[str, Any], all_models: List[Dict[str, Any]]) -> None:
        """Process a single relationship with better error handling and lookup detection."""
        source_table_id = rel.get("sourceTableId")
        target_table_id = rel.get("targetTableId")
        source_field_id = rel.get("sourceFieldId")
        target_field_id = rel.get("targetFieldId")

        # Get table info
        source_table_info = self.table_id_mapping.get(source_table_id)
        target_table_info = self.table_id_mapping.get(target_table_id)

        if not source_table_info:
            self.warnings.append(f"Skipping relationship '{rel.get('name')}' - source table not found")
            return

        if not target_table_info:
            # Try to handle external models gracefully
            field_info = self.field_id_mapping.get(source_field_id)
            field_name = field_info["sanitized_name"] if field_info else rel.get("name", "related")

            # If it's an external model reference, keep it
            for table in self.table_id_mapping.values():
                if table["table"]["id"] == target_table_id:
                    if table["is_external"]:
                        # It's an external model, this is OK
                        target_table_info = table
                        break

            if not target_table_info:
                self.warnings.append(
                    f"Relationship '{field_name}' references missing model "
                    f"(table_id: {target_table_id}) - skipping relationship"
                )
                return

        # Get models
        source_model = model_lookup.get(source_table_id)
        target_model = model_lookup.get(target_table_id)

        # Determine relationship type
        source_card = rel.get("sourceCardinality", "many")
        target_card = rel.get("targetCardinality", "many")

        # Get field name
        field_info = self.field_id_mapping.get(source_field_id)
        field_name = field_info["sanitized_name"] if field_info else rel.get("name", "related")

        # Check if this is a lookup relationship
        is_lookup_relationship = target_table_info["full_name"] == "lookup.Lookup"

        # Build relationship
        if source_card == "many" and target_card == "one":
            # ForeignKey on source model
            if source_model:
                self._add_relationship(source_model, field_name, "ForeignKey",
                                       target_table_info["full_name"], rel,
                                       is_lookup=is_lookup_relationship,
                                       lookup_category=self.lookup_categories.get(source_field_id))
        elif source_card == "one" and target_card == "many":
            # ForeignKey on target model
            if target_model:
                field_info = self.field_id_mapping.get(target_field_id)
                field_name = field_info["sanitized_name"] if field_info else f"{source_table_info['model_name'].lower()}_id"
                self._add_relationship(target_model, field_name, "ForeignKey",
                                       source_table_info["full_name"], rel)
        elif source_card == "one" and target_card == "one":
            # OneToOneField on source model
            if source_model:
                self._add_relationship(source_model, field_name, "OneToOneField",
                                       target_table_info["full_name"], rel,
                                       is_lookup=is_lookup_relationship,
                                       lookup_category=self.lookup_categories.get(source_field_id))
        elif source_card == "many" and target_card == "many":
            # ManyToManyField on source model
            if source_model:
                self._add_relationship(source_model, field_name, "ManyToManyField",
                                       target_table_info["full_name"], rel)

    def _add_relationship(self, model: Dict[str, Any], field_name: str, rel_type: str,
                          related_model: str, rel_data: Dict[str, Any],
                          is_lookup: bool = False, lookup_category: Optional[str] = None) -> None:
        """Add relationship to model with special handling for lookup relationships."""
        # Remove any existing field with same name
        model["fields"] = [f for f in model["fields"] if f["name"] != field_name]

        # Build options
        options = []

        if rel_type in ["ForeignKey", "OneToOneField"]:
            # Handle on_delete
            on_delete = rel_data.get("onDelete", "CASCADE").upper()
            if on_delete not in ["CASCADE", "SET_NULL", "PROTECT", "RESTRICT", "DO_NOTHING"]:
                on_delete = "CASCADE"
            options.append(f"on_delete=models.{on_delete}")

            # Add null=True if SET_NULL
            if on_delete == "SET_NULL":
                options.append("null=True")
                options.append("blank=True")

        # Special handling for lookup relationships
        if is_lookup and lookup_category:
            # Add limit_choices_to for lookup relationships
            limit_choices_dict = {"parent_lookup__name": lookup_category}
            options.append(f"limit_choices_to={limit_choices_dict}")
            self.warnings.append(f"Added lookup category '{lookup_category}' for field '{field_name}'")
        elif is_lookup and not lookup_category:
            # Try to derive lookup category from field name
            lookup_category = self._derive_lookup_category(field_name, model["name"])
            limit_choices_dict = {"parent_lookup__name": lookup_category}
            options.append(f"limit_choices_to={limit_choices_dict}")
            self.warnings.append(f"Derived lookup category '{lookup_category}' for field '{field_name}'")

        # Handle limit_choices_to from rel_data if provided
        if "limitedTo" in rel_data and not is_lookup:
            limited_to = rel_data["limitedTo"]
            # Fix the format for Django
            if isinstance(limited_to, dict):
                # Convert parent_lookup_name to parent_lookup__name
                fixed_limited = {}
                for key, value in limited_to.items():
                    if key.startswith("parent_lookup_") and "__" not in key:
                        key = key.replace("parent_lookup_", "parent_lookup__", 1)
                    fixed_limited[key] = value
                options.append(f"limit_choices_to={fixed_limited}")

        # Add related_name to avoid clashes
        related_name = f"{model['name'].lower()}_{field_name}_set"
        options.append(f"related_name='{related_name}'")

        # Add relationship
        model["relationships"].append({
            "name": field_name,
            "type": rel_type,
            "related_model": related_model,
            "options": ", ".join(options)
        })

    def _optimize_models(self, models: List[Dict[str, Any]]) -> None:
        """Final optimization pass on models with automatic fixes."""
        model_names = {}

        for model in models:
            # Fix duplicate model names
            original_name = model["name"]
            if original_name in model_names:
                counter = 2
                new_name = f"{original_name}{counter}"
                while new_name in model_names:
                    counter += 1
                    new_name = f"{original_name}{counter}"
                model["name"] = new_name
                self.warnings.append(f"Renamed duplicate model '{original_name}' to '{new_name}'")
            model_names[model["name"]] = True

            # Remove duplicate relationships
            seen = set()
            unique_rels = []
            for rel in model.get("relationships", []):
                key = (rel["name"], rel["type"], rel["related_model"])
                if key not in seen:
                    seen.add(key)
                    unique_rels.append(rel)
            model["relationships"] = unique_rels

            # Ensure model has at least one field (AUTO-FIX)
            if not model["fields"] and not model["relationships"]:
                model["fields"].append({
                    "name": "name",
                    "type": "CharField",
                    "options": "max_length=255"
                })
                self.warnings.append(f"Added default 'name' field to model '{model['name']}' (no fields found)")

            # Add created_at/updated_at if model has no timestamp fields
            field_names = {f["name"] for f in model["fields"]}
            has_created = any(name in field_names for name in ["created_at", "created", "date_created"])
            has_updated = any(name in field_names for name in ["updated_at", "updated", "modified"])

            if not has_created:
                model["fields"].append({
                    "name": "created_at",
                    "type": "DateTimeField",
                    "options": "auto_now_add=True"
                })

            if not has_updated:
                model["fields"].append({
                    "name": "updated_at",
                    "type": "DateTimeField",
                    "options": "auto_now=True"
                })

            # Clean up meta options
            if "meta" in model and not model["meta"]:
                del model["meta"]

    def get_warnings(self) -> List[str]:
        """Get all warnings generated during conversion."""
        return self.warnings

    def validate_output(self, django_models: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate the converted Django models."""
        errors = []
        model_names = set()

        for model in django_models:
            # Check model name
            if not model.get("name"):
                errors.append("Model missing name")
                continue

            # Check for duplicate model names
            if model["name"] in model_names:
                errors.append(f"Duplicate model name: {model['name']}")
            model_names.add(model["name"])

            # Check for at least one field or relationship
            if not model.get("fields") and not model.get("relationships"):
                errors.append(f"Model {model['name']} has no fields or relationships")

            # Validate fields
            field_names = set()
            for field in model.get("fields", []):
                if not field.get("name"):
                    errors.append(f"Field missing name in model {model['name']}")
                elif field["name"] in field_names:
                    errors.append(f"Duplicate field name '{field['name']}' in model {model['name']}")
                field_names.add(field.get("name"))

                if not field.get("type"):
                    errors.append(f"Field {field.get('name')} missing type in model {model['name']}")

            # Validate relationships
            for rel in model.get("relationships", []):
                if not rel.get("name"):
                    errors.append(f"Relationship missing name in model {model['name']}")
                elif rel["name"] in field_names:
                    errors.append(f"Relationship name '{rel['name']}' conflicts with field name in model {model['name']}")

                if not rel.get("type"):
                    errors.append(f"Relationship {rel.get('name')} missing type in model {model['name']}")

                if not rel.get("related_model"):
                    errors.append(f"Relationship {rel.get('name')} missing related_model in model {model['name']}")

        return len(errors) == 0, errors


# Utility function for direct conversion
def convert_erd_to_django(erd_data: Dict[str, Any], app_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert ERD JSON data to Django-compatible format.

    Args:
        erd_data: ERD JSON data (dict, not file path)
        app_name: Optional app name to use for model references

    Returns:
        Dictionary containing converted models and metadata
    """
    converter = ERDToDjangoConverter()
    django_models = converter.convert(erd_data)

    # Apply app name if provided
    if app_name:
        for model in django_models:
            for rel in model.get("relationships", []):
                # Update internal references
                if "." not in rel["related_model"]:
                    # Find if this model exists in our list
                    if any(m["name"] == rel["related_model"] for m in django_models):
                        rel["related_model"] = f"{app_name}.{rel['related_model']}"

    # Validate
    is_valid, errors = converter.validate_output(django_models)

    return {
        "models": django_models,
        "warnings": converter.get_warnings(),
        "errors": errors,
        "is_valid": is_valid,
        "model_count": len(django_models),
        "field_count": sum(len(m.get("fields", [])) for m in django_models),
        "relationship_count": sum(len(m.get("relationships", [])) for m in django_models)
    }