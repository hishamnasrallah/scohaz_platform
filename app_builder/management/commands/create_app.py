import os
import json
import subprocess
import sys
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = 'Create a new Django app dynamically'

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

        if not app_name.isidentifier():
            raise CommandError(f"Invalid app name: {app_name}")

        # Step 1: Load and validate model definitions
        models = self.load_model_definitions(models_definition, models_file)
        try:
            self.stdout.write(f"Validating schema for '{app_name}'...")
            validate_model_schema(models)
            self.stdout.write(self.style.SUCCESS(f"Schema validation passed for '{app_name}'!"))
        except ValueError as e:
            raise CommandError(f"Schema validation failed: {e}")

        # Step 2: Proceed with app creation, Set up app folder and files
        app_path = os.path.join(os.getcwd(), app_name)
        if os.path.exists(app_path):
            raise CommandError(f"App '{app_name}' already exists.")
        os.makedirs(app_path)

        self.create_app_files(app_name, app_path)
        self.generate_mixins_file(app_path, app_name)
        self.generate_models_file(app_path, models, app_name)
        self.generate_signals_file(app_path, models, app_name)
        self.generate_utils_folder(app_path, app_name)
        self.generate_middleware_file(app_path, app_name)
        self.generate_serializers_file(app_path, models, app_name)
        self.generate_views_file(app_path, models, app_name)
        self.generate_urls_file(app_path, models, app_name)
        self.generate_admin_file(app_path, models, app_name)
        self.generate_tests_file(app_path, models, app_name)
        self.generate_commands_file(app_path)
        self.register_app_in_settings(app_name)
        self.add_middleware_to_settings(app_name)
        self.create_migrations(app_name)

        self.stdout.write(self.style.SUCCESS(f"Application '{app_name}' created successfully."))


    def load_model_definitions(self, models_definition, models_file):
        """
        Load model definitions from either a string or a file, and validate the schema.
        """
        if models_definition:
            try:
                models = json.loads(models_definition)
            except json.JSONDecodeError as e:
                raise CommandError(f"Invalid JSON for models: {e}")
        elif models_file:
            try:
                with open(models_file, 'r') as file:
                    models = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                raise CommandError(f"Error reading models file '{models_file}': {e}")
        else:
            raise CommandError("You must provide model definitions using --models or --models-file.")

        # Validate the schema
        try:
            validate_model_schema(models)
            self.stdout.write(self.style.SUCCESS("Model schema validation passed!"))
        except ValueError as e:
            raise CommandError(f"Schema validation error: {e}")

        return models

    def create_app_files(self, app_name, app_path):
        """
        Create basic files for the Django app with advanced configuration in apps.py.
        """
        os.makedirs(os.path.join(app_path, 'migrations'), exist_ok=True)
        open(os.path.join(app_path, '__init__.py'), 'w').close()
        open(os.path.join(app_path, 'migrations', '__init__.py'), 'w').close()

        # Create the management/commands directory structure
        os.makedirs(os.path.join(app_path, 'management', 'commands'), exist_ok=True)
        open(os.path.join(app_path, 'management', '__init__.py'), 'w').close()  # Init for management directory
        open(os.path.join(app_path, 'management', 'commands', '__init__.py'), 'w').close()  # Init for commands directory

        # Create apps.py
        with open(os.path.join(app_path, 'apps.py'), 'w') as f:
            f.write(
                f"from django.apps import AppConfig\n\n"
                f"class {app_name.capitalize()}Config(AppConfig):\n"
                f"    default_auto_field = 'django.db.models.BigAutoField'\n"
                f"    name = '{app_name}'\n\n"
                f"    def ready(self):\n"
                f"        # Custom initialization logic for {app_name}\n"
                f"        import {app_name}.signals\n"
                f"        print('App {app_name} is ready!')\n"
            )

    #
    # def generate_models_file(self, app_path, models):
    #     """
    #     Generate models.py with dynamic model definitions.
    #     """
    #     models_code = "from django.db import models\n\n"
    #     for model in models:
    #         model_name = model["name"]
    #         models_code += f"class {model_name}(models.Model):\n"
    #         for field in model["fields"]:
    #             models_code += f"    {field['name']} = models.{field['type']}({field['options']})\n"
    #         for relation in model.get("relationships", []):
    #             models_code += (
    #                 f"    {relation['name']} = models.{relation['type']}("
    #                 f"{relation['related_model']}, {relation['options']})\n"
    #             )
    #         models_code += "\n"
    #
    #     with open(os.path.join(app_path, 'models.py'), 'w') as f:
    #         f.write(models_code)

    def generate_models_file(self, app_path, models, app_name):
        """
        Generate models.py with dynamic model definitions.
        """
        # Start adding necessary imports
        models_code = "from django.db import models\n"
        models_code += "from django.db.models.signals import post_save\n"
        models_code += "from django.dispatch import receiver\n"
        models_code += "from .mixins import DynamicValidationMixin\n\n"

        # Add IntegrationConfig model for API integrations
        models_code += """
class IntegrationConfig(models.Model):
    name = models.CharField(max_length=255)
    base_url = models.URLField()
    method = models.CharField(
        max_length=10,
        choices=[
            ('GET', 'GET'),
            ('POST', 'POST'),
            ('PUT', 'PUT'),
            ('DELETE', 'DELETE')
        ]
    )
    headers = models.JSONField(blank=True, null=True)
    body = models.JSONField(blank=True, null=True)
    timeout = models.IntegerField(default=30)

    class Meta:
        verbose_name = 'Integration Config'
        verbose_name_plural = 'Integration Configs'

    def __str__(self):
        return self.name\n\n
"""

        # Add ValidationRule model
        models_code += """
class ValidationRule(models.Model):
    model_name = models.CharField(max_length=255)
    field_name = models.CharField(max_length=255)
    rule_type = models.CharField(max_length=50, choices=[('regex', 'Regex'), ('custom', 'Custom')])
    rule_value = models.TextField()
    error_message = models.TextField()
    user_roles = models.JSONField(blank=True, null=True)
    global_rule = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.model_name}.{self.field_name}: {self.rule_type}"
"""

        # Iterate over models to generate model classes
        for model in models:
            model_name = model["name"]
            models_code += f"class {model_name}(DynamicValidationMixin, models.Model):\n"

            # Add fields to the model
            for field in model["fields"]:
                options = field.get("options", "")

                # Handle static choices
                if "choices" in field:
                    choices_name = f"{field['name'].upper()}_CHOICES"
                    models_code += f"    {choices_name} = {field['choices']}\n"
                    options += f", choices={choices_name}"

                # Handle dynamic choices using _lookup
                if "_lookup" in field:
                    models_code += (
                        f"    {field['name']} = models.ForeignKey(\n"
                        f"        to='lookup.Lookup',\n"
                        f"        on_delete=models.CASCADE,\n"
                        f"        limit_choices_to={{'parent_lookup__code': '{field['_lookup']}'}}\n"
                        f"    )\n"
                    )
                elif field["type"] == "OneToOneField":
                    options = field.get("options", "")
                    models_code += f"    {field['name']} = models.OneToOneField(to='{field['related_model']}', {options})\n"
                elif field["type"] == "ManyToManyField":
                    options = field.get("options", "")
                    models_code += f"    {field['name']} = models.ManyToManyField(to='{field['related_model']}', {options})\n"
                elif field["type"] == "ForeignKey":
                    related_name = f"{app_name.lower()}_{model_name.lower()}_{field['name']}_set"
                    options += f", related_name='{related_name}'"
                    models_code += f"    {field['name']} = models.{field['type']}('{field['related_model']}', {options})\n"
                else:
                    models_code += f"    {field['name']} = models.{field['type']}({options})\n"

            # Add relationships
            for relation in model.get("relationships", []):
                related_model = relation["related_model"]
                options = relation.get("options", "")
                related_name = f"{app_name.lower()}_{model_name.lower()}_{relation['name']}_set"
                options += f", related_name='{related_name}'"
                models_code += (
                    f"    {relation['name']} = models.{relation['type']}(\n"
                    f"        to='{related_model}',\n"
                    f"        {options}\n"
                    f"    )\n"
                )

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
\n
"""

        # Write the models to the models.py file
        with open(os.path.join(app_path, "models.py"), "w") as f:
            f.write(models_code)

    def generate_serializers_file(self, app_path, models, app_name):
        """
        Generate serializers.py with ModelSerializer for each model, including IntegrationConfig and ValidationRule.
        """
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
        fields = '__all__'\n\n
"""

        # Add ValidationRule serializer
        code += """
class ValidationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidationRule
        fields = '__all__'\n\n
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

    def generate_views_file(self, app_path, models, app_name):
        """
        Generate views.py with DRF ViewSets, applying conditional logic.
        """
        # Import base modules
        imports = f"""from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from {app_name}.models import {', '.join(model['name'] for model in models)}, IntegrationConfig, ValidationRule
