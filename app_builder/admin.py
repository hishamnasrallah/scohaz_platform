import json
import subprocess
import tempfile
import os

import sys
import re

from django.contrib import admin, messages
from django.core.management import call_command
from django.http import HttpResponse

from .models import (
    ApplicationDefinition,
    ModelDefinition,
    FieldDefinition,
    RelationshipDefinition
)
from .tasks import create_app_task
from app_builder.utils.erd_converter import convert_erd_to_django



def fix_limited_to_keys(schema_data):
    """
    Traverse the schema and fix any 'limit_choices_to={...}' inside the 'options' string
    by converting 'parent_lookup_name' → 'parent_lookup__name'.
    """
    def fix_key_format(key):
        if key.startswith("parent_lookup_") and "__" not in key:
            return key.replace("parent_lookup_", "parent_lookup__", 1)
        return key

    def fix_options_string(options_str):
        # Match limit_choices_to={...} using regex
        match = re.search(r"limit_choices_to\s*=\s*({.*?})", options_str)
        if not match:
            return options_str  # No match, return original

        json_part = match.group(1)
        try:
            parsed = json.loads(json_part)
        except json.JSONDecodeError:
            return options_str  # Invalid JSON, skip

        # Fix the keys
        fixed = {fix_key_format(k): v for k, v in parsed.items()}
        fixed_json_str = json.dumps(fixed)

        # Replace only the matched JSON part
        return options_str.replace(json_part, fixed_json_str)

    def process_dict(d):
        for k, v in d.items():
            if k == "options" and isinstance(v, str) and "limit_choices_to" in v:
                d[k] = fix_options_string(v)
            elif isinstance(v, dict):
                process_dict(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        process_dict(item)

    if isinstance(schema_data, list):
        for item in schema_data:
            process_dict(item)
    elif isinstance(schema_data, dict):
        process_dict(schema_data)


@admin.action(description="Compile (with intelligent ERD conversion)")
def generate_json_files_with_conversion(modeladmin, request, queryset):
    """
    Enhanced version that uses intelligent converter for ERD imports.
    This is IN ADDITION to your existing generate_json_files action.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "generated_application_source")
    os.makedirs(output_dir, exist_ok=True)

    success_count = 0
    error_count = 0
    total_warnings = []

    for obj in queryset:
        app_name = obj.app_name

        try:
            # Check if this was imported from ERD
            if obj.erd_json:
                # Use intelligent converter for ERD imports
                messages.info(request, f"Converting ERD for '{app_name}' using intelligent converter...")

                result = convert_erd_to_django(obj.erd_json, app_name=app_name)

                if not result["is_valid"]:
                    messages.error(
                        request,
                        f"Validation failed for '{app_name}': " + "; ".join(result["errors"][:3])
                    )
                    error_count += 1
                    continue

                schema_data = result["models"]

                # Collect warnings
                if result["warnings"]:
                    total_warnings.extend([f"[{app_name}] {w}" for w in result["warnings"]])

                # Show statistics
                messages.info(
                    request,
                    f"Converted '{app_name}': {result['model_count']} models, "
                    f"{result['field_count']} fields, {result['relationship_count']} relationships"
                )
            else:
                # Use original compile_schema for manually created definitions
                messages.info(request, f"Compiling schema for '{app_name}' (manual definition)...")
                schema_data = obj.compile_schema()

                # Apply the limit_choices_to fix from original code
                fix_limited_to_keys(schema_data)

            # Write JSON file
            file_path = os.path.join(output_dir, f"{app_name}.json")
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(schema_data, json_file, indent=4, ensure_ascii=False)

            messages.success(request, f"Generated JSON for '{app_name}' at {file_path}")
            success_count += 1

            # Also save a detailed report for ERD imports
            if obj.erd_json:
                report_path = os.path.join(output_dir, f"{app_name}_conversion_report.json")
                with open(report_path, "w", encoding="utf-8") as report_file:
                    json.dump(result, report_file, indent=4, ensure_ascii=False)

        except Exception as e:
            messages.error(request, f"Failed to process '{app_name}': {e}")
            error_count += 1

    # Summary message
    messages.info(
        request,
        f"✅ Completed: {success_count} successful, {error_count} failed. "
        f"Files saved to: {output_dir}"
    )

    # Show warnings summary if any
    if total_warnings:
        messages.warning(
            request,
            f"⚠️ {len(total_warnings)} total warnings. First 5: " +
            "; ".join(total_warnings[:5])
        )


@admin.action(description="Validate ERD Imports")
def validate_erd_imports(modeladmin, request, queryset):
    """
    Validate ERD imports without generating files.
    NEW ACTION - Add this.
    """
    for obj in queryset:
        if not obj.erd_json:
            messages.info(request, f"'{obj.app_name}' is not an ERD import - skipping validation")
            continue

        try:
            result = convert_erd_to_django(obj.erd_json, app_name=obj.app_name)

            if result["is_valid"]:
                messages.success(
                    request,
                    f"✓ '{obj.app_name}' validation passed - "
                    f"{result['model_count']} models, {result['field_count']} fields"
                )
            else:
                messages.error(
                    request,
                    f"✗ '{obj.app_name}' validation failed: " +
                    "; ".join(result["errors"][:3])
                )

            if result["warnings"]:
                messages.warning(
                    request,
                    f"⚠️ '{obj.app_name}' has {len(result['warnings'])} warnings"
                )

        except Exception as e:
            messages.error(request, f"Error validating '{obj.app_name}': {e}")


@admin.action(description="Export Conversion Report")
def export_conversion_report(modeladmin, request, queryset):
    """
    Export detailed conversion report for ERD imports.
    NEW ACTION - Add this.
    """
    if queryset.count() != 1:
        messages.error(request, "Please select exactly one application")
        return

    obj = queryset.first()

    if not obj.erd_json:
        messages.error(request, "This application was not imported from an ERD")
        return

    try:
        result = convert_erd_to_django(obj.erd_json, app_name=obj.app_name)

        # Create detailed report
        report = {
            "application": {
                "id": obj.id,
                "app_name": obj.app_name,
                "created_at": obj.created_at.isoformat(),
                "has_erd": True
            },
            "conversion": result,
            "original_erd_summary": {
                "tables": len(obj.erd_json.get("tables", [])),
                "relationships": len(obj.erd_json.get("relationships", [])),
                "database_type": obj.erd_json.get("databaseType", "unknown")
            }
        }

        # Return as downloadable JSON
        response = HttpResponse(
            json.dumps(report, indent=2, ensure_ascii=False),
            content_type="application/json"
        )
        response["Content-Disposition"] = f'attachment; filename="{obj.app_name}_conversion_report.json"'
        return response

    except Exception as e:
        messages.error(request, f"Error generating report: {e}")
        return None

@admin.action(description="Compile Project For New Applications")
def generate_json_files(modeladmin, request, queryset):
    import json
    import os

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "generated_application_source")
    os.makedirs(output_dir, exist_ok=True)

    for obj in queryset:
        app_name = obj.app_name
        schema_data = obj.compile_schema()

        print(f"\n📦 Generating for app: {app_name}")
        print("🔍 Original type:", type(schema_data))

        fix_limited_to_keys(schema_data)  # Mutates in-place

        # Optional: Confirm results
        for model in schema_data:
            for rel in model.get("relationships", []):
                if rel.get("limitedTo"):
                    print(f"✅ [{app_name}] fixed limitedTo:", rel["limitedTo"])

        try:
            file_path = os.path.join(output_dir, f"{app_name}.json")
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(schema_data, json_file, indent=4)
            messages.success(request, f"Generated JSON for '{app_name}' at {file_path}")
        except Exception as e:
            messages.error(request, f"Failed to write file for '{app_name}': {e}")

    messages.info(request, f"✅ All JSON files saved to: {output_dir}")


@admin.action(description="Generate JSON files for selected applications")
def generate_json_and_download_it_and_take_copy_to_project_files(modeladmin, request, queryset):
    """
    Admin action to generate JSON files and store them in the project root.
    """
    # Define the directory to save JSON files (e.g., "generated_jsons" in the project root)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "generated_application_source")
    os.makedirs(output_dir, exist_ok=True)  # Ensure the directory exists

    generated_files = []

    for obj in queryset:
        app_name = obj.app_name  # Assuming `app_name` is a field in the model
        schema_data = obj.compile_schema()  # Assuming `compile_schema` generates the data

        try:
            # Create a JSON file in the specified directory
            file_path = os.path.join(output_dir, f"{app_name}.json")
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(schema_data, json_file, indent=4)
                generated_files.append(file_path)
                messages.success(request, f"Generated JSON file for application: {app_name}")

        except Exception as e:
            messages.error(request, f"Failed to generate JSON for {app_name}: {e}")

    # If one file is selected, provide it as a download
    if len(generated_files) == 1:
        with open(generated_files[0], "rb") as file:
            response = HttpResponse(file.read(), content_type="application/json")
            response["Content-Disposition"] = f'attachment; filename="{os.path.basename(generated_files[0])}"'
        return response

    # Inform the user where the files are saved
    messages.info(request, f"JSON files generated successfully and saved to {output_dir}.")
    return None  # Stay on the admin page

# @admin.action(description="Create Django App(s) from selected definitions")
# def create_app_from_definitions(modeladmin, request, queryset):
#     """
#     For each selected ApplicationDefinition, compile the entire schema to JSON,
#     write it to a temp file, and invoke `create_app` with optional flags.
#     """
#     for definition in queryset:
#         app_name = definition.app_name
#         schema_data = definition.compile_schema()
#
#         try:
#             with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
#                 json.dump(schema_data, tmp, indent=4)
#                 schema_path = tmp.name
#         except Exception as e:
#             messages.error(request, f"Failed to create temp JSON for {app_name}: {e}")
#             continue
#
#         cmd_kwargs = {}
#         if definition.overwrite:
#             cmd_kwargs["overwrite"] = True
#         if definition.skip_admin:
#             cmd_kwargs["skip_admin"] = True
#         if definition.skip_tests:
#             cmd_kwargs["skip_tests"] = True
#         if definition.skip_urls:
#             cmd_kwargs["skip_urls"] = True
#
#         try:
#             # Run the task asynchronously
#             create_app_task(app_name, schema_path, **cmd_kwargs)
#             messages.success(request, f"Started creation of app '{app_name}' in the background.")
#         except Exception as e:
#             messages.error(request, f"Error creating app '{app_name}': {e}")
#         finally:
#             if os.path.exists(schema_path):
#                 os.remove(schema_path)

# def create_app_from_definitions(modeladmin, request, queryset):
#     """
#     For each selected ApplicationDefinition, compile the entire schema to JSON,
#     write it to a temp file, and invoke `create_app` with optional flags.
#     """
#     for definition in queryset:
#         app_name = definition.app_name
#         schema_data = definition.compile_schema()
#
#         try:
#             with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
#                 json.dump(schema_data, tmp, indent=4)
#                 schema_path = tmp.name
#         except Exception as e:
#             messages.error(request, f"Failed to create temp JSON for {app_name}: {e}")
#             continue
#
#         cmd_kwargs = {}
#         if definition.overwrite:
#             cmd_kwargs["overwrite"] = True
#         if definition.skip_admin:
#             cmd_kwargs["skip_admin"] = True
#         if definition.skip_tests:
#             cmd_kwargs["skip_tests"] = True
#         if definition.skip_urls:
#             cmd_kwargs["skip_urls"] = True
#
#         try:
#             call_command(
#                 "create_app",
#                 app_name,
#                 models_file=schema_path,
#                 **cmd_kwargs
#             )
#             messages.success(request, f"Created app '{app_name}' successfully.")
#         except Exception as e:
#             messages.error(request, f"Error creating app '{app_name}': {e}")
#         finally:
#             if os.path.exists(schema_path):
#                 os.remove(schema_path)

class ModelDefinitionInline(admin.TabularInline):
    model = ModelDefinition
    extra = 0

@admin.register(ApplicationDefinition)
class ApplicationDefinitionAdmin(admin.ModelAdmin):
    # MODIFY list_display - add these two methods
    list_display = (
        "app_name",
        "is_erd_import",  # ADD THIS
        "model_count",     # ADD THIS
        "overwrite",
        "skip_admin",
        "skip_tests",
        "skip_urls",
        "created_at",
        "updated_at"
    )

    # KEEP your existing list_filter, search_fields, inlines
    list_filter = ("overwrite", "skip_admin", "skip_tests", "skip_urls", "created_at")
    search_fields = ("app_name",)
    inlines = [ModelDefinitionInline]

    # UPDATE actions - add the new ones to your existing list
    actions = [
        # create_app_from_definitions,              # KEEP existing
        generate_json_files,                      # KEEP your original if you want
        generate_json_files_with_conversion,      # ADD this new one
        validate_erd_imports,                     # ADD this new one
        export_conversion_report,                 # ADD this new one
    ]

    # ADD these two methods to your class
    def is_erd_import(self, obj):
        """Check if this was imported from ERD."""
        return bool(obj.erd_json)
    is_erd_import.boolean = True
    is_erd_import.short_description = "ERD Import"

    def model_count(self, obj):
        """Count of models in this application."""
        return obj.modeldefinition_set.count()
    model_count.short_description = "Models"

class FieldDefinitionInline(admin.TabularInline):
    model = FieldDefinition
    extra = 0

class RelationshipDefinitionInline(admin.TabularInline):
    model = RelationshipDefinition
    extra = 0

@admin.register(ModelDefinition)
class ModelDefinitionAdmin(admin.ModelAdmin):
    list_display = ("model_name", "application", "db_table")
    search_fields = ("model_name", "application__app_name")
    list_filter = ("application",)
    inlines = [FieldDefinitionInline, RelationshipDefinitionInline]

@admin.register(FieldDefinition)
class FieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ("field_name", "field_type", "model_definition", "has_choices")
    search_fields = ("field_name",)
    list_filter = ("field_type", "has_choices", "model_definition__model_name")

@admin.register(RelationshipDefinition)
class RelationshipDefinitionAdmin(admin.ModelAdmin):
    list_display = ("relation_name", "relation_type", "related_model", "model_definition")
    search_fields = ("relation_name", "related_model")
    list_filter = ("relation_type", "model_definition__model_name")
