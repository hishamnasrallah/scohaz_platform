import os
import json
import subprocess
import sys
import ast
import logging
from pathlib import Path
from time import sleep

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from django.db import connection

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# You can configure logging handlers as needed
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class Command(BaseCommand):
    help = 'Create a new Django app dynamically with comprehensive configurations.'

    def add_arguments(self, parser):
        parser.add_argument('app_name', type=str, help='Name of the app to create')
        parser.add_argument('--models', type=str, help='JSON definition of the models')
        parser.add_argument('--models-file', type=str, help='Path to a JSON file containing model definitions')
        parser.add_argument('--overwrite', action='store_true', help='Overwrite the app if it exists')
        parser.add_argument('--skip-tests', action='store_true', help='Skip test file generation')
        parser.add_argument('--skip-admin', action='store_true', help='Skip admin registration')
        parser.add_argument('--skip-urls', action='store_true', help='Skip URL generation')

    def handle(self, *args, **kwargs):
        app_name = kwargs['app_name']
        models_definition = kwargs.get('models')
        models_file = kwargs.get('models_file')
        overwrite = kwargs.get('overwrite')
        skip_tests = kwargs.get('skip_tests')
        skip_admin = kwargs.get('skip_admin')
        skip_urls = kwargs.get('skip_urls')

        logger.info(f"Starting creation of app '{app_name}'...")

        if not app_name.isidentifier():
            logger.error(f"Invalid app name: {app_name}")
            raise CommandError(f"Invalid app name: {app_name}")

        # Step 1: Load and validate model definitions
        models = self.load_model_definitions(models_definition, models_file)
        try:
            logger.info(f"Validating schema for '{app_name}'...")
            validate_model_schema(models)
            self.stdout.write(self.style.SUCCESS(f"Schema validation passed for '{app_name}'!"))
            logger.info(f"Schema validation passed for '{app_name}'.")
        except ValueError as e:
            logger.error(f"Schema validation failed: {e}")
            raise CommandError(f"Schema validation failed: {e}")

        # Step 2: Check if app exists
        app_path = os.path.join(settings.BASE_DIR, app_name)
        if os.path.exists(app_path):
            if overwrite:
                logger.warning(f"App '{app_name}' already exists. Overwriting as per '--overwrite' flag.")
                self.delete_existing_app(app_path, app_name)
            else:
                logger.error(f"App '{app_name}' already exists. Use '--overwrite' to replace it.")
                raise CommandError(f"App '{app_name}' already exists. Use '--overwrite' to replace it.")

        # Step 3: Create app structure and files
        try:
            self.register_app_in_settings(app_name)
            self.add_middleware_to_settings(app_name)
            self.create_app_files(app_name, app_path)
            # sleep(10)
            self.generate_logger_file(app_path, app_name)
            self.generate_utils_folder(app_path, app_name)
            self.generate_crud_folder(app_path, app_name)
            self.generate_mixins_file(app_path, app_name)
            self.generate_models_file(app_path, models, app_name)
            self.generate_signals_file(app_path, models, app_name)
            self.generate_middleware_file(app_path, app_name)
            self.generate_serializers_file(app_path, models, app_name)
            self.generate_views_file(app_path, models, app_name)
            # self.register_app_in_settings(app_name)
            # self.add_middleware_to_settings(app_name)

            if not skip_urls:
                self.generate_urls_file(app_path, models, app_name)
            self.generate_dynamic_form_builder(app_path, app_name, models)
            if not skip_admin:
                self.generate_admin_file(app_path, models, app_name)
            if not skip_tests:
                self.generate_tests_file(app_path, models, app_name)
            self.generate_commands_file(app_path)
            self.create_migrations(app_name)

            self.stdout.write(self.style.SUCCESS(f"Application '{app_name}' created successfully."))
            logger.info(f"Application '{app_name}' created successfully.")
        except CommandError as ce:
            logger.error(f"CommandError: {ce}")
            raise ce
        except Exception as e:
            logger.exception(f"An unexpected error occurred: {e}")
            raise CommandError(f"An unexpected error occurred: {e}")

    def load_model_definitions(self, models_definition, models_file):
        """
        Load model definitions from either a string or a file, and validate the schema.
        """
        if models_definition:
            try:
                models = json.loads(models_definition)
                logger.debug("Loaded model definitions from --models argument.")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON for models: {e}")
                raise CommandError(f"Invalid JSON for models: {e}")
        elif models_file:
            try:
                with open(models_file, 'r') as file:
                    models = json.load(file)
                logger.debug(f"Loaded model definitions from file '{models_file}'.")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"Error reading models file '{models_file}': {e}")
                raise CommandError(f"Error reading models file '{models_file}': {e}")
        else:
            logger.error("No model definitions provided. Use --models or --models-file.")
            raise CommandError("You must provide model definitions using --models or --models-file.")

        # Validate the schema
        try:
            validate_model_schema(models)
            self.stdout.write(self.style.SUCCESS("Model schema validation passed!"))
            logger.info("Model schema validation passed.")
        except ValueError as e:
            logger.error(f"Schema validation error: {e}")
            raise CommandError(f"Schema validation error: {e}")

        return models

    def create_app_files(self, app_name, app_path):
        """
        Create basic files for the Django app with advanced configuration in apps.py.
        """
        logger.info(f"Creating app directory at '{app_path}'...")
        os.makedirs(os.path.join(app_path, 'migrations'), exist_ok=True)
        open(os.path.join(app_path, '__init__.py'), 'w').close()
        open(os.path.join(app_path, 'migrations', '__init__.py'), 'w').close()

        # Create the management/commands directory structure
        management_commands_path = os.path.join(app_path, 'management', 'commands')
        os.makedirs(management_commands_path, exist_ok=True)
        open(os.path.join(app_path, 'management', '__init__.py'), 'w').close()
        open(os.path.join(management_commands_path, '__init__.py'), 'w').close()

        # Create apps.py
        apps_py_content = (
            "from django.apps import AppConfig\n\n"
            f"class {app_name.capitalize()}Config(AppConfig):\n"
            f"    default_auto_field = 'django.db.models.BigAutoField'\n"
            f"    name = '{app_name}'\n\n"
            f"    def ready(self):\n"
            f"        # Custom initialization logic for {app_name}\n"
            f"        import {app_name}.signals\n"
            f"        print('App {app_name} is ready!')\n"
        )
        with open(os.path.join(app_path, 'apps.py'), 'w') as f:
            f.write(apps_py_content)
        logger.debug("Created 'apps.py'.")

    def delete_existing_app(self, app_path, app_name):
        """
        Delete an existing app's directory and cleanup related configurations.
        """
        logger.info(f"Deleting existing app directory at '{app_path}'...")
        try:
            # Remove the app directory
            subprocess.run(['rm', '-rf', app_path], check=True)
            logger.info(f"App directory '{app_path}' deleted successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to delete app directory '{app_path}': {e}")
            raise CommandError(f"Failed to delete app directory '{app_path}': {e}")

        # Remove from INSTALLED_APPS and CUSTOM_APPS
        self.remove_app_from_settings(app_name)

    def remove_app_from_settings(self, app_name):
        """
        Remove the app from CUSTOM_APPS and INSTALLED_APPS in settings.py.
        """
        settings_file_path = self.get_settings_file_path()
        if not os.path.exists(settings_file_path):
            logger.error("Could not find settings.py to remove the app.")
            raise CommandError("Could not find settings.py to remove the app.")

        with open(settings_file_path, "r") as f:
            settings_content = f.read()

        # Remove from CUSTOM_APPS
        if f"'{app_name}'" in settings_content.split("CUSTOM_APPS = [")[1].split("]")[0]:
            updated_custom_apps = settings_content.split("CUSTOM_APPS = [")[0] + "CUSTOM_APPS = [\n    " + \
                                  ',\n    '.join(
                                      [app for app in settings_content.split("CUSTOM_APPS = [")[1].split("]")[0].split(",\n    ") if app.strip().strip("'") != app_name]
                                  ) + "\n]\n" + settings_content.split("CUSTOM_APPS = [")[1].split("]")[1]
            settings_content = updated_custom_apps
            logger.debug(f"Removed '{app_name}' from CUSTOM_APPS.")
        else:
            logger.warning(f"App '{app_name}' was not found in CUSTOM_APPS.")

        # Remove from INSTALLED_APPS if present
        if f"'{app_name}'" in settings_content.split("INSTALLED_APPS")[-1]:
            # Use AST to safely remove the app from INSTALLED_APPS
            tree = ast.parse(settings_content)
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if getattr(target, 'id', None) == 'INSTALLED_APPS':
                            if isinstance(node.value, ast.List):
                                node.value.elts = [elt for elt in node.value.elts if elt.value != app_name]
                                break
            # Write back the modified settings.py
            with open(settings_file_path, 'w') as f:
                f.write(ast.unparse(tree))
            logger.debug(f"Removed '{app_name}' from INSTALLED_APPS.")
        else:
            logger.warning(f"App '{app_name}' was not found in INSTALLED_APPS.")

    def get_settings_file_path(self):
        """
        Determine the path to the project's settings.py file.
        Adjust this method based on your project structure.
        """
        # Example assumes settings.py is in 'scohaz_platform/settings/settings.py'
        settings_file_path = os.path.join(settings.BASE_DIR, "scohaz_platform", "settings", "settings.py")
        if not os.path.exists(settings_file_path):
            logger.error(f"Settings file not found at '{settings_file_path}'.")
            raise CommandError(f"Settings file not found at '{settings_file_path}'.")
        return settings_file_path

    def generate_models_file(self, app_path, models, app_name):
        """
        Generate models.py with dynamic model definitions, validation rules, and condition logic.
        Ensures that validation is integrated dynamically using the ValidationRule model and other enhancements.
        """
        logger.info("Generating 'models.py' with dynamic model definitions...")
        # Start adding necessary imports
        models_code = "from django.db import models\n"
        models_code += "from django.contrib.auth.models import Group\n"
        models_code += "from django.db.models.signals import post_save\n"
        models_code += "from django.dispatch import receiver\n"
        models_code += f"from .mixins import ModelCommonMixin\n\n"  # Include ModelCommonMixin

        # Add IntegrationConfig model for API integrations
        models_code += """
class IntegrationConfig(models.Model):
    name = models.CharField(max_length=255)
    base_url = models.URLField()
    method = models.CharField(
        max_length=10,
        choices=[('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('DELETE', 'DELETE')]
    )
    headers = models.JSONField(blank=True, null=True)
    body = models.JSONField(blank=True, null=True)
    timeout = models.IntegerField(default=30)

    class Meta:
        verbose_name = 'Integration Config'
        verbose_name_plural = 'Integration Configs'

    def __str__(self):
        return self.name

"""
        # Add ValidationRule model for dynamic validation rules
        models_code += f"""
class ValidationRule(models.Model):
    \"\"\"
    Represents a dynamic validation rule for a specific field in a specific model.
    Now with support for nested condition logic in a JSON expression.
    \"\"\"
    model_name = models.CharField(max_length=100)
    field_name = models.CharField(max_length=100)

    VALIDATOR_TYPES = [
        ('regex', 'Regex Validation'),
        ('function', 'Function Validation'),
        ('condition', 'Conditional Validation'),
    ]
    validator_type = models.CharField(max_length=50, choices=VALIDATOR_TYPES)

    regex_pattern = models.CharField(max_length=255, blank=True, null=True)
    function_name = models.CharField(max_length=255, blank=True, null=True)
    function_params = models.JSONField(blank=True, null=True)

    # New: a JSON field for storing the complex nested expression
    # e.g., `[ {{ "field": "salary", "operation": "=", "value": {{"field": "base_salary", "operation": "+", "value": {{"field": "bonus"}} }} }}]`
    condition_logic = models.JSONField(blank=True, null=True)

    user_roles = models.ManyToManyField(
        Group, blank=True, related_name='{app_name}_validation_rule_user_roles',
        help_text="Only these groups can edit this field."
    )

    environment = models.CharField(max_length=50, blank=True, null=True)

    # **Dynamic error message**: Displayed when this rule fails
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Custom error message shown if this rule fails. "
                  "If empty, a default message is used."
    )

    def __str__(self):
        return f"{{self.model_name}}.{{self.field_name}} - {{self.validator_type}}"
"""

        # Iterate over models to generate model classes
        for model in models:
            model_name = model["name"]
            models_code += f"\nclass {model_name}(ModelCommonMixin, models.Model):\n"

            # Add fields to the model
            for field in model["fields"]:
                field_name = field["name"]
                field_type = field["type"]
                options = field.get("options", "")
                related_model = field.get("related_model", "")
                lookup = field.get("_lookup", "")

                # Handle static choices
                if "choices" in field:
                    choices = field["choices"]
                    choices_name = f"{field_name.upper()}_CHOICES"
                    models_code += f"    {choices_name} = {choices}\n"

                # Handle dynamic choices using ForeignKey if _lookup is specified
                if "_lookup" in field:
                    models_code += (
                        f"    {field_name} = models.ForeignKey(\n"
                        f"        to='lookup.Lookup',\n"
                        f"        on_delete=models.CASCADE,\n"
                        f"        limit_choices_to={{'parent_lookup__code': '{lookup}'}}\n"
                        f"    )\n"
                    )
                elif field_type in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
                    related_name = f"{app_name.lower()}_{model_name.lower()}_{field_name}_set"
                    models_code += f"    {field_name} = models.{field_type}('{related_model}', related_name='{related_name}', {options})\n"
                else:
                    if "choices" in field:
                        models_code += f"    {field_name} = models.{field_type}({options}, choices={choices_name})\n"
                    else:
                        models_code += f"    {field_name} = models.{field_type}({options})\n"

            # Add Meta class if provided
            meta = model.get("meta", {})
            if meta:
                models_code += "    class Meta:\n"
                for key, value in meta.items():
                    if isinstance(value, str) and not value.startswith("[") and not value.startswith("'"):
                        value = f"'{value}'"
                    models_code += f"        {key} = {value}\n"

            models_code += "\n"

        # Add dynamic signals for IntegrationConfig
        models_code += """
@receiver(post_save, sender=IntegrationConfig)
def handle_integration_post_save(sender, instance, created, **kwargs):
    if created:
        print(f"IntegrationConfig created: {instance.name}")
    else:
        print(f"IntegrationConfig updated: {instance.name}")
"""

        # Write the models to the models.py file
        with open(os.path.join(app_path, "models.py"), "w") as f:
            f.write(models_code)
        logger.debug("Generated 'models.py'.")

    def generate_serializers_file(self, app_path, models, app_name):
        """
        Generate serializers.py with ModelSerializer for each model, including IntegrationConfig and ValidationRule.
        """
        logger.info("Generating 'serializers.py'...")
        # Base imports for serializers file
        code = (
            "from rest_framework import serializers\n"
            f"from {app_name}.models import IntegrationConfig, ValidationRule, {', '.join(model['name'] for model in models)}\n\n"
        )

        # Add IntegrationConfig serializer
        code += """
class IntegrationConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationConfig
        fields = '__all__'

"""

        # Add ValidationRule serializer
        code += """
class ValidationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidationRule
        fields = '__all__'

"""

        # Add serializers for dynamically generated models
        for model in models:
            model_name = model["name"]
            code += (
                f"class {model_name}Serializer(serializers.ModelSerializer):\n"
                f"    class Meta:\n"
                f"        model = {model_name}\n"
                f"        fields = '__all__'\n\n"
            )

        # Write the serializers.py file
        with open(os.path.join(app_path, 'serializers.py'), 'w') as f:
            f.write(code)
        logger.debug("Generated 'serializers.py'.")

    def generate_views_file(self, app_path, models, app_name):
        """
        Generate views.py with DRF ViewSets, applying conditional logic.
        """
        logger.info("Generating 'views.py'...")
        # Import base modules
        imports = (
            f"from rest_framework import viewsets, status\n"
            f"from rest_framework.decorators import action\n"
            f"from rest_framework.response import Response\n"
            f"from {app_name}.serializers import IntegrationConfigSerializer, ValidationRuleSerializer, {', '.join(model['name']+'Serializer' for model in models)}\n"
            f"from {app_name}.models import IntegrationConfig, ValidationRule, {', '.join(model['name'] for model in models)}\n"
            # f"from {app_name}.serializers import IntegrationConfigSerializer, ValidationRuleSerializer, {{', '.join(f'{{model['name']}}Serializer' for model in models)}}\n"
            f"from {app_name}.utils.api import make_api_call\n\n"
        )

        # Start views file content
        views_code = imports

        # IntegrationConfig ViewSet
        views_code += """
class IntegrationConfigViewSet(viewsets.ModelViewSet):
    queryset = IntegrationConfig.objects.all()
    serializer_class = IntegrationConfigSerializer

    @action(detail=True, methods=['post'], url_path='trigger')
    def trigger_integration(self, request, pk=None):
        integration = self.get_object()
        response = make_api_call(
            base_url=integration.base_url,
            method=integration.method,
            headers=integration.headers,
            body=integration.body,
            timeout=integration.timeout,
        )
        if "error" in response:
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        return Response(response, status=status.HTTP_200_OK)

"""

        # ValidationRule ViewSet
        views_code += """
class ValidationRuleViewSet(viewsets.ModelViewSet):
    queryset = ValidationRule.objects.all()
    serializer_class = ValidationRuleSerializer

"""

        # Dynamic ViewSets for Models
        for model in models:
            model_name = model["name"]
            serializer_name = f"{model_name}Serializer"
            views_code += f"""
class {model_name}ViewSet(viewsets.ModelViewSet):
    queryset = {model_name}.objects.all()
    serializer_class = {serializer_name}

    def list(self, request, *args, **kwargs):
        # Add conditional filtering based on query params
        queryset = self.get_queryset()
        filter_param = request.query_params.get('filter_param')
        if filter_param:
            queryset = queryset.filter(name__icontains=filter_param)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='custom-action')
    def custom_action(self, request):
        # Add custom action logic here
        custom_data = {{'message': f'Custom action triggered for {model_name}'}}
        return Response(custom_data, status=status.HTTP_200_OK)
"""
        # Write the updated views file
        views_file_path = os.path.join(app_path, 'views.py')
        with open(views_file_path, 'w') as f:
            f.write(views_code)
        logger.debug("Generated 'views.py'.")

    def generate_urls_file(self, app_path, models, app_name):
        """
        Generate urls.py with routes for IntegrationConfig, ValidationRule, and dynamically generated models.
        """
        logger.info("Generating 'urls.py'...")
        # Generate view names for dynamic models
        viewset_names = ", ".join(f"{model['name']}ViewSet" for model in models)

        # Base imports for urls file
        imports = (
            f"from django.urls import path, include\n"
            f"from rest_framework.routers import DefaultRouter\n"
            f"from {app_name}.views import IntegrationConfigViewSet, ValidationRuleViewSet, {viewset_names}\n\n"
        )

        # Initialize the router
        router_initialization = "router = DefaultRouter()\n"

        # Register IntegrationConfig and ValidationRule endpoints
        router_registration = (
            "router.register(r'integration-configs', IntegrationConfigViewSet)\n"
            "router.register(r'validation-rules', ValidationRuleViewSet)\n"
        )

        # Register dynamic model endpoints
        for model in models:
            model_name = model["name"]
            route_name = model_name.lower()  # Use lowercase model name for routes
            router_registration += f"router.register(r'{route_name}', {model_name}ViewSet)\n"

        # URL patterns
        url_patterns = "\nurlpatterns = [\n    path('', include(router.urls)),\n]\n"

        # Combine all parts into the complete code
        urls_code = imports + router_initialization + router_registration + url_patterns

        # Write the urls.py file
        with open(os.path.join(app_path, 'urls.py'), 'w') as f:
            f.write(urls_code)
        logger.debug("Generated 'urls.py'.")

    def generate_logger_file(self, app_path, app_name):
        """
        Generate logger.py for specific app.
        """
        logger.info("Generating 'logger.py'...")

        logger_code = f"""
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG for detailed logs; adjust as needed
handler = logging.StreamHandler()  # You can configure this to log to a file or other handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
"""

        # Write the urls.py file
        with open(os.path.join(app_path, 'logger.py'), 'w') as f:
            f.write(logger_code)
        logger.debug("Generated 'logger.py'.")


    def generate_mixins_file(self, app_path, app_name):
        """
        Generate mixins.py with dynamic validation logic using VALIDATOR_REGISTRY and condition evaluation.
        Ensures that validation rules for user roles, condition logic, and dynamic validation are applied.
        Follows the 'code style' with full comments and scalability.
        """
        logger.info("Generating 'mixins.py' with dynamic validation logic...")
        mixin_code = f"""from {app_name}.forms import DynamicFormBuilder
from {app_name}.crud.managers import user_can
import json
from {app_name}.utils.custom_validation import VALIDATOR_REGISTRY
from {app_name}.utils.condition_evaluator import ConditionEvaluator
from datetime import datetime
from {app_name}.middleware import get_current_user
from {app_name}.logger import logger
from django.db import models
from django.core.exceptions import ValidationError
from django.apps import apps

"""
        # dynamic validation mixin
        mixin_code += f"""

class DynamicAdminMixin:
    context_name = "admin"

    # ---------------
    # PERMISSION CHECKS
    # ---------------
    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        object_id = obj.pk if obj else None
        return user_can(request.user, "read", self.model, self.context_name, object_id)

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return user_can(request.user, "create", self.model, self.context_name)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        object_id = obj.pk if obj else None
        return user_can(request.user, "update", self.model, self.context_name, object_id)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        object_id = obj.pk if obj else None
        return user_can(request.user, "delete", self.model, self.context_name, object_id)

    # ---------------
    # DYNAMIC FORM
    # ---------------
    def get_form(self, request, obj=None, **kwargs):
        \"\"\"Return a dynamically built form class. Example uses DynamicFormBuilder.\"\"\"
        class CustomDynamicForm(DynamicFormBuilder):
            class Meta:
                model = self.model
                fields = "__all__"

            def __init__(self_inner, *args, **inner_kwargs):
                inner_kwargs.setdefault('user', request.user)
                super().__init__(*args, **inner_kwargs)

        return CustomDynamicForm

    # ---------------
    # SAVE MODEL
    # ---------------
    def save_model(self, request, obj, form, change):
        \"\"\"
        Override to set created_by/updated_by and call obj.full_clean().
        \"\"\"
        obj.set_validation_user(request.user)  # so the model can see the user, if needed

        if not obj.created_by:
            obj.created_by = request.user
        obj.updated_by = request.user

        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            # Force the model's validation
            x = obj.full_clean()  # calls ModelCommonMixin.clean()
            super().save_model(request, obj, form, change)
        except DjangoValidationError as e:
            form.add_error(None, e)
            raise e


class ModelCommonMixin(models.Model):
    \"\"\"
    A mixin that adds created_at, updated_at, plus dynamic validation logic in clean().
    \"\"\"

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="{app_name}_created_%(class)s_set"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="{app_name}_updated_%(class)s_set"
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"{{self.__class__.__name__}} (ID: {{self.id}})"

    def clean(self):
        \"\"\"
        The single source of truth for dynamic validation rules.
        Raises ValidationError if any rule fails.
        \"\"\"
        super().clean()

        user = get_current_user()  # or another approach to get the current user
        if not user:
            raise ValidationError("User context is missing.")

        # 1) Grab relevant ValidationRule objects
        ValidationRuleModel = apps.get_model('testcrm7', 'ValidationRule')
        model_name = self.__class__.__name__
        rules = ValidationRuleModel.objects.filter(model_name=model_name)

        # 2) Build record_data for ConditionEvaluator
        record_data = {{}}
        for field in self._meta.fields:
            field_name = field.name
            record_data[field_name] = getattr(self, field_name, None)

        # 3) Loop over rules
        for rule in rules:
            # --- (a) check user_roles ---
            if rule.user_roles.exists():
                user_groups = set(user.groups.all())
                required_roles = set(rule.user_roles.all())

                # If you truly want to BLOCK the user from saving if they lack these roles, you can:
                if not user_groups.intersection(required_roles):
                    # Raise an error if this field requires a certain role
                    raise ValidationError({{
                        rule.field_name: rule.error_message or "You do not have permission to modify this field."
                    }})
                    # Or "skip" the rule if you only want to skip that rule's validation,
                    # but typically you'd raise an error if the user is unauthorized.
            if rule.validator_type == 'regex':
                pass
            elif rule.validator_type == 'condition':
                # --- (b) condition logic (skip or fail) ---
                if rule.condition_logic:
                    cond_eval = ConditionEvaluator(record_data)
                    evaluation_result = cond_eval.evaluate(rule.condition_logic, rule.error_message)
                    if not evaluation_result[1]:
                        # If the condition is not satisfied, do you want to skip this rule
                        # or block saving? Typically "skip" means "don't validate this rule."
                        # So we just continue:
                        raise ValidationError({{evaluation_result[0]["field"]: evaluation_result[0]["error_message"]}})
            elif rule.validator_type == 'function':
                # --- (c) apply the actual validation (regex, function, etc.) ---
                validator = VALIDATOR_REGISTRY[rule.function_name]
                if not validator:
                    raise ValidationError({{
                        "__all__": f"Unknown validation rule type: {{rule.validator_type}}, {{rule.function_name}}"
                    }})

                try:
                    params = self._prepare_validator_params(rule)
                    field_value = getattr(self, rule.field_name, None)

                    # If your validator fails, it should raise ValidationError itself
                    validator(
                        field_value,
                        rule,
                        **params,
                    )
                except ValidationError as ve:
                    # re-raise so admin shows it near `rule.field_name`
                    raise ValidationError({{rule.field_name: ve.messages}})
                except Exception as e:
                    raise ValidationError({{rule.field_name: str(e)}})

    def _prepare_validator_params(self, rule):
        \"\"\"Helper to parse rule.params or validator_type to pass to validator.\"\"\"
        rule_params = getattr(rule, 'function_params', {{}}) or {{}}
        validator_type = rule.validator_type

        if validator_type == 'max_length':
            return [rule_params.get('max_length')]
        elif validator_type == 'regex':
            return [rule_params.get('pattern')]
        elif validator_type == 'custom':
            return [rule_params.get('function_path')]
        elif validator_type == 'choice':
            return [rule_params.get('choices')]
        return rule_params

    def set_validation_user(self, user):
        \"\"\"If needed, store the user for use in validations.\"\"\"
        setattr(self, '_validation_user', user)
"""
        # Write the mixins.py file
        with open(os.path.join(app_path, 'mixins.py'), 'w') as f:
            f.write(mixin_code)
        logger.debug("Generated 'mixins.py'.")

    def generate_admin_file(self, app_path, models, app_name):
        """
        Generate admin.py with dynamic registration and configuration,
        including the handling of common fields like created_by and updated_by.
        """
        logger.info("Generating 'admin.py' with dynamic registrations...")
        admin_code = (
            "from django.contrib import admin\n"
            f"from {app_name}.models import *\n"
            f"from {app_name}.mixins import DynamicAdminMixin\n\n"
        )

        # Register the IntegrationConfig model with dynamic admin configuration
        admin_code += """
@admin.register(IntegrationConfig)
class IntegrationConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_url', 'method')
    search_fields = ('name', 'base_url')
"""

        # Register the ValidationRule model with dynamic admin configuration
        admin_code += """
@admin.register(ValidationRule)
class ValidationRuleAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'field_name', 'validator_type', 'regex_pattern', 'function_name')
    search_fields = ('model_name', 'field_name', 'validator_type')
"""

        for model in models:
            model_name = model["name"]

            # Dynamically configure admin class
            admin_class_name = f"{model_name}Admin"
            list_display = [field["name"] for field in model["fields"]]
            search_fields = [field["name"] for field in model["fields"] if field["type"] == "CharField"]
            list_filter = [
                field["name"]
                for field in model["fields"]
                if field["type"] in ["BooleanField", "DateField", "DateTimeField"]
            ]

            admin_code += f"""
class {admin_class_name}(DynamicAdminMixin, admin.ModelAdmin):
    list_display = {list_display}
    search_fields = {search_fields}
    list_filter = {list_filter}

admin.site.register({model_name}, {admin_class_name})
"""

        # Write the admin.py file
        admin_file_path = os.path.join(app_path, 'admin.py')
        with open(admin_file_path, 'w') as f:
            f.write(admin_code)
        logger.debug("Generated 'admin.py'.")

    def generate_tests_file(self, app_path, models, app_name):
        """
        Generate tests.py with comprehensive unit tests for models, API integrations, and endpoints.
        """
        logger.info("Generating 'tests.py' with comprehensive unit tests...")
        # Collect all models referenced in the current application and externally
        local_models = {model["name"] for model in models}
        external_models = set()

        # Gather external models from fields and relationships
        for model in models:
            for field in model.get("fields", []):
                if field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"] and "." in field.get("related_model", ""):
                    external_models.add(field["related_model"])
            for relation in model.get("relationships", []):
                if "." in relation.get("related_model", ""):
                    external_models.add(relation["related_model"])

        # Generate imports for local models
        model_imports = ", ".join(sorted(local_models))
        imports = f"from {app_name}.models import {model_imports}, IntegrationConfig, ValidationRule\n"

        # Generate imports for external models
        for external_model in external_models:
            external_app, external_model_name = external_model.split(".")
            imports += f"from {external_app}.models import {external_model_name}\n"

        # Base imports for the test file
        code = (
            "from django.test import TestCase\n"
            "from rest_framework.test import APIClient\n"
            "from rest_framework import status\n"
            f"{imports}\n"
            f"from {app_name}.utils.api import make_api_call\n\n"
        )

        # Add a Base Test Class for Common Setup
        code += """
class BaseTestSetup(TestCase):
    def setUp(self):
        self.valid_config = IntegrationConfig.objects.create(
            name="Test API",
            base_url="https://api.example.com",
            method="GET",
            headers={"Authorization": "Bearer testtoken"},
            timeout=10
        )
        self.client = APIClient()
"""

        # Add tests for IntegrationConfig
        code += """
class IntegrationConfigTests(BaseTestSetup):
    def test_integration_config_creation(self):
        self.assertEqual(self.valid_config.name, "Test API")
        self.assertEqual(self.valid_config.base_url, "https://api.example.com")
        self.assertEqual(self.valid_config.method, "GET")
        self.assertEqual(self.valid_config.headers["Authorization"], "Bearer testtoken")
        self.assertEqual(self.valid_config.timeout, 10)

    def test_make_api_call_success(self):
        response = make_api_call(
            base_url="https://jsonplaceholder.typicode.com/posts",
            method="GET"
        )
        self.assertTrue(isinstance(response, list))  # Assuming the API returns a list

    def test_make_api_call_failure(self):
        response = make_api_call(
            base_url="https://invalid.url",
            method="GET"
        )
        self.assertIn("error", response)
"""

        # Add tests for ValidationRule model
        code += """
class ValidationRuleTests(BaseTestSetup):
    def setUp(self):
        super().setUp()
        self.validation_rule = ValidationRule.objects.create(
            model_name="ExampleModel",
            field_name="status",
            rule_type="regex",
            params={"pattern": "^draft|published$"},
            error_message="Invalid status value."
        )

    def test_validation_rule_creation(self):
        self.assertEqual(self.validation_rule.model_name, "ExampleModel")
        self.assertEqual(self.validation_rule.field_name, "status")
        self.assertEqual(self.validation_rule.rule_type, "regex")
        self.assertEqual(self.validation_rule.params["pattern"], "^draft|published$")
        self.assertEqual(self.validation_rule.error_message, "Invalid status value.")
"""

        # Add tests for models and endpoints dynamically
        for model in models:
            model_name = model["name"]
            api_endpoint = model_name.lower()

            # Model tests
            code += f"""
class {model_name}ModelTests(BaseTestSetup):
    def setUp(self):
        super().setUp()
"""
            relationships = model.get("relationships", [])
            for relation in relationships:
                related_model_name = relation["related_model"].split(".")[-1]
                code += f"        self.{related_model_name.lower()} = {related_model_name}.objects.create()\n"
            for field in model["fields"]:
                if field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"] and "." in field.get("related_model", ""):
                    related_model_name = field["related_model"].split(".")[-1]
                    code += f"        self.{related_model_name.lower()} = {related_model_name}.objects.create()\n"
            if not relationships and not any(field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"] for field in model["fields"]):
                code += "        pass\n"

            code += f"""
    def test_create_{model_name.lower()}(self):
        obj = {model_name}.objects.create(
"""
            # Include fields during creation
            for field in model["fields"]:
                if field["type"] == "CharField":
                    code += f"            {field['name']}='Test String',\n"
                elif field["type"] == "TextField":
                    code += f"            {field['name']}='Test Text',\n"
                elif field["type"] == "BooleanField":
                    code += f"            {field['name']}=True,\n"
                elif field["type"] == "DecimalField":
                    code += f"            {field['name']}=123.45,\n"
                elif field["type"] == "EmailField":
                    code += f"            {field['name']}='test@example.com',\n"
                elif field["type"] == "URLField":
                    code += f"            {field['name']}='https://example.com',\n"
                elif field["type"] == "IntegerField":
                    code += f"            {field['name']}=123,\n"
                elif field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
                    related_model_name = field["related_model"].split(".")[-1]
                    code += f"            {field['name']}=self.{related_model_name.lower()},\n"

            code += f"""        )
        self.assertIsNotNone(obj.id)
        self.assertEqual(str(obj), f"{model_name} object ({{obj.id}})")
"""

            # API tests
            code += f"""
class {model_name}APITests(BaseTestSetup):
    def setUp(self):
        super().setUp()
"""
            for relation in relationships:
                related_model_name = relation["related_model"].split(".")[-1]
                code += f"        self.{related_model_name.lower()} = {related_model_name}.objects.create()\n"

            code += f"""
    def test_get_{api_endpoint}_list(self):
        response = self.client.get(f'/{app_name}/{api_endpoint}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_{api_endpoint}(self):
        data = {{
"""
            for field in model["fields"]:
                if field["type"] == "CharField":
                    code += f"            '{field['name']}': 'Test String',\n"
                elif field["type"] == "TextField":
                    code += f"            '{field['name']}': 'Test Text',\n"
                elif field["type"] == "BooleanField":
                    code += f"            '{field['name']}': True,\n"
                elif field["type"] == "DecimalField":
                    code += f"            '{field['name']}': 123.45,\n"
                elif field["type"] == "EmailField":
                    code += f"            '{field['name']}': 'test@example.com',\n"
                elif field["type"] == "URLField":
                    code += f"            '{field['name']}': 'https://example.com',\n"
                elif field["type"] == "IntegerField":
                    code += f"            '{field['name']}': 123,\n"
                elif field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
                    related_model_name = field["related_model"].split(".")[-1]
                    code += f"            '{field['name']}': self.{related_model_name.lower()}.id,\n"

            code += """        }
        response = self.client.post(f'/{app_name}/{api_endpoint}/', data)
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

    def test_update_{api_endpoint}(self):
        obj = {model_name}.objects.create(
"""
            # Include fields during creation for update test
            for field in model["fields"]:
                if field["type"] == "CharField":
                    code += f"            {field['name']}='Initial String',\n"
                elif field["type"] == "TextField":
                    code += f"            {field['name']}='Initial Text',\n"
                elif field["type"] == "BooleanField":
                    code += f"            {field['name']}=False,\n"
                elif field["type"] == "DecimalField":
                    code += f"            {field['name']}=100.00,\n"
                elif field["type"] == "EmailField":
                    code += f"            {field['name']}='initial@example.com',\n"
                elif field["type"] == "URLField":
                    code += f"            {field['name']}='https://initial.com',\n"
                elif field["type"] == "IntegerField":
                    code += f"            {field['name']}=100,\n"
                elif field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
                    related_model_name = field["related_model"].split(".")[-1]
                    code += f"            {field['name']}=self.{related_model_name.lower()},\n"

            code += f"""        )
        update_data = {{
"""
            for field in model["fields"]:
                if field["type"] == "CharField":
                    code += f"            '{field['name']}': 'Updated String',\n"
                elif field["type"] == "TextField":
                    code += f"            '{field['name']}': 'Updated Text',\n"
                elif field["type"] == "BooleanField":
                    code += f"            '{field['name']}': True,\n"
                elif field["type"] == "DecimalField":
                    code += f"            '{field['name']}': 150.75,\n"
                elif field["type"] == "EmailField":
                    code += f"            '{field['name']}': 'updated@example.com',\n"
                elif field["type"] == "URLField":
                    code += f"            '{field['name']}': 'https://updated.com',\n"
                elif field["type"] == "IntegerField":
                    code += f"            '{field['name']}': 150,\n"
                elif field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
                    related_model_name = field["related_model"].split(".")[-1]
                    code += f"            '{field['name']}': self.{related_model_name.lower()}.id,\n"

            code += f"""        }}
        response = self.client.put(f'/{app_name}/{api_endpoint}/{{obj.id}}/', update_data)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])

    def test_delete_{api_endpoint}(self):
        obj = {model_name}.objects.create(
"""
            # Include fields during creation for delete test
            for field in model["fields"]:
                if field["type"] == "CharField":
                    code += f"            {field['name']}='Delete String',\n"
                elif field["type"] == "TextField":
                    code += f"            {field['name']}='Delete Text',\n"
                elif field["type"] == "BooleanField":
                    code += f"            {field['name']}=False,\n"
                elif field["type"] == "DecimalField":
                    code += f"            {field['name']}=50.00,\n"
                elif field["type"] == "EmailField":
                    code += f"            {field['name']}='delete@example.com',\n"
                elif field["type"] == "URLField":
                    code += f"            {field['name']}='https://delete.com',\n"
                elif field["type"] == "IntegerField":
                    code += f"            {field['name']}=50,\n"
                elif field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
                    related_model_name = field["related_model"].split(".")[-1]
                    code += f"            {field['name']}=self.{related_model_name.lower()},\n"

            code += f"""        )
        response = self.client.delete(f'/{app_name}/{api_endpoint}/{{obj.id}}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
"""

        # Write the tests to the `tests.py` file
        with open(os.path.join(app_path, 'tests.py'), 'w') as f:
            f.write(code)
        logger.debug("Generated 'tests.py'.")

    def generate_commands_file(self, app_path):
        """
        Generate a sample management command for the app.
        """
        logger.info("Generating sample management command 'populate_data.py'...")
        commands_path = os.path.join(app_path, 'management', 'commands')
        command_code = """\
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Populate initial data for the app'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating initial data...')
        # Add your custom logic here
        self.stdout.write(self.style.SUCCESS('Data populated successfully!'))
"""
        with open(os.path.join(commands_path, 'populate_data.py'), 'w') as f:
            f.write(command_code)
        logger.debug("Generated 'populate_data.py'.")

    def register_app_in_settings(self, app_name):
        """
        Add the app to the CUSTOM_APPS in settings.py if not already present.
        """

        from pathlib import Path
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        settings_file_path = os.path.join(BASE_DIR, "scohaz_platform/settings/settings.py")  # Adjust this to your settings file location
        if not os.path.exists(settings_file_path):
            raise CommandError("Could not find settings.py to register the app.")

        # Read the settings content
        with open(settings_file_path, "r") as f:
            settings_content = f.read()

        # Ensure the app_name is not already present in CUSTOM_APPS
        if f"'{app_name}'" not in settings_content:
            # Add the app_name to CUSTOM_APPS
            updated_content = settings_content.replace(
                "CUSTOM_APPS = [",
                f"CUSTOM_APPS = [\n    '{app_name}',"
            )
            try:
                # Write the updated settings file
                with open(settings_file_path, "w") as f:
                    f.write(updated_content)

                # Log the success message
                self.stdout.write(self.style.SUCCESS(f"App '{app_name}' added to CUSTOM_APPS and INSTALLED_APPS."))
            except Exception as e:
                raise CommandError(f"Error updating settings.py: {e}")
        else:
            self.stdout.write(self.style.WARNING(f"App '{app_name}' is already in CUSTOM_APPS."))

        # Check if the app is present in INSTALLED_APPS
        if f"'{app_name}'" not in settings_content.split("INSTALLED_APPS")[-1]:
            # updated_content = settings_content.replace(
            #     "INSTALLED_APPS += CUSTOM_APPS + [",
            #     f"INSTALLED_APPS += CUSTOM_APPS + [\n    '{app_name}',"
            # )
            try:
                # Write the updated settings file again if needed
                # with open(settings_file_path, "w") as f:
                #     f.write(updated_content)

                # Log the success message for INSTALLED_APPS
                self.stdout.write(self.style.SUCCESS(f"App '{app_name}' added to INSTALLED_APPS."))
            except Exception as e:
                raise CommandError(f"Error ensuring app is in INSTALLED_APPS: {e}")
        else:
            self.stdout.write(self.style.WARNING(f"App '{app_name}' is already in INSTALLED_APPS."))


    def add_middleware_to_settings(self, app_name):
        """
        Add the app's middleware to MIDDLEWARE in settings.py.
        """
        from pathlib import Path
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        settings_file_path = os.path.join(BASE_DIR, 'scohaz_platform', 'settings', 'settings.py')

        if not os.path.exists(settings_file_path):
            raise CommandError("Could not find settings.py to register middleware.")

        dynamic_model_middleware = f"    '{app_name}.middleware.DynamicModelMiddleware',\n"
        current_user_middleware = f"    '{app_name}.middleware.CurrentUserMiddleware',\n"

        with open(settings_file_path, "r") as f:
            settings_content = f.readlines()

        # Clean up APPS_CURRENT_USER_MIDDLEWARE
        in_apps_middleware = False
        cleaned_apps_middleware = []
        for line in settings_content:
            if line.strip().startswith("APPS_CURRENT_USER_MIDDLEWARE = ["):
                in_apps_middleware = True
            if in_apps_middleware:
                if dynamic_model_middleware.strip() in line:  # Remove misplaced DynamicModelMiddleware
                    continue
                if line.strip() == "]":
                    in_apps_middleware = False
            cleaned_apps_middleware.append(line)

        # Add CurrentUserMiddleware if not already present
        if current_user_middleware.strip() not in ''.join(cleaned_apps_middleware):
            cleaned_apps_middleware = [
                line if not line.strip().startswith("APPS_CURRENT_USER_MIDDLEWARE = [") else
                f"{line.strip()}\n{current_user_middleware}"
                for line in cleaned_apps_middleware
            ]

        # Clean up MIDDLEWARE
        in_middleware = False
        cleaned_middleware = []
        for line in cleaned_apps_middleware:
            if line.strip().startswith("MIDDLEWARE = ["):
                in_middleware = True
            if in_middleware:
                if current_user_middleware.strip() in line:  # Remove misplaced CurrentUserMiddleware
                    continue
                if line.strip() == "]":
                    in_middleware = False
            cleaned_middleware.append(line)

        # Add DynamicModelMiddleware if not already present
        if dynamic_model_middleware.strip() not in ''.join(cleaned_middleware):
            cleaned_middleware = [
                line if not line.strip().startswith("MIDDLEWARE = [") else
                f"{line.strip()}\n{dynamic_model_middleware}"
                for line in cleaned_middleware
            ]

        # Write back to settings.py
        with open(settings_file_path, "w") as f:
            f.writelines(cleaned_middleware)

        self.stdout.write(self.style.SUCCESS("Settings updated successfully."))


    def generate_dynamic_form_builder(self, app_path, app_name, models):
        """
        Generate the dynamic form builder and integrate it with the validation rules.
        """
        logger.info("Generating 'forms.py' with DynamicFormBuilder...")
        form_builder_code = f"""
from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from {app_name}.logger import logger

# from {app_name}.utils.conditions import ConditionEvaluator
# from {app_name}.utils.validators import VALIDATOR_REGISTRY

class DynamicFormBuilder(forms.ModelForm):
    \"\"\"
    A dynamic form builder class to generate form fields based on the model definition.
    This class expects the Meta class to be defined in its subclasses.
    Handles user-based validation, condition-based validation, and dynamically
    generates form fields for model fields such as ForeignKey, OneToOneField, ManyToManyField, etc.
    \"\"\"

    def __init__(self, *args, **kwargs):
        \"\"\"
        Initialize the form by extracting the user and instance,
        then dynamically set up form fields based on the model's fields.

        Parameters:
        - user (User): User object for role-based validation.
        - instance (ModelInstance): Existing instance of the model (if any) for editing purposes.

        \"\"\"
        # Extract user from kwargs
        self.user = kwargs.pop('user', None)

        # Ensure 'instance' is passed to the superclass without modification
        super().__init__(*args, **kwargs)

        if self.user:
            self.instance.set_validation_user(self.user)
            logger.debug(f"DynamicFormBuilder: Validation user set to {{self.user.username}}")
        else:
            logger.warning("DynamicFormBuilder: No user provided for validation.")

        # Determine the model name from the Meta class
        self.model_name = self.Meta.model.__name__

        # Handle relationships dynamically (ForeignKey, OneToOneField, ManyToManyField)
        self._build_relationship_fields()

        # Generate additional non-relationship fields if necessary
        additional_fields = self.generate_fields()
        for field_name, field in additional_fields.items():
            if field_name not in self.fields:
                self.fields[field_name] = field

    def _build_relationship_fields(self):
        \"\"\"
        Dynamically add fields for relationships such as ForeignKey, OneToOneField, and ManyToManyField.
        \"\"\"
        for field in self.Meta.model._meta.get_fields():
            if field.is_relation and not field.auto_created:
                if field.many_to_one and not isinstance(field, models.ManyToManyField):
                    # Handle ForeignKey or OneToOneField relationships
                    related_model = field.remote_field.model
                    self.fields[field.name] = forms.ModelChoiceField(
                        queryset=related_model.objects.all(),
                        required=not field.blank,
                        label=field.verbose_name,
                        initial=getattr(self.instance, field.name) if self.instance else None
                    )
                elif isinstance(field, models.ManyToManyField):
                    # Handle ManyToManyField relationships
                    related_model = field.remote_field.model
                    self.fields[field.name] = forms.ModelMultipleChoiceField(
                        queryset=related_model.objects.all(),
                        required=not field.blank,
                        label=field.verbose_name,
                        initial=getattr(self.instance, field.name).all() if self.instance else None
                    )

    def generate_fields(self):
        \"\"\"
        Generate form fields based on the model fields dynamically.
        Only handles non-relationship fields to prevent overriding relationship fields.

        Returns:
        - fields (dict): A dictionary of field names and their corresponding form fields.
        \"\"\"
        fields = {{}}
        for field in self.Meta.model._meta.get_fields():
            # Skip auto-created fields and relationship fields (handled separately)
            if field.auto_created or field.is_relation:
                continue

            if field.name == 'id':
                continue  # Skip the 'id' field as it's auto-generated

            # Handle various non-relationship field types
            if isinstance(field, models.CharField):
                fields[field.name] = forms.CharField(
                    label=field.verbose_name,
                    max_length=field.max_length,
                    required=not field.blank,
                    widget=forms.TextInput(attrs={{'placeholder': field.verbose_name}})
                )
            elif isinstance(field, models.TextField):
                fields[field.name] = forms.CharField(
                    label=field.verbose_name,
                    required=not field.blank,
                    widget=forms.Textarea(attrs={{'placeholder': field.verbose_name}})
                )
            elif isinstance(field, models.IntegerField):
                fields[field.name] = forms.IntegerField(
                    label=field.verbose_name,
                    required=not field.blank
                )
            elif isinstance(field, models.BooleanField):
                fields[field.name] = forms.BooleanField(
                    label=field.verbose_name,
                    required=False
                )
            elif isinstance(field, models.DateField):
                fields[field.name] = forms.DateField(
                    label=field.verbose_name,
                    required=not field.blank,
                    widget=forms.DateInput(attrs={{'type': 'date'}})
                )
            elif isinstance(field, models.DateTimeField):
                fields[field.name] = forms.DateTimeField(
                    label=field.verbose_name,
                    required=not field.blank,
                    widget=forms.DateTimeInput(attrs={{'type': 'datetime-local'}})
                )
            elif isinstance(field, models.DecimalField):
                fields[field.name] = forms.DecimalField(
                    label=field.verbose_name,
                    required=not field.blank,
                    max_digits=field.max_digits,
                    decimal_places=field.decimal_places
                )
            elif isinstance(field, models.FloatField):
                fields[field.name] = forms.FloatField(
                    label=field.verbose_name,
                    required=not field.blank
                )
            elif isinstance(field, models.EmailField):
                fields[field.name] = forms.EmailField(
                    label=field.verbose_name,
                    required=not field.blank
                )
            elif isinstance(field, models.URLField):
                fields[field.name] = forms.URLField(
                    label=field.verbose_name,
                    required=not field.blank
                )
            elif isinstance(field, models.SlugField):
                fields[field.name] = forms.SlugField(
                    label=field.verbose_name,
                    required=not field.blank
                )
            # Add more field types as needed
            else:
                # For any unhandled field types, use a generic field or skip
                fields[field.name] = forms.CharField(
                    label=field.verbose_name,
                    required=not field.blank
                )
        return fields
    
    def clean(self):
        \"\"\"
        Override the clean method to incorporate dynamic validation.
        \"\"\"
        # Ensure that 'user' is set for validation
        if self.user:
            self.instance.set_validation_user(self.user)
            logger.debug(f"DynamicFormBuilder: Validation user set to {{self.user.username}}")
        else:
            logger.error("DynamicFormBuilder: No user provided for validation.")
            raise ValidationError("User context is missing.")

        # Call the superclass clean method to perform built-in validations
        cleaned_data = super().clean()

        # The DynamicValidationMixin handles dynamic validation via model's clean method,
        # which is called by full_clean(), so additional validation here may be redundant.

        return cleaned_data
    
"""

        # Write the forms.py file
        with open(os.path.join(app_path, 'forms.py'), 'w') as f:
            f.write(form_builder_code)
        logger.debug("Generated 'forms.py'.")

    def generate_signals_file(self, app_path, models, app_name):
        """
        Generate signals.py to handle dynamic pre-save and post-save hooks for models.
        """
        logger.info("Generating 'signals.py' with dynamic signal handlers...")
        signal_code = (
            f"from django.db.models.signals import pre_save, post_save\n"
            f"from django.dispatch import receiver\n"
            f"from {app_name}.models import {', '.join(model['name'] for model in models)}\n\n"
        )

        # Generate pre-save and post-save hooks for each model
        for model in models:
            model_name = model["name"]

            # Pre-save signal
            signal_code += f"""\
@receiver(pre_save, sender={model_name})
def pre_save_{model_name.lower()}(sender, instance, **kwargs):
    # Add custom pre-save logic here
    print(f'Pre-save hook triggered for {model_name}: {{instance}}')

"""

            # Post-save signal
            signal_code += f"""\
@receiver(post_save, sender={model_name})
def post_save_{model_name.lower()}(sender, instance, created, **kwargs):
    if created:
        print(f'{model_name} instance created: {{instance}}')
    else:
        print(f'{model_name} instance updated: {{instance}}')

"""

        # Write the signals file
        signals_file_path = os.path.join(app_path, 'signals.py')
        with open(signals_file_path, 'w') as f:
            f.write(signal_code)
        logger.debug("Generated 'signals.py'.")

    def generate_utils_folder(self, app_path, app_name):
        """
        Generate a utils folder with modular validation, condition evaluation, and API call logic.
        Automatically adapts to the app context.
        """
        logger.info("Generating 'utils' folder with validators, API calls, and condition evaluators...")
        utils_folder_path = os.path.join(app_path, 'utils')
        os.makedirs(utils_folder_path, exist_ok=True)

        # Generate __init__.py for the utils package
        with open(os.path.join(utils_folder_path, '__init__.py'), 'w') as init_file:
            init_file.write("# utils package\n")
        logger.debug("Created '__init__.py' in 'utils'.")

        # Generate validators.py with dynamic validators and support for multiple validation types
        custom_validation_code = f"""\
import re
from datetime import datetime
from django.core.exceptions import ValidationError


# Registry to map rule types to validation functions
VALIDATOR_REGISTRY = {{}}

# Decorator to register a validation function in the registry
def register_validator(rule_type):
    def decorator(func):
        VALIDATOR_REGISTRY[rule_type] = func
        return func
    return decorator

def show_error_message(value, instance):
    if instance.error_message:
        raise ValueError(f"{{instance.error_message}}")
    else:
        raise ValueError(f"Value '{{value}}' does not match pattern: {{instance.function_params}}")


# Base Validation Utilities
@register_validator('regex')
def validate_regex(value, pattern, error_message="Invalid format", **kwargs):
    if not re.match(pattern, str(value)):
        raise ValidationError(error_message)

@register_validator('min_length')
def validate_min_length(value, min_length, error_message="Value is too short", **kwargs):
    if len(str(value)) < min_length:
        raise ValidationError(error_message)

@register_validator('max_length')
def validate_max_length(value, max_length, error_message="Value is too long", **kwargs):
    if len(str(value)) > max_length:
        raise ValidationError(error_message)

@register_validator('range')
def validate_range(value, min_value=None, max_value=None, error_message="Value out of range", **kwargs):
    if min_value is not None and value < min_value:
        raise ValidationError(f"Value must be greater than or equal to {{min_value}}")
    if max_value is not None and value > max_value:
        raise ValidationError(f"Value must be less than or equal to {{max_value}}")

@register_validator('active_customer')
def validate_active_customer(value, instance=None, error_message="The customer must be active.", **kwargs):
    if not value.is_active:
        raise ValidationError(error_message)

@register_validator('max_payment')
def validate_max_payment(value, instance=None, error_message="Total payment exceeds invoice amount.", **kwargs):
    if instance:
        total_payments = sum(payment.amount for payment in instance.invoice.payment_set.all())
        if total_payments + value > instance.invoice.total:
            raise ValidationError(error_message)

@register_validator('date_format')
def validate_date_format(value, date_format, error_message="Invalid date format", **kwargs):
    try:
        datetime.strptime(value, date_format)
    except ValueError:
        raise ValidationError(error_message)

@register_validator('custom')
def validate_custom_function(value, function_path, error_message="Custom validation failed", instance=None, user=None, **kwargs):
    module_path, func_name = function_path.rsplit('.', 1)
    try:
        module = __import__(module_path, fromlist=[func_name])
        func = getattr(module, func_name)
        func(value, instance=instance, user=user)
    except Exception as e:
        raise ValidationError(f"{{error_message}}: {{str(e)}}")

@register_validator('choice')
def validate_choice(value, choices, error_message="Invalid choice", **kwargs):
    if value not in choices:
        raise ValidationError(error_message)

@register_validator('length')
def length_validator(value, instance=None, min_length=None, max_length=None):
    if len(value) < min_length or len(value) > max_length:
        show_error_message(value, instance)
"""

        with open(os.path.join(utils_folder_path, 'custom_validation.py'), 'w') as validators_file:
            validators_file.write(custom_validation_code)
        logger.debug("Generated 'custom_validation.py'.")

        # Generate api.py for API call logic
        api_code = """\
import requests
from requests.exceptions import RequestException

def make_api_call(base_url, method, headers=None, body=None, timeout=30):
    try:
        response = requests.request(
            method=method,
            url=base_url,
            headers=headers,
            json=body,
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        return {"error": str(e)}
"""

        with open(os.path.join(utils_folder_path, 'api.py'), 'w') as api_file:
            api_file.write(api_code)
        logger.debug("Generated 'api.py'.")

        # Generate condition_evaluator.py with dynamic condition evaluator logic
        condition_evaluator_code = f"""\
import re
from typing import Any, Dict, List, Union
from urllib import request

from django.apps import apps


class ConditionEvaluator:
    \"\"\"
    A reusable evaluator for nested condition logic:
    - 'and' / 'or' operations with multiple sub-conditions
    - Comparisons: '=', '!=', '>', '>=', '<', '<=', 'contains', 'matches', etc.
    - Arithmetic references: {{"field": "base_salary", "operation": "+", "value": {{"field": "bonus"}}}}
    \"\"\"
    def __init__(self, record_data: Dict[str, Any]):
        \"\"\"
        :param record_data: The data dictionary of the model fields, e.g. self.__dict__.
        \"\"\"
        self.record_data = record_data

    def evaluate(self, expression: Any) -> bool:
        \"\"\"
        Main entry point to evaluate an expression that can be:
          - A list => implicit AND of multiple sub-expressions
          - A dict => a single condition or a logical group with 'operation' and 'conditions'
        \"\"\"
        if isinstance(expression, list):
            # If you have a single item with {{'operation': 'or', 'conditions': [...]}} use special logic
            if len(expression) == 1 and isinstance(expression[0], dict) and "operation" in expression[0]:
                return self._evaluate_logical_group(expression[0])
            else:
                # Implicit AND for each item in the list
                return all(self.evaluate(item) for item in expression)

        if isinstance(expression, dict):
            # Possibly a logical group: {{"operation": "or"/"and", "conditions": [...]}}
            if "operation" in expression and "conditions" in expression:
                return self._evaluate_logical_group(expression)

            # A single condition: {{"field": "...", "operation": "=", "value": ...}}
            if "field" in expression and "operation" in expression and "value" in expression:
                return self._evaluate_simple_condition(expression)

            # Possibly an arithmetic expression: {{"field": "...", "operation": "+", "value": {{...}}}}
            if "operation" in expression and expression["operation"] in ["+", "-", "*", "**", "/"]:
                # By itself, arithmetic might not be a boolean check, so typically you'd embed it in a comparison.
                # We'll treat raw arithmetic as "True" if it doesn't error out,
                # or you might raise an error if you don't allow top-level arithmetic.
                _ = self._evaluate_arithmetic(expression)
                return True

        return False

    def _evaluate_logical_group(self, expr: Dict[str, Any]) -> bool:
        \"\"\"
        Evaluate a logical group of conditions.

        Logical group example:
        {{
            "operation": "or",
            "conditions": [
                {{"field": "first_name", "operation": "=", "value": "Hisham"}},
                {{"field": "last_name", "operation": "startswith", "value": "Nasr"}}
            ]
        }}

        Single condition example:
        {{
            "field": "first_name",
            "operation": "contains",
            "value": "nasr"
        }}
        \"\"\"
        op = expr.get("operation", "").lower()

        # If 'conditions' is missing, treat the expression as a single condition
        if "conditions" not in expr:
            return self._evaluate_simple_condition(expr)

        # Retrieve conditions for logical group evaluation
        conditions = expr["conditions"]

        if op == "and":
            return all(self.evaluate(c) for c in conditions)
        elif op == "or":
            return any(self.evaluate(c) for c in conditions)
        # You can extend with "not", "xor", etc. if needed
        return False

    def _evaluate_simple_condition(self, expr: Dict[str, Any]) -> bool:
        field_name = expr["field"]
        operation = expr["operation"]
        value_expr = expr["value"]

        left_value = self._get_value(field_name)
        right_value = self._resolve_value_expr(value_expr)

        return self._compare_values(left_value, operation, right_value)
"""

        with open(os.path.join(utils_folder_path, 'condition_evaluator.py'), 'w') as condition_evaluator_file:
            condition_evaluator_file.write(condition_evaluator_code)
        logger.debug("Generated 'condition_evaluator.py'.")

    def generate_crud_folder(self, app_path, app_name):
        """
        Generate a crud folder with modular permissions.
        Automatically adapts to the app context.
        """
        logger.info("Generating 'crud' folder for permissions")
        crud_folder_path = os.path.join(app_path, 'crud')
        os.makedirs(crud_folder_path, exist_ok=True)

        # Generate __init__.py for the utils package
        with open(os.path.join(crud_folder_path, '__init__.py'), 'w') as init_file:
            init_file.write("# crud package\n")
        logger.debug("Created '__init__.py' in 'crud'.")

        # Generate mangers.py.py with dynamic permissions and support for multiple types
        managers_code = f"""
# {app_name}/crud/managers.py

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from authentication.models import CRUDPermission

def user_can(user, action, model_class, context, object_id=None):
    \"\"\"
    :param user: the user instance
    :param action: one of "create", "read", "update", "delete"
    :param model_class: e.g. BlogPost
    :param context: e.g. "api", "admin", "form_view"
    :param object_id: optional if you are checking at object level
    :return: True/False
    \"\"\"
    if not user.is_authenticated:
        return False

    # We get all groups for the user
    groups = user.groups.all()  # many-to-many

    # Then for each group, we see if there's a matching permission
    content_type = ContentType.objects.get_for_model(model_class)

    # Optional: handle object-level permissions if needed
    # If object_id is set, you look for CRUDPermission with matching object_id
    # Otherwise, you look for CRUDPermission without object_id
    query = CRUDPermission.objects.filter(
        group__in=groups,
        content_type=content_type,
        context__icontains=context,
    )

    if object_id:
        query = query.filter(Q(object_id=object_id) | Q(object_id__isnull=True))
    else:
        query = query.filter(object_id__isnull=True)

    # If no record found, user doesn't have permission
    if not query.exists():
        return False

    # If found, check the boolean for create/read/update/delete
    for perm in query:
        if action == "create" and perm.can_create:
            return True
        elif action == "read" and perm.can_read:
            return True
        elif action == "update" and perm.can_update:
            return True
        elif action == "delete" and perm.can_delete:
            return True

    return False
"""

        with open(os.path.join(crud_folder_path, 'managers.py'), 'w') as managers_file:
            managers_file.write(managers_code)
        logger.debug("Generated 'managers.py'.")

    def generate_middleware_file(self, app_path, app_name):
        """
        Generate middleware.py to handle dynamic logic for requests and responses.
        """
        middleware_code = f"""
from django.utils.deprecation import MiddlewareMixin
# from {app_name}.models import IntegrationConfig
# In your utils or middleware.py file
import threading

        
def get_current_user():
    \"\"\"
    Retrieve the current user from thread-local storage.
    \"\"\"
    return getattr(thread_local, 'current_user', None)

# Thread-local storage to capture the current user
thread_local = threading.local()
class CurrentUserMiddleware(MiddlewareMixin):
    \"\"\"
    Middleware to store the current user in thread-local storage.
    \"\"\"
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        thread_local.current_user = request.user
        print(f"User in middleware: {{request.user.username}}")  # Debugging line
        response = self.get_response(request)
        return response

        

class DynamicModelMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Add logic to handle requests dynamically
        if request.path.startswith('/{app_name}/'):
            print(f"Processing request for {app_name}: {{request.path}}")

    def process_response(self, request, response):
        # Add logic to handle responses dynamically
        if request.path.startswith('/{app_name}/'):
            print(f"Processing response for {app_name}: {{response.status_code}}")
        return response
"""
        middleware_file_path = os.path.join(app_path, 'middleware.py')
        with open(middleware_file_path, 'w') as f:
            f.write(middleware_code)

    def generate_tests_file(self, app_path, models, app_name):
        """
        Generate tests.py with comprehensive unit tests for models, API integrations, and endpoints.
        """
        logger.info("Generating 'tests.py' with comprehensive unit tests...")
        # Collect all models referenced in the current application and externally
        local_models = {model["name"] for model in models}
        external_models = set()

        # Gather external models from fields and relationships
        for model in models:
            for field in model.get("fields", []):
                if field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"] and "." in field.get("related_model", ""):
                    external_models.add(field["related_model"])
            for relation in model.get("relationships", []):
                if "." in relation.get("related_model", ""):
                    external_models.add(relation["related_model"])

        # Generate imports for local models
        model_imports = ", ".join(sorted(local_models))
        imports = f"from {app_name}.models import {model_imports}, IntegrationConfig, ValidationRule\n"

        # Generate imports for external models
        for external_model in external_models:
            external_app, external_model_name = external_model.split(".")
            imports += f"from {external_app}.models import {external_model_name}\n"

        # Base imports for the test file
        code = (
            "from django.test import TestCase\n"
            "from rest_framework.test import APIClient\n"
            "from rest_framework import status\n"
            f"{imports}\n"
            f"from {app_name}.utils.api import make_api_call\n\n"
        )

        # Add a Base Test Class for Common Setup
        code += """
class BaseTestSetup(TestCase):
    def setUp(self):
        self.valid_config = IntegrationConfig.objects.create(
            name="Test API",
            base_url="https://api.example.com",
            method="GET",
            headers={"Authorization": "Bearer testtoken"},
            timeout=10
        )
        self.client = APIClient()
"""

        # Add tests for IntegrationConfig
        code += """
class IntegrationConfigTests(BaseTestSetup):
    def test_integration_config_creation(self):
        self.assertEqual(self.valid_config.name, "Test API")
        self.assertEqual(self.valid_config.base_url, "https://api.example.com")
        self.assertEqual(self.valid_config.method, "GET")
        self.assertEqual(self.valid_config.headers["Authorization"], "Bearer testtoken")
        self.assertEqual(self.valid_config.timeout, 10)

    def test_make_api_call_success(self):
        response = make_api_call(
            base_url="https://jsonplaceholder.typicode.com/posts",
            method="GET"
        )
        self.assertTrue(isinstance(response, list))  # Assuming the API returns a list

    def test_make_api_call_failure(self):
        response = make_api_call(
            base_url="https://invalid.url",
            method="GET"
        )
        self.assertIn("error", response)
"""

        # Add tests for ValidationRule model
        code += """
class ValidationRuleTests(BaseTestSetup):
    def setUp(self):
        super().setUp()
        self.validation_rule = ValidationRule.objects.create(
            model_name="ExampleModel",
            field_name="status",
            rule_type="regex",
            params={"pattern": "^draft|published$"},
            error_message="Invalid status value."
        )

    def test_validation_rule_creation(self):
        self.assertEqual(self.validation_rule.model_name, "ExampleModel")
        self.assertEqual(self.validation_rule.field_name, "status")
        self.assertEqual(self.validation_rule.rule_type, "regex")
        self.assertEqual(self.validation_rule.params["pattern"], "^draft|published$")
        self.assertEqual(self.validation_rule.error_message, "Invalid status value.")
"""

        # Add tests for models and endpoints dynamically
        for model in models:
            model_name = model["name"]
            api_endpoint = model_name.lower()

            # Model tests
            code += f"""
class {model_name}ModelTests(BaseTestSetup):
    def setUp(self):
        super().setUp()
"""
            relationships = model.get("relationships", [])
            for relation in relationships:
                related_model_name = relation["related_model"].split(".")[-1]
                code += f"        self.{related_model_name.lower()} = {related_model_name}.objects.create()\n"
            for field in model["fields"]:
                if field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"] and "." in field.get("related_model", ""):
                    related_model_name = field["related_model"].split(".")[-1]
                    code += f"        self.{related_model_name.lower()} = {related_model_name}.objects.create()\n"
            if not relationships and not any(field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"] for field in model["fields"]):
                code += "        pass\n"

            code += f"""
    def test_create_{model_name.lower()}(self):
        obj = {model_name}.objects.create(
"""
            # Include fields during creation
            for field in model["fields"]:
                if field["type"] == "CharField":
                    code += f"            {field['name']}='Test String',\n"
                elif field["type"] == "TextField":
                    code += f"            {field['name']}='Test Text',\n"
                elif field["type"] == "BooleanField":
                    code += f"            {field['name']}=True,\n"
                elif field["type"] == "DecimalField":
                    code += f"            {field['name']}=123.45,\n"
                elif field["type"] == "EmailField":
                    code += f"            {field['name']}='test@example.com',\n"
                elif field["type"] == "URLField":
                    code += f"            {field['name']}='https://example.com',\n"
                elif field["type"] == "IntegerField":
                    code += f"            {field['name']}=123,\n"
                elif field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
                    related_model_name = field["related_model"].split(".")[-1]
                    code += f"            {field['name']}=self.{related_model_name.lower()},\n"

            code += f"""        )
        self.assertIsNotNone(obj.id)
        self.assertEqual(str(obj), f"{model_name} object ({{obj.id}})")
"""

            # API tests
            code += f"""
class {model_name}APITests(BaseTestSetup):
    def setUp(self):
        super().setUp()
"""
            for relation in relationships:
                related_model_name = relation["related_model"].split(".")[-1]
                code += f"        self.{related_model_name.lower()} = {related_model_name}.objects.create()\n"

            code += f"""
    def test_get_{api_endpoint}_list(self):
        response = self.client.get(f'/{app_name}/{api_endpoint}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_{api_endpoint}(self):
        data = {{
"""
            for field in model["fields"]:
                if field["type"] == "CharField":
                    code += f"            '{field['name']}': 'Test String',\n"
                elif field["type"] == "TextField":
                    code += f"            '{field['name']}': 'Test Text',\n"
                elif field["type"] == "BooleanField":
                    code += f"            '{field['name']}': True,\n"
                elif field["type"] == "DecimalField":
                    code += f"            '{field['name']}': 123.45,\n"
                elif field["type"] == "EmailField":
                    code += f"            '{field['name']}': 'test@example.com',\n"
                elif field["type"] == "URLField":
                    code += f"            '{field['name']}': 'https://example.com',\n"
                elif field["type"] == "IntegerField":
                    code += f"            '{field['name']}': 123,\n"
                elif field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
                    related_model_name = field["related_model"].split(".")[-1]
                    code += f"            '{field['name']}': self.{related_model_name.lower()}.id,\n"

            code += """        }
        response = self.client.post(f'/{app_name}/{api_endpoint}/', data)
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

    def test_update_{api_endpoint}(self):
        obj = {model_name}.objects.create(
"""
            # Include fields during creation for update test
            for field in model["fields"]:
                if field["type"] == "CharField":
                    code += f"            {field['name']}='Initial String',\n"
                elif field["type"] == "TextField":
                    code += f"            {field['name']}='Initial Text',\n"
                elif field["type"] == "BooleanField":
                    code += f"            {field['name']}=False,\n"
                elif field["type"] == "DecimalField":
                    code += f"            {field['name']}=100.00,\n"
                elif field["type"] == "EmailField":
                    code += f"            {field['name']}='initial@example.com',\n"
                elif field["type"] == "URLField":
                    code += f"            {field['name']}='https://initial.com',\n"
                elif field["type"] == "IntegerField":
                    code += f"            {field['name']}=100,\n"
                elif field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
                    related_model_name = field["related_model"].split(".")[-1]
                    code += f"            {field['name']}=self.{related_model_name.lower()},\n"

            code += f"""        )
        update_data = {{
"""
            for field in model["fields"]:
                if field["type"] == "CharField":
                    code += f"            '{field['name']}': 'Updated String',\n"
                elif field["type"] == "TextField":
                    code += f"            '{field['name']}': 'Updated Text',\n"
                elif field["type"] == "BooleanField":
                    code += f"            '{field['name']}': True,\n"
                elif field["type"] == "DecimalField":
                    code += f"            '{field['name']}': 150.75,\n"
                elif field["type"] == "EmailField":
                    code += f"            '{field['name']}': 'updated@example.com',\n"
                elif field["type"] == "URLField":
                    code += f"            '{field['name']}': 'https://updated.com',\n"
                elif field["type"] == "IntegerField":
                    code += f"            '{field['name']}': 150,\n"
                elif field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
                    related_model_name = field["related_model"].split(".")[-1]
                    code += f"            '{field['name']}': self.{related_model_name.lower()}.id,\n"

            code += f"""        }}
        response = self.client.put(f'/{app_name}/{api_endpoint}/{{obj.id}}/', update_data)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])

    def test_delete_{api_endpoint}(self):
        obj = {model_name}.objects.create(
"""
            # Include fields during creation for delete test
            for field in model["fields"]:
                if field["type"] == "CharField":
                    code += f"            {field['name']}='Delete String',\n"
                elif field["type"] == "TextField":
                    code += f"            {field['name']}='Delete Text',\n"
                elif field["type"] == "BooleanField":
                    code += f"            {field['name']}=False,\n"
                elif field["type"] == "DecimalField":
                    code += f"            {field['name']}=50.00,\n"
                elif field["type"] == "EmailField":
                    code += f"            {field['name']}='delete@example.com',\n"
                elif field["type"] == "URLField":
                    code += f"            {field['name']}='https://delete.com',\n"
                elif field["type"] == "IntegerField":
                    code += f"            {field['name']}=50,\n"
                elif field["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
                    related_model_name = field["related_model"].split(".")[-1]
                    code += f"            {field['name']}=self.{related_model_name.lower()},\n"

            code += f"""        )
        response = self.client.delete(f'/{app_name}/{api_endpoint}/{{obj.id}}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
"""

        # Write the tests to the `tests.py` file
        with open(os.path.join(app_path, 'tests.py'), 'w') as f:
            f.write(code)
        logger.debug("Generated 'tests.py'.")

    def generate_commands_file(self, app_path):
        """
        Generate a sample management command for the app.
        """
        logger.info("Generating sample management command 'populate_data.py'...")
        commands_path = os.path.join(app_path, 'management', 'commands')
        command_code = """\
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Populate initial data for the app'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating initial data...')
        # Add your custom logic here
        self.stdout.write(self.style.SUCCESS('Data populated successfully!'))
"""
        with open(os.path.join(commands_path, 'populate_data.py'), 'w') as f:
            f.write(command_code)
        logger.debug("Generated 'populate_data.py'.")

    def register_app_in_settings(self, app_name):
        """
        Add the app to the CUSTOM_APPS in settings.py if not already present.
        """
        logger.info(f"Registering app '{app_name}' in settings.py...")
        settings_file_path = self.get_settings_file_path()
        if not os.path.exists(settings_file_path):
            logger.error("Could not find settings.py to register the app.")
            raise CommandError("Could not find settings.py to register the app.")

        # Read the settings content
        with open(settings_file_path, "r") as f:
            settings_content = f.read()

        # Ensure the app_name is not already present in CUSTOM_APPS
        if f"'{app_name}'" not in settings_content:
            # Add the app_name to CUSTOM_APPS
            updated_content = settings_content.replace(
                "CUSTOM_APPS = [",
                f"CUSTOM_APPS = [\n    '{app_name}',"
            )
            try:
                # Write the updated settings file
                with open(settings_file_path, "w") as f:
                    f.write(updated_content)

                # Log the success message
                self.stdout.write(self.style.SUCCESS(f"App '{app_name}' added to CUSTOM_APPS."))
                logger.info(f"App '{app_name}' added to CUSTOM_APPS.")
            except Exception as e:
                logger.error(f"Error updating settings.py: {e}")
                raise CommandError(f"Error updating settings.py: {e}")
        else:
            self.stdout.write(self.style.WARNING(f"App '{app_name}' is already in CUSTOM_APPS."))
            logger.warning(f"App '{app_name}' is already in CUSTOM_APPS.")

        # Ensure the app is present in INSTALLED_APPS
        # if f"'{app_name}'" not in settings_content.split("INSTALLED_APPS")[-1]:
        #     # Parse settings.py using ast
        #     with open(settings_file_path, 'r') as file:
        #         tree = ast.parse(settings_content)
        #
        #     modified = False
        #     for node in tree.body:
        #         if isinstance(node, ast.Assign):
        #             for target in node.targets:
        #                 if getattr(target, 'id', None) == 'INSTALLED_APPS':
        #                     if isinstance(node.value, ast.List):
        #                         node.value.elts.append(ast.Constant(value=app_name))
        #                         modified = True
        #                         break
        #     if modified:
        #         try:
        #             # Write back the modified settings.py
        #             with open(settings_file_path, 'w') as f:
        #                 f.write(ast.unparse(tree))
        #             self.stdout.write(self.style.SUCCESS(f"App '{app_name}' added to INSTALLED_APPS."))
        #             logger.info(f"App '{app_name}' added to INSTALLED_APPS.")
        #         except Exception as e:
        #             logger.error(f"Error writing to settings.py: {e}")
        #             raise CommandError(f"Error writing to settings.py: {e}")
        #     else:
        #         self.stdout.write(self.style.WARNING(f"App '{app_name}' is already in INSTALLED_APPS."))
        #         logger.warning(f"App '{app_name}' is already in INSTALLED_APPS.")
        # else:
        #     self.stdout.write(self.style.WARNING(f"App '{app_name}' is already in INSTALLED_APPS."))
        #     logger.warning(f"App '{app_name}' is already in INSTALLED_APPS.")

    def add_middleware_to_settings(self, app_name):
        """
        Add the app's middleware to MIDDLEWARE in settings.py.
        """
        from pathlib import Path
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        settings_file_path = os.path.join(BASE_DIR, 'scohaz_platform', 'settings', 'settings.py')

        if not os.path.exists(settings_file_path):
            raise CommandError("Could not find settings.py to register middleware.")

        dynamic_model_middleware = f"    '{app_name}.middleware.DynamicModelMiddleware',\n"
        current_user_middleware = f"    '{app_name}.middleware.CurrentUserMiddleware',\n"

        with open(settings_file_path, "r") as f:
            settings_content = f.readlines()

        # Clean up APPS_CURRENT_USER_MIDDLEWARE
        in_apps_middleware = False
        cleaned_apps_middleware = []
        for line in settings_content:
            if line.strip().startswith("APPS_CURRENT_USER_MIDDLEWARE = ["):
                in_apps_middleware = True
            if in_apps_middleware:
                if dynamic_model_middleware.strip() in line:  # Remove misplaced DynamicModelMiddleware
                    continue
                if line.strip() == "]":
                    in_apps_middleware = False
            cleaned_apps_middleware.append(line)

        # Add CurrentUserMiddleware if not already present
        if current_user_middleware.strip() not in ''.join(cleaned_apps_middleware):
            cleaned_apps_middleware = [
                line if not line.strip().startswith("APPS_CURRENT_USER_MIDDLEWARE = [") else
                f"{line.strip()}\n{current_user_middleware}"
                for line in cleaned_apps_middleware
            ]

        # Clean up MIDDLEWARE
        in_middleware = False
        cleaned_middleware = []
        for line in cleaned_apps_middleware:
            if line.strip().startswith("MIDDLEWARE = ["):
                in_middleware = True
            if in_middleware:
                if current_user_middleware.strip() in line:  # Remove misplaced CurrentUserMiddleware
                    continue
                if line.strip() == "]":
                    in_middleware = False
            cleaned_middleware.append(line)

        # Add DynamicModelMiddleware if not already present
        if dynamic_model_middleware.strip() not in ''.join(cleaned_middleware):
            cleaned_middleware = [
                line if not line.strip().startswith("MIDDLEWARE = [") else
                f"{line.strip()}\n{dynamic_model_middleware}"
                for line in cleaned_middleware
            ]

        # Write back to settings.py
        with open(settings_file_path, "w") as f:
            f.writelines(cleaned_middleware)

        self.stdout.write(self.style.SUCCESS("Settings updated successfully."))

    def create_migrations(self, app_name):
        """
        Create migrations for the dynamically generated models and handle database integrity issues automatically.
        """
        try:
            self.stdout.write(f"Generating migrations for app '{app_name}'...")
            subprocess.run([sys.executable, 'manage.py', 'makemigrations', app_name], check=True)

            # Clean up database integrity issues before applying migrations
            self.stdout.write("Cleaning up database integrity issues...")
            clean_database_integrity_issues()

            self.stdout.write(f"Applying migrations for app '{app_name}'...")
            subprocess.run([sys.executable, 'manage.py', 'migrate', app_name], check=True)
            self.stdout.write(self.style.SUCCESS(f"Migrations successfully created and applied for '{app_name}'"))
        except subprocess.CalledProcessError as e:
            raise CommandError(f"Error during migration: {e}")


def validate_model_schema(schema):
    """
    Validate the schema for generating Django models dynamically.
    Ensures structure, relationships, field constraints, and uniqueness.
    """
    required_model_keys = {"name", "fields"}
    required_field_keys = {"name", "type"}
    valid_field_types = {
        "CharField", "TextField", "IntegerField", "FloatField", "DecimalField",
        "DateField", "DateTimeField", "BooleanField", "JSONField",  # Add JSONField
        "ForeignKey", "OneToOneField", "ManyToManyField", "PositiveIntegerField", "EmailField"
    }

    valid_relation_types = {"ForeignKey", "OneToOneField", "ManyToManyField"}
    reserved_db_table_names = {"auth_user", "django_migrations", "django_admin_log"}

    def fetch_existing_tables():
        with connection.cursor() as cursor:
            db_engine = connection.settings_dict["ENGINE"]
            if "sqlite3" in db_engine:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            elif "postgresql" in db_engine:
                cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public';")
            elif "oracle" in db_engine:
                cursor.execute("SELECT table_name FROM user_tables;")
            elif "mysql" in db_engine:
                cursor.execute("SHOW TABLES;")
            elif "microsoft" in db_engine:  # SQL Server
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE';")
            else:
                raise ValueError(f"Unsupported database vendor: {db_engine}")
            return {row[0] for row in cursor.fetchall()}

    existing_tables = fetch_existing_tables()

    for model in schema:
        # Check for required keys in models
        if not required_model_keys.issubset(model.keys()):
            missing_keys = required_model_keys - model.keys()
            raise ValueError(f"Model '{model}' is missing required keys: {missing_keys}")

        # Validate db_table name
        db_table = model.get("meta", {}).get("db_table")
        if db_table:
            if db_table in reserved_db_table_names:
                raise ValueError(f"'{db_table}' is a reserved table name and cannot be used.")
            if db_table in existing_tables:
                raise ValueError(f"Table name '{db_table}' already exists in the database.")

        # Check fields and their types
        for field in model["fields"]:
            if not required_field_keys.issubset(field.keys()):
                missing_keys = required_field_keys - field.keys()
                raise ValueError(f"Field '{field}' in model '{model['name']}' is missing required keys: {missing_keys}")

            if field["name"] in {"save", "delete", "clean", "full_clean"}:
                raise ValueError(f"Field name '{field['name']}' in model '{model['name']}' clashes with reserved keywords.")

            if field["type"] not in valid_field_types:
                raise ValueError(f"Invalid field type '{field['type']}' in model '{model['name']}'.")

            # Validate field options
            options = field.get("options", "")
            if options:
                # Assuming options are provided as a string, e.g., "max_length=255, blank=True"
                option_pairs = [opt.strip() for opt in options.split(",")]
                valid_options = {
                    "AutoField": {"primary_key", "verbose_name", "help_text", "db_column", "db_index", "unique", "editable"},
                    "BigAutoField": {"primary_key", "verbose_name", "help_text", "db_column", "db_index", "unique", "editable"},
                    "BigIntegerField": {"blank", "null", "default", "verbose_name", "help_text", "db_column", "db_index", "unique"},
                    "BinaryField": {"blank", "null", "default", "verbose_name", "help_text", "db_column"},
                    "BooleanField": {"blank", "null", "default", "verbose_name", "help_text", "db_column"},
                    "CharField": {"max_length", "blank", "null", "default", "choices", "unique", "verbose_name", "help_text", "db_column"},
                    "DateField": {"auto_now", "auto_now_add", "blank", "null", "default", "verbose_name", "help_text", "db_column"},
                    "DateTimeField": {"auto_now", "auto_now_add", "blank", "null", "default", "verbose_name", "help_text", "db_column"},
                    "DecimalField": {
                        "max_digits",
                        "decimal_places",
                        "blank",
                        "null",
                        "default",
                        "verbose_name",
                        "help_text",
                        "db_column",
                        "unique"
                    },
                    "DurationField": {"blank", "null", "default", "verbose_name", "help_text", "db_column"},
                    "EmailField": {"blank", "null", "default", "unique", "verbose_name", "help_text", "db_column", "max_length"},
                    "FileField": {"upload_to", "blank", "null", "default", "verbose_name", "help_text", "db_column"},
                    "FilePathField": {"path", "match", "recursive", "allow_files", "allow_folders", "blank", "null", "default", "verbose_name", "help_text", "db_column"},
                    "FloatField": {"blank", "null", "default", "verbose_name", "help_text", "db_column", "unique"},
                    "ImageField": {"upload_to", "blank", "null", "default", "verbose_name", "help_text", "db_column"},
                    "IntegerField": {"blank", "null", "default", "verbose_name", "help_text", "db_column", "unique"},
                    "GenericIPAddressField": {
                        "protocol",
                        "unpack_ipv4",
                        "blank",
                        "null",
                        "default",
                        "verbose_name",
                        "help_text",
                        "db_column",
                        "unique"
                    },
                    "JSONField": {"blank", "null", "default", "verbose_name", "help_text", "db_column", "unique"},
                    "ManyToManyField": {"blank", "related_name", "related_query_name", "limit_choices_to", "symmetrical", "through", "through_fields", "verbose_name", "help_text"},
                    "NullBooleanField": {"blank", "null", "default", "verbose_name", "help_text", "db_column"},
                    "OneToOneField": {"on_delete", "blank", "null", "related_name", "db_constraint", "verbose_name", "help_text", "db_column", "unique"},
                    "PositiveIntegerField": {"blank", "null", "default", "verbose_name", "help_text", "db_column", "unique"},
                    "PositiveSmallIntegerField": {"blank", "null", "default", "verbose_name", "help_text", "db_column", "unique"},
                    "SlugField": {"max_length", "blank", "null", "default", "unique", "verbose_name", "help_text", "db_column"},
                    "SmallIntegerField": {"blank", "null", "default", "verbose_name", "help_text", "db_column", "unique"},
                    "TextField": {"blank", "null", "default", "verbose_name", "help_text", "db_column", "unique"},
                    "TimeField": {"auto_now", "auto_now_add", "blank", "null", "default", "verbose_name", "help_text", "db_column"},
                    "URLField": {"max_length", "blank", "null", "default", "unique", "verbose_name", "help_text", "db_column"},
                    "UUIDField": {"default", "editable", "blank", "null", "unique", "verbose_name", "help_text", "db_column"},
                    # Add more field types as needed
                }
                field_valid_options = valid_options.get(field["type"], set())
                for opt in option_pairs:
                    key = opt.split("=")[0].strip()
                    if key not in field_valid_options:
                        raise ValueError(f"Invalid option '{key}' for field '{field['name']}' in model '{model['name']}'.")

        # Check relationships
        for relation in model.get("relationships", []):
            if not {"name", "type", "related_model"}.issubset(relation.keys()):
                missing_keys = {"name", "type", "related_model"} - relation.keys()
                raise ValueError(f"Relationship in model '{model['name']}' is missing required keys: {missing_keys}")

            if relation["type"] not in valid_relation_types:
                raise ValueError(f"Invalid relationship type '{relation['type']}' in model '{model['name']}'.")

            if "." in relation["related_model"]:
                parts = relation["related_model"].split(".")
                if len(parts) != 2 or not all(part.isidentifier() for part in parts):
                    raise ValueError(f"Invalid 'related_model' format '{relation['related_model']}' in model '{model['name']}'.")

    return True


def clean_database_integrity_issues():
    """
    Automatically cleans up database integrity issues, such as invalid foreign keys.
    Specifically, it addresses cases where foreign keys point to non-existent rows.
    """
    from django.db import connection

    try:
        with connection.cursor() as cursor:
        # Example: Identify and delete invalid foreign keys in auth_permission
            # Adjust the queries based on your specific database and integrity issues
            if connection.vendor == 'mysql':
                cursor.execute("""
                    DELETE FROM django_admin_log
                    WHERE content_type_id NOT IN (SELECT id FROM django_content_type);
                """)
                cursor.execute("""
                    DELETE FROM auth_group_permissions
                    WHERE permission_id IN (SELECT id FROM auth_permission
                    WHERE content_type_id NOT IN (SELECT id FROM django_content_type));
                """)
                cursor.execute("""
                    DELETE FROM auth_permission
                    WHERE content_type_id NOT IN (SELECT id FROM django_content_type);
                """)
                logger.debug("Cleaned up invalid foreign keys in auth_permission for MySQL.")
            elif connection.vendor == 'postgresql':
                cursor.execute("""
                    DELETE FROM django_admin_log
                    WHERE content_type_id NOT IN (SELECT id FROM django_content_type);
                """)
                cursor.execute("""
                    DELETE FROM auth_group_permissions
                    WHERE permission_id IN (SELECT id FROM auth_permission
                    WHERE content_type_id NOT IN (SELECT id FROM django_content_type));
                """)
                cursor.execute("""
                    DELETE FROM auth_permission
                    WHERE content_type_id NOT IN (SELECT id FROM django_content_type);
                """)
                logger.debug("Cleaned up invalid foreign keys in auth_permission for PostgreSQL.")
            elif connection.vendor == 'sqlite':
                cursor.execute("""
                    DELETE FROM django_admin_log
                    WHERE content_type_id NOT IN (SELECT id FROM django_content_type);
                """)
                cursor.execute("""
                    DELETE FROM auth_group_permissions
                    WHERE permission_id IN (SELECT id FROM auth_permission
                    WHERE content_type_id NOT IN (SELECT id FROM django_content_type));
                """)
                cursor.execute("""
                    DELETE FROM auth_permission
                    WHERE content_type_id NOT IN (SELECT id FROM django_content_type);
                """)
                logger.debug("Cleaned up invalid foreign keys in auth_permission for SQLite.")
            # Add more database-specific cleanup as needed

            connection.commit()
            logger.info("Database integrity issues cleaned up successfully.")
    except Exception as e:
        logger.error(f"Error during database cleanup: {e}")
        raise