from {app_name}.serializers import {', '.join(f"{model['name']}Serializer" for model in models)}, IntegrationConfigSerializer, ValidationRuleSerializer
from {app_name}.utils.api import make_api_call
"""
        # Start views file content
        views_code = imports + "\n"

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
        return Response(response, status=status.HTTP_200_OK if "error" not in response else status.HTTP_400_BAD_REQUEST)
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

    def generate_urls_file(self, app_path, models, app_name):
        """
        Generate urls.py with routes for IntegrationConfig, ValidationRule, and dynamically generated models.
        """
        # Generate view names for dynamic models
        viewset_names = ", ".join(f"{model['name']}ViewSet" for model in models)

        # Base imports for urls file
        imports = f"""from django.urls import path, include
from rest_framework.routers import DefaultRouter
from {app_name}.views import IntegrationConfigViewSet, ValidationRuleViewSet, {viewset_names}


"""

        # Initialize the router
        router_initialization = "router = DefaultRouter()\n"

        # Register IntegrationConfig and ValidationRule endpoints
        router_registration = """router.register(r'integration-configs', IntegrationConfigViewSet)
router.register(r'validation-rules', ValidationRuleViewSet)
"""

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

        # Automatically add the app's URLs to the project's main urls.py
        # self.add_to_main_urls(app_name)

    def add_to_main_urls(self, app_name):
        """
        Add the app's URLs to the main project's urls.py file.
        """
        # Define the path to the main project's `urls.py`
        project_urls_path = os.path.join(os.getcwd(), "scohaz_platform", "urls.py")  # Adjust path as per your project structure
        if not os.path.exists(project_urls_path):
            raise CommandError("Could not find the project's main urls.py file to register the app's routes.")

        with open(project_urls_path, "r") as f:
            project_urls_content = f.read()

        # Check if the app's routes are already registered
        if f"'{app_name}.urls'" not in project_urls_content:
            updated_content = project_urls_content.replace(
                "urlpatterns = [",
                f"urlpatterns = [\n    path('{app_name}/', include('{app_name}.urls')),"
            )

            with open(project_urls_path, "w") as f:
                f.write(updated_content)

            self.stdout.write(self.style.SUCCESS(f"Routes for '{app_name}' added to the project's main URLs."))
        else:
            self.stdout.write(self.style.WARNING(f"Routes for '{app_name}' are already registered in the project's main URLs."))

    def generate_admin_file(self, app_path, models, app_name):
        """
        Generate admin.py with dynamic registration and configuration.
        """
        admin_code = "from django.contrib import admin\n"
        admin_code += f"from {app_name}.models import *\n\n"
        admin_code += """
