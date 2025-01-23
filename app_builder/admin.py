import json
import subprocess
import tempfile
import os

import sys
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

@admin.action(description="Compile Project For New Applications")
def generate_json_files(modeladmin, request, queryset):
    """
    Admin action to generate JSON files and store them in the specified folder.
    """
    # Define the directory to save JSON files (e.g., "generated_jsons" in the project root)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "generated_application_source")
    os.makedirs(output_dir, exist_ok=True)  # Ensure the directory exists

    for obj in queryset:
        app_name = obj.app_name  # Assuming `app_name` is a field in the model
        schema_data = obj.compile_schema()  # Assuming `compile_schema` generates the data

        try:
            # Save the JSON file in the specified directory
            file_path = os.path.join(output_dir, f"{app_name}.json")
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(schema_data, json_file, indent=4)
            messages.success(request, f"Generated JSON file for application '{app_name}' and saved to {file_path}")
        except Exception as e:
            messages.error(request, f"Failed to generate JSON for '{app_name}': {e}")

    # Add an info message to confirm completion
    messages.info(request, f"All JSON files were saved to: {output_dir}")

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

@admin.action(description="Create Django App(s) from selected definitions")
def create_app_from_definitions(modeladmin, request, queryset):
    """
    For each selected ApplicationDefinition, compile the entire schema to JSON,
    write it to a temp file, and invoke `create_app` with optional flags.
    """
    for definition in queryset:
        app_name = definition.app_name
        schema_data = definition.compile_schema()

        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
                json.dump(schema_data, tmp, indent=4)
                schema_path = tmp.name
        except Exception as e:
            messages.error(request, f"Failed to create temp JSON for {app_name}: {e}")
            continue

        cmd_kwargs = {}
        if definition.overwrite:
            cmd_kwargs["overwrite"] = True
        if definition.skip_admin:
            cmd_kwargs["skip_admin"] = True
        if definition.skip_tests:
            cmd_kwargs["skip_tests"] = True
        if definition.skip_urls:
            cmd_kwargs["skip_urls"] = True

        try:
            # Run the task asynchronously
            create_app_task(app_name, schema_path, **cmd_kwargs)
            messages.success(request, f"Started creation of app '{app_name}' in the background.")
        except Exception as e:
            messages.error(request, f"Error creating app '{app_name}': {e}")
        finally:
            if os.path.exists(schema_path):
                os.remove(schema_path)

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
    list_display = (
        "app_name",
        "overwrite",
        "skip_admin",
        "skip_tests",
        "skip_urls",
        "created_at",
        "updated_at"
    )
    list_filter = ("overwrite", "skip_admin", "skip_tests", "skip_urls", "created_at")
    search_fields = ("app_name",)
    inlines = [ModelDefinitionInline]
    actions = [create_app_from_definitions, generate_json_files]

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
