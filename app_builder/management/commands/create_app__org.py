import os
import json
import subprocess
import sys
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create a new Django app dynamically'

    def add_arguments(self, parser):
        parser.add_argument('app_name', type=str, help='Name of the app to create')
        parser.add_argument('--models', type=str, help='JSON definition of the models')
        parser.add_argument('--models-file', type=str, help='Path to a JSON file containing model definitions')

    def handle(self, *args, **kwargs):
        app_name = kwargs['app_name']
        models_definition = kwargs.get('models')
        models_file = kwargs.get('models_file')

        # Validate app name
        if not app_name.isidentifier():
            raise CommandError(f"Invalid app name: {app_name}")

        # Create the app directory
        app_path = os.path.join(os.getcwd(), app_name)
        if os.path.exists(app_path):
            raise CommandError(f"App '{app_name}' already exists.")
        os.makedirs(app_path)

        # Create required files
        self.create_app_files(app_name, app_path)

        # Load model definitions from either --models or --models-file
        models = None
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

        if models:
            self.generate_models_file(app_path, models, app_name)
            self.generate_serializers_file(app_path, models)
            self.generate_views_file(app_path, models)
            self.generate_urls_file(app_path, models)
            self.generate_admin_file(app_path, models)
            self.generate_tests_file(app_path, models)
            self.register_app_in_settings(app_name)

            # Generate initial migration
            self.create_migrations(app_name)

        self.stdout.write(self.style.SUCCESS(f"Application '{app_name}' created successfully."))

    def create_app_files(self, app_name, app_path):
        """
        Create basic files for the Django app.
        """
        os.makedirs(os.path.join(app_path, 'migrations'), exist_ok=True)
        open(os.path.join(app_path, '__init__.py'), 'w').close()
        open(os.path.join(app_path, 'migrations', '__init__.py'), 'w').close()
        with open(os.path.join(app_path, 'apps.py'), 'w') as f:
            f.write(
                f"from django.apps import AppConfig\n\n"
                f"class {app_name.capitalize()}Config(AppConfig):\n"
                f"    default_auto_field = 'django.db.models.BigAutoField'\n"
                f"    name = '{app_name}'\n"
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
        models_code = "from django.db import models\n\n"
        for model in models:
            model_name = model["name"]
            models_code += f"class {model_name}(models.Model):\n"
            for field in model["fields"]:
                models_code += f"    {field['name']} = models.{field['type']}({field['options']})\n"
            for relation in model.get("relationships", []):
                # Dynamically set the related model with the app name
                related_model = relation['related_model']
                if '.' not in related_model:  # If app_name is not included, add it
                    related_model = f'"{app_name}.{related_model}"'
                models_code += (
                    f"    {relation['name']} = models.{relation['type']}("
                    f"to=\"{related_model}\", {relation['options']})\n"
                )
            models_code += "\n"

        with open(os.path.join(app_path, 'models.py'), 'w') as f:
            f.write(models_code)

    def generate_serializers_file(self, app_path, models):
        """
        Generate serializers.py with ModelSerializer for each model.
        """
        code = "from rest_framework import serializers\n"
        code += "from .models import *\n\n"

        for model in models:
            model_name = model["name"]
            code += (
                f"class {model_name}Serializer(serializers.ModelSerializer):\n"
                f"    class Meta:\n"
                f"        model = {model_name}\n"
                f"        fields = '__all__'\n\n"
            )

        with open(os.path.join(app_path, 'serializers.py'), 'w') as f:
            f.write(code)

    def generate_views_file(self, app_path, models):
        """
        Generate views.py with DRF ViewSets.
        """
        code = "from rest_framework import viewsets\n"
        code += "from .models import *\n"
        code += "from .serializers import *\n\n"

        for model in models:
            model_name = model["name"]
            code += (
                f"class {model_name}ViewSet(viewsets.ModelViewSet):\n"
                f"    queryset = {model_name}.objects.all()\n"
                f"    serializer_class = {model_name}Serializer\n\n"
            )

        with open(os.path.join(app_path, 'views.py'), 'w') as f:
            f.write(code)

    def generate_urls_file(self, app_path, models):
        """
        Generate urls.py with routes for each model ViewSet.
        """
        code = (
            "from django.urls import path, include\n"
            "from rest_framework.routers import DefaultRouter\n"
            "from .views import *\n\n"
            "router = DefaultRouter()\n"
        )

        for model in models:
            model_name = model["name"]
            route_name = model_name.lower()
            code += f"router.register(r'{route_name}', {model_name}ViewSet)\n"

        code += "\nurlpatterns = [\n    path('', include(router.urls)),\n]\n"

        with open(os.path.join(app_path, 'urls.py'), 'w') as f:
            f.write(code)

    def generate_admin_file(self, app_path, models):
        """
        Generate admin.py with model registration.
        """
        code = "from django.contrib import admin\n"
        code += "from .models import *\n\n"

        for model in models:
            code += f"admin.site.register({model['name']})\n"

        with open(os.path.join(app_path, 'admin.py'), 'w') as f:
            f.write(code)

    def generate_tests_file(self, app_path, models):
        """
        Generate tests.py with unit tests for models and API endpoints.
        """
        code = (
            "from django.test import TestCase\n"
            "from rest_framework.test import APIClient\n"
            "from rest_framework import status\n"
            "from .models import *\n\n"
        )

        for model in models:
            model_name = model["name"]
            api_endpoint = model_name.lower()  # Assuming the endpoint matches the model name in lowercase.

            # Model Tests
            code += (
                f"class {model_name}ModelTests(TestCase):\n"
                f"    def setUp(self):\n"
                f"        # Create related objects if necessary\n"
            )

            # Include related fields in the setup
            for relation in model.get("relationships", []):
                related_model_name = relation["related_model"].split(".")[-1]
                code += (
                    f"        self.{related_model_name.lower()} = {related_model_name}.objects.create()\n"
                )

            code += (
                f"    def test_create_{model_name.lower()}(self):\n"
                f"        obj = {model_name}.objects.create(\n"
            )

            # Include fields and relationships during creation
            for field in model["fields"]:
                if field["type"] == "CharField":
                    code += f"            {field['name']}='Test String',\n"
                elif field["type"] == "TextField":
                    code += f"            {field['name']}='Test Text',\n"
                elif field["type"] == "DateTimeField" and "auto_now_add" not in field["options"]:
                    code += f"            {field['name']}='2023-01-01T00:00:00Z',\n"
            for relation in model.get("relationships", []):
                related_model_name = relation["related_model"].split(".")[-1]
                code += f"            {relation['name']}=self.{related_model_name.lower()},\n"

            code += (
                f"        )\n"
                f"        self.assertIsNotNone(obj.id)\n\n"
            )

            # API Tests
            code += (
                f"class {model_name}APITests(TestCase):\n"
                f"    def setUp(self):\n"
                f"        self.client = APIClient()\n"
                f"        # Create related objects\n"
            )

            for relation in model.get("relationships", []):
                related_model_name = relation["related_model"].split(".")[-1]
                code += (
                    f"        self.{related_model_name.lower()} = {related_model_name}.objects.create()\n"
                )

            code += (
                f"    def test_get_{api_endpoint}_list(self):\n"
                f"        response = self.client.get(f'/{api_endpoint}/')\n"
                f"        self.assertEqual(response.status_code, status.HTTP_200_OK)\n\n"
                f"    def test_create_{api_endpoint}(self):\n"
                f"        data = {{\n"
            )

            for field in model["fields"]:
                if field["type"] == "CharField":
                    code += f"            '{field['name']}': 'Test String',\n"
                elif field["type"] == "TextField":
                    code += f"            '{field['name']}': 'Test Text',\n"
            for relation in model.get("relationships", []):
                related_model_name = relation["related_model"].split(".")[-1]
                code += f"            '{relation['name']}': self.{related_model_name.lower()}.id,\n"

            code += (
                f"        }}\n"
                f"        response = self.client.post(f'/{api_endpoint}/', data)\n"
                f"        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])\n\n"
            )

        with open(os.path.join(app_path, 'tests.py'), 'w') as f:
            f.write(code)

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
        Create migrations for the dynamically generated models.
        """
        try:
            # Run makemigrations for the newly created app
            self.stdout.write(f"Generating migrations for app '{app_name}'...")
            os.system(f"python manage.py makemigrations {app_name}")

            # Apply the migrations
            self.stdout.write(f"Applying migrations for app '{app_name}'...")
            os.system(f"python manage.py migrate {app_name}")

            self.stdout.write(self.style.SUCCESS(f"Migrations successfully created and applied for '{app_name}'."))
        except Exception as e:
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
        Add the app to the INSTALLED_APPS in settings.py if not already present.
        """
        from pathlib import Path
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        settings_file_path = os.path.join(BASE_DIR, "scohaz_platform/settings/settings.py")  # Adjust this to your settings file location
        if not os.path.exists(settings_file_path):
            raise CommandError("Could not find settings.py to register the app.")

        with open(settings_file_path, "r") as f:
            settings_content = f.read()

        if f"'{app_name}'" not in settings_content:
            updated_content = settings_content.replace(
                "CUSTOM_APPS = [",
                f"CUSTOM_APPS = [\n    '{app_name}',"
            )

            with open(settings_file_path, "w") as f:
                f.write(updated_content)
            self.stdout.write(self.style.SUCCESS(f"App '{app_name}' added to INSTALLED_APPS."))
        else:
            self.stdout.write(self.style.WARNING(f"App '{app_name}' is already in INSTALLED_APPS."))