@admin.register(IntegrationConfig)
class IntegrationConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_url', 'method')
    search_fields = ('name', 'base_url')\n\n
"""
        admin_code += """
@admin.register(ValidationRule)
class ValidationRuleAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'field_name', 'rule_type', 'error_message')
    search_fields = ('model_name', 'field_name', 'rule_type')\n\n
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

            admin_code += f"class {admin_class_name}(admin.ModelAdmin):\n"
            admin_code += f"    list_display = {list_display}\n"
            admin_code += f"    search_fields = {search_fields}\n"
            admin_code += f"    list_filter = {list_filter}\n\n"
            admin_code += f"admin.site.register({model_name}, {admin_class_name})\n\n"

        # Write the admin.py file
        admin_file_path = os.path.join(app_path, 'admin.py')
        with open(admin_file_path, 'w') as f:
            f.write(admin_code)

    def generate_middleware_file(self, app_path, app_name):
        """
        Generate middleware.py to handle dynamic logic for requests and responses.
        """
        middleware_code = f"""
from django.utils.deprecation import MiddlewareMixin
from {app_name}.models import IntegrationConfig

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

    def add_middleware_to_settings(self, app_name):
        """
        Add the app's middleware to MIDDLEWARE in settings.py.
        """
        from pathlib import Path
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        settings_file_path = os.path.join(BASE_DIR, 'scohaz_platform', 'settings', 'settings.py')

        if not os.path.exists(settings_file_path):
            raise CommandError("Could not find settings.py to register middleware.")

        with open(settings_file_path, "r") as f:
            settings_content = f.read()

        middleware_entry = f"    '{app_name}.middleware.DynamicModelMiddleware',"

        # Check if the middleware is already present
        if middleware_entry not in settings_content:
            updated_content = settings_content.replace(
                "MIDDLEWARE = [",
                f"MIDDLEWARE = [\n{middleware_entry}"
            )
            with open(settings_file_path, "w") as f:
                f.write(updated_content)
            self.stdout.write(self.style.SUCCESS(f"Middleware for '{app_name}' added to MIDDLEWARE in settings.py."))
        else:
            self.stdout.write(self.style.WARNING(f"Middleware for '{app_name}' is already registered."))

    def generate_tests_file(self, app_path, models, app_name):
        """
        Generate tests.py with comprehensive unit tests for models, API integrations, and endpoints.
        """
        # Collect all models referenced in the current application and externally
        local_models = {model["name"] for model in models}
        external_models = set()

        # Gather external models from fields and relationships
        for model in models:
            for field in model.get("fields", []):
                if field["type"] == "ForeignKey" and "." in field["related_model"]:
                    external_models.add(field["related_model"])
            for relation in model.get("relationships", []):
                if "." in relation["related_model"]:
                    external_models.add(relation["related_model"])

        # Generate imports for local models
        model_imports = ", ".join(sorted(local_models))
        imports = f"from {app_name}.models import {model_imports}, IntegrationConfig, ValidationRule"

        # Generate imports for external models
        for external_model in external_models:
            external_app, external_model_name = external_model.split(".")
            imports += f"\nfrom {external_app}.models import {external_model_name}"

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
        self.client = APIClient()\n\n
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
        self.assertIn("error", response)\n\n
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
            rule_value="^draft|published$",
            error_message="Invalid status value."
        )

    def test_validation_rule_creation(self):
        self.assertEqual(self.validation_rule.model_name, "ExampleModel")
        self.assertEqual(self.validation_rule.field_name, "status")
        self.assertEqual(self.validation_rule.rule_type, "regex")
        self.assertEqual(self.validation_rule.rule_value, "^draft|published$")
        self.assertEqual(self.validation_rule.error_message, "Invalid status value.")\n\n
"""

        # Add tests for models and endpoints dynamically
        for model in models:
            model_name = model["name"]
            api_endpoint = model_name.lower()

            # Model tests
            code += f"\nclass {model_name}ModelTests(BaseTestSetup):\n"
            code += "    def setUp(self):\n"
            code += "        super().setUp()\n"

            # Create related objects for relationships
            relationships = model.get("relationships", [])
            for relation in relationships:
                related_model_name = relation["related_model"].split(".")[-1]
                code += f"        self.{related_model_name.lower()} = {related_model_name}.objects.create()\n"
            if not relationships:
                code += "        pass\n"

            code += f"    def test_create_{model_name.lower()}(self):\n"
            code += f"        obj = {model_name}.objects.create(\n"

            # Include fields during creation
            for field in model["fields"]:
                if field["type"] == "CharField":
                    code += f"            {field['name']}='Test String',\n"
                elif field["type"] == "TextField":
                    code += f"            {field['name']}='Test Text',\n"
                elif field["type"] == "DateTimeField" and "auto_now_add" not in field["options"]:
                    code += f"            {field['name']}='2023-01-01T00:00:00Z',\n"
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

            # Add relationships during creation
            for relation in relationships:
                related_model_name = relation["related_model"].split(".")[-1]
                code += f"            {relation['name']}=self.{related_model_name.lower()},\n"

            code += (
                f"        )\n"
                f"        self.assertIsNotNone(obj.id)\n"
                f"        self.assertEqual(str(obj), f'{model_name} object ({{obj.id}})')\n\n"
            )

            # API tests
            code += f"class {model_name}APITests(BaseTestSetup):\n"
            code += "    def setUp(self):\n"
            code += "        super().setUp()\n"

            for relation in relationships:
                related_model_name = relation["related_model"].split(".")[-1]
                code += f"        self.{related_model_name.lower()} = {related_model_name}.objects.create()\n"

            code += f"    def test_get_{api_endpoint}_list(self):\n"
            code += f"        response = self.client.get(f'/{app_name}/{api_endpoint}/')\n"
            code += f"        self.assertEqual(response.status_code, status.HTTP_200_OK)\n\n"

            code += f"    def test_create_{api_endpoint}(self):\n"
            code += "        data = {\n"

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

            for relation in relationships:
                related_model_name = relation["related_model"].split(".")[-1]
                code += f"            '{relation['name']}': self.{related_model_name.lower()}.id,\n"

            code += "        }\n"
            code += f"        response = self.client.post(f'/{app_name}/{api_endpoint}/', data)\n"
            code += "        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])\n\n"

        # Write the tests to the `tests.py` file
        with open(os.path.join(app_path, 'tests.py'), 'w') as f:
            f.write(code)

    def generate_commands_file(self, app_path):
        """
        Generate a sample management command for the app.
        """
        commands_path = os.path.join(app_path, 'management', 'commands')
        command_code = """
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

    # def generate_tests_file(self, app_path, models):
    #     """
    #     Generate tests.py with unit tests for models and API endpoints.
    #     """
    #     code = (
    #         "from django.test import TestCase\n"
    #         "from rest_framework.test import APIClient\n"
    #         "from rest_framework import status\n"
    #         "from .models import *\n\n"
    #     )
    #
    #     for model in models:
    #         model_name = model["name"]
    #         api_endpoint = model_name.lower()  # Assuming the endpoint matches the model name in lowercase.
    #
    #         # Model Tests
    #         code += (
    #             f"class {model_name}ModelTests(TestCase):\n"
    #             f"    def setUp(self):\n"
    #             f"        # Setup logic for {model_name}\n"
    #             f"        pass\n\n"
    #             f"    def test_create_{model_name.lower()}(self):\n"
    #             f"        # Test creating a {model_name} instance\n"
    #             f"        obj = {model_name}.objects.create()\n"
    #             f"        self.assertIsNotNone(obj.id)\n\n"
    #             f"    def test_str_representation_{model_name.lower()}(self):\n"
    #             f"        # Add logic to test __str__ or similar methods\n"
    #             f"        obj = {model_name}.objects.create()\n"
    #             f"        self.assertEqual(str(obj), 'Expected String')\n\n"
    #         )
    #
    #         # API Tests
    #         code += (
    #             f"class {model_name}APITests(TestCase):\n"
    #             f"    def setUp(self):\n"
    #             f"        self.client = APIClient()\n"
    #             f"        # Add setup logic if required\n\n"
    #             f"    def test_get_{api_endpoint}_list(self):\n"
    #             f"        response = self.client.get(f'/{api_endpoint}/')\n"
    #             f"        self.assertEqual(response.status_code, status.HTTP_200_OK)\n\n"
    #             f"    def test_create_{api_endpoint}(self):\n"
    #             f"        data = {{}}\n"  # Add field data based on model definition if possible
    #             f"        response = self.client.post(f'/{api_endpoint}/', data)\n"
    #             f"        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])\n\n"
    #             f"    def test_update_{api_endpoint}(self):\n"
    #             f"        data = {{}}\n"  # Add update data logic
    #             f"        obj = {model_name}.objects.create()\n"
    #             f"        response = self.client.put(f'/{api_endpoint}/{{obj.id}}/', data)\n"
    #             f"        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])\n\n"
    #             f"    def test_delete_{api_endpoint}(self):\n"
    #             f"        obj = {model_name}.objects.create()\n"
    #             f"        response = self.client.delete(f'/{api_endpoint}/{{obj.id}}/')\n"
    #             f"        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)\n\n"
    #         )
    #
    #     with open(os.path.join(app_path, 'tests.py'), 'w') as f:
    #         f.write(code)

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

    # def generate_migrations(self, app_name):
    #     """
    #     Generate initial migrations for the app.
    #     """
    #     python_executable = sys.executable  # Get the current Python executable
    #     try:
    #         subprocess.run([python_executable, "manage.py", "makemigrations", app_name], check=True)
    #         subprocess.run([python_executable, "manage.py", "migrate"], check=True)
    #     except subprocess.CalledProcessError as e:
    #         raise CommandError(f"Error during migration: {e}")

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

    def validate_model_schema(models):
        """
        Validate the JSON schema for dynamic model creation.
        Ensures structure, relationships, field constraints, and uniqueness.
        """
        required_model_keys = {"name", "fields"}
        required_field_keys = {"name", "type"}
        valid_field_types = {
            "CharField", "TextField", "IntegerField", "FloatField", "DecimalField",
            "DateField", "DateTimeField", "BooleanField", "JSONField",  # Add JSONField
            "ForeignKey", "OneToOneField", "ManyToManyField", "PositiveIntegerField", "EmailField"
        }

        valid_options_per_type = {
            "CharField": {"max_length", "blank", "null", "default"},
            "TextField": {"blank", "null", "default"},
            "IntegerField": {"blank", "null", "default"},
            # Add more fields and their valid options here
        }
        reserved_keywords = {"save", "delete", "clean", "full_clean"}

        # Fetch existing database tables
        def fetch_existing_tables():
            with connection.cursor() as cursor:
                if connection.vendor == 'sqlite':
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                elif connection.vendor == 'postgresql':
                    cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public';")
                elif connection.vendor == 'mysql':
                    cursor.execute("SHOW TABLES;")
                elif connection.vendor == 'oracle':
                    cursor.execute("SELECT table_name FROM user_tables;")
                else:
                    raise ValueError(f"Unsupported database vendor: {connection.vendor}")
                return {row[0] for row in cursor.fetchall()}

        existing_tables = fetch_existing_tables()

        for model in models:
            # Validate model keys
            if not required_model_keys.issubset(model.keys()):
                missing_keys = required_model_keys - model.keys()
                raise ValueError(f"Model '{model}' is missing required keys: {missing_keys}")

            # Validate model name
            if not model["name"].isidentifier():
                raise ValueError(f"Invalid model name '{model['name']}'. Must be a valid Python identifier.")

            # Validate field definitions
            field_names = set()
            for field in model["fields"]:
                if not required_field_keys.issubset(field.keys()):
                    missing_keys = required_field_keys - field.keys()
                    raise ValueError(f"Field '{field}' in model '{model['name']}' is missing required keys: {missing_keys}")

                if field["name"] in field_names:
                    raise ValueError(f"Duplicate field name '{field['name']}' in model '{model['name']}'.")
                if field["name"] in reserved_keywords:
                    raise ValueError(f"Field name '{field['name']}' in model '{model['name']}' clashes with reserved keywords.")
                field_names.add(field["name"])

                # Validate field type
                if field["type"] not in valid_field_types:
                    raise ValueError(f"Invalid field type '{field['type']}' in field '{field['name']}' of model '{model['name']}'.")

                # Validate field options
                options = field.get("options", "")
                if options:
                    invalid_options = set(options.split(", ")) - valid_options_per_type.get(field["type"], set())
                    if invalid_options:
                        raise ValueError(f"Invalid options for field '{field['name']}' in model '{model['name']}': {invalid_options}")

            # Validate relationships
            for relation in model.get("relationships", []):
                if not {"name", "type", "related_model"}.issubset(relation.keys()):
                    missing_keys = {"name", "type", "related_model"} - relation.keys()
                    raise ValueError(f"Relationship in model '{model['name']}' is missing required keys: {missing_keys}")

                if not relation["related_model"].isidentifier() and "." not in relation["related_model"]:
                    raise ValueError(f"Invalid related_model '{relation['related_model']}' in model '{model['name']}'.")

            # Validate unique Meta attributes (e.g., db_table)
            meta = model.get("meta", {})
            if meta:
                db_table = meta.get("db_table")
                if db_table and db_table in existing_tables:
                    raise ValueError(f"Custom db_table '{db_table}' in model '{model['name']}' already exists in the database.")

        return True


    def generate_mixins_file(self, app_path, app_name):
        """
        Generate mixins.py with dynamic validation logic using VALIDATOR_REGISTRY.
        """
        mixin_code = f"""
from django.core.exceptions import ValidationError
from .utils.validators import VALIDATOR_REGISTRY


class DynamicValidationMixin:
    def clean(self):
        super().clean()

        # Import ValidationRule dynamically to avoid circular import
        from django.apps import apps
        ValidationRule = apps.get_model('{app_name}', 'ValidationRule')

        # Get the model name
        model_name = self.__class__.__name__

        # Fetch validation rules for this model
        rules = ValidationRule.objects.filter(model_name=model_name)

        # Get the user from the instance's context
        user = getattr(self, '_validation_user', None)

        for rule in rules:
            # Skip rule if it's not a global rule and user-specific context is missing
            if not rule.global_rule and not user:
                continue

            # Role-Based Validation (handle JSONField 'user_roles')
            if rule.user_roles and user:
                user_groups = set(user.groups.values_list('name', flat=True))
                required_roles = set(rule.user_roles)
                if not user_groups.intersection(required_roles):
                    continue  # Skip rules that don't match the user's roles

            # Fetch the validator dynamically from the registry
            validator = VALIDATOR_REGISTRY.get(rule.rule_type)
            if not validator:
                raise ValidationError({{
                    "__all__": f"Unknown validation rule type: {{rule.rule_type}}"
                }})

            # Parse rule_value dynamically for specific validations
            try:
                if rule.rule_type == 'range':
                    params = [float(p) for p in rule.rule_value.split(',')]
                elif rule.rule_type == 'choice':
                    params = [eval(rule.rule_value)]  # Safely parse the choices
                else:
                    params = [rule.rule_value]

                # Call the validator with appropriate arguments
                validator(
                    getattr(self, rule.field_name, None),
                    *params,
                    error_message=rule.error_message,
                    instance=self,
                    user=user
                )
            except Exception as e:
                raise ValidationError({{
                    rule.field_name: f"Validation error: {{str(e)}}"
                }})

    def set_validation_user(self, user):
        \"\"\"Method to set the user for context-sensitive validation.\"\"\" 
        setattr(self, '_validation_user', user)
"""
        with open(os.path.join(app_path, 'mixins.py'), 'w') as f:
            f.write(mixin_code)


#     def generate_mixins_file(self, app_path, app_name):
#         """
#         Generate mixins.py with dynamic validation logic for user-specific and permission-based rules.
#         """
#         mixin_code = f"""
# from django.core.exceptions import ValidationError
# from django.contrib.auth.models import Permission
#
#
# class DynamicValidationMixin:
#     def clean(self):
#         super().clean()
#
#         # Import ValidationRule dynamically to avoid circular import
#         from django.apps import apps
#         ValidationRule = apps.get_model('{app_name}', 'ValidationRule')
#
#         # Get the model name
#         model_name = self.__class__.__name__
#
#         # Fetch validation rules for this model
#         rules = ValidationRule.objects.filter(model_name=model_name)
#
#         # Get the user from the instance's context
#         user = getattr(self, '_validation_user', None)
#
#         for rule in rules:
#             # Role-Based Validation
#             if rule.user_role and user and not user.groups.filter(name=rule.user_role).exists():
#                 continue  # Skip rules that don't apply to the user's role
#
#             # Permission-Based Validation
#             if rule.permission_required and user:
#                 try:
#                     permission = Permission.objects.get(codename=rule.permission_required)
#                     if not user.has_perm(f"{{permission.content_type.app_label}}.{{permission.codename}}"):
#                         continue  # Skip rules if the user lacks the required permission
#                 except Permission.DoesNotExist:
#                     raise ValidationError({{
#                         "__all__": f"Validation rule references a non-existent permission: {{rule.permission_required}}"
#                     }})
#
#             # Get the value of the field being validated
#             field_value = getattr(self, rule.field_name, None)
#
#             # Regex-Based Validation
#             if rule.rule_type == 'regex':
#                 import re
#                 if not re.match(rule.rule_value, str(field_value)):
#                     raise ValidationError({{rule.field_name: rule.error_message}})
#
#             # Custom Function-Based Validation
#             elif rule.rule_type == 'custom':
#                 module_path, func_name = rule.rule_value.rsplit('.', 1)
#                 try:
#                     module = __import__(module_path, fromlist=[func_name])
#                     func = getattr(module, func_name)
#                     func(self, field_value, user)  # Call the custom validation function
#                 except Exception as e:
#                     raise ValidationError({{
#                         rule.field_name: f"Custom validation failed: {{str(e)}}"
#                     }})
#
#     def set_validation_user(self, user):
#         \"\"\"
#         Method to set the user for context-sensitive validation.
#         \"\"\"
#         setattr(self, '_validation_user', user)
# """
#         with open(os.path.join(app_path, 'mixins.py'), 'w') as f:
#             f.write(mixin_code)

    def generate_signals_file(self, app_path, models, app_name):
        """
        Generate signals.py to handle dynamic pre-save and post-save hooks for models.
        """
        signal_code = (
            "from django.db.models.signals import pre_save, post_save\n"
            "from django.dispatch import receiver\n"
            f"from {app_name}.models import {', '.join(model['name'] for model in models)}\n\n"
        )

        # Generate pre-save and post-save hooks for each model
        for model in models:
            model_name = model["name"]

            # Pre-save signal
            signal_code += (
                f"@receiver(pre_save, sender={model_name})\n"
                f"def pre_save_{model_name.lower()}(sender, instance, **kwargs):\n"
                f"    # Add custom pre-save logic here\n"
                f"    print(f'Pre-save hook triggered for {model_name}: {{instance}}')\n\n"
            )

            # Post-save signal
            signal_code += (
                f"@receiver(post_save, sender={model_name})\n"
                f"def post_save_{model_name.lower()}(sender, instance, created, **kwargs):\n"
                f"    if created:\n"
                f"        print(f'{model_name} instance created: {{instance}}')\n"
                f"    else:\n"
                f"        print(f'{model_name} instance updated: {{instance}}')\n\n"
            )

        # Write the signals file
        signals_file_path = os.path.join(app_path, 'signals.py')
        with open(signals_file_path, 'w') as f:
            f.write(signal_code)

    def generate_utils_folder(self, app_path, app_name):
        """
        Generate a utils folder with modular validation and API call logic.
        Automatically adapts to the app context.
        """
        utils_folder_path = os.path.join(app_path, 'utils')
        os.makedirs(utils_folder_path, exist_ok=True)

        # Generate __init__.py for the utils package
        with open(os.path.join(utils_folder_path, '__init__.py'), 'w') as init_file:
            init_file.write("# utils package\n")

        # Generate validators.py
        validators_code = f"""
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
"""
        with open(os.path.join(utils_folder_path, 'validators.py'), 'w') as validators_file:
            validators_file.write(validators_code)

        # Generate api.py
        api_code = """
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

def validate_model_schema(schema):
    """
    Validate the schema for generating Django models dynamically.
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
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE();")
            elif "microsoft" in db_engine:  # SQL Server
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE';")
            else:
                raise ValueError("Unsupported database backend.")
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

            if field["type"] not in valid_field_types:
                raise ValueError(f"Invalid field type '{field['type']}' in model '{model['name']}'.")

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
            # Identify problematic rows in `auth_permission`
            cursor.execute("""
                DELETE FROM auth_permission
                WHERE content_type_id NOT IN (SELECT id FROM django_content_type);
            """)
            connection.commit()
            print("Cleaned up invalid foreign keys in auth_permission.")
    except Exception as e:
        print(f"Error during database cleanup: {e}")

