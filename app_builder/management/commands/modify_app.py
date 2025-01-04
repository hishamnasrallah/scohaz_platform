import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.apps import apps
from django.db import connection
from app_builder.management.commands.create_app import Command as CreateAppCommand

class Command(BaseCommand):
    help = 'Modify an existing Django application dynamically'

    def add_arguments(self, parser):
        parser.add_argument('app_name', type=str, help='Name of the app to modify')
        parser.add_argument('--models-file', type=str, help='Path to a JSON file containing updated model definitions')

    def handle(self, *args, **options):
        app_name = options['app_name']
        models_file = options['models_file']

        # Validate app existence
        if not apps.is_installed(app_name):
            raise CommandError(f"App '{app_name}' is not installed.")

        # Load model definitions from the file
        if not models_file or not os.path.exists(models_file):
            raise CommandError("You must provide a valid path to the models JSON file using --models-file.")

        with open(models_file, 'r') as file:
            models_schema = json.load(file)

        # Validate schema
        self.validate_schema(models_schema)

        # Modify the app
        self.stdout.write(self.style.SUCCESS(f"Modifying app '{app_name}'..."))
        self.modify_app(app_name, models_schema)
        self.stdout.write(self.style.SUCCESS(f"App '{app_name}' modified successfully."))

    def validate_schema(self, schema):
        """
        Validate the schema for correctness and conflicts.
        """
        required_model_keys = {"name", "fields"}
        required_field_keys = {"name", "type"}

        for model in schema:
            if not required_model_keys.issubset(model.keys()):
                raise CommandError(f"Model '{model}' is missing required keys: {required_model_keys - model.keys()}")

            for field in model["fields"]:
                if not required_field_keys.issubset(field.keys()):
                    raise CommandError(f"Field '{field}' in model '{model['name']}' is missing required keys: {required_field_keys - field.keys()}")

    def modify_app(self, app_name, schema):
        """
        Modify the specified app based on the new schema.
        """
        create_app_command = CreateAppCommand()

        # Regenerate models, serializers, views, admin, and URLs
        app_path = os.path.join(settings.BASE_DIR, app_name)
        create_app_command.generate_models_file(app_path, schema, app_name)
        create_app_command.generate_serializers_file(app_path, schema, app_name)
        create_app_command.generate_views_file(app_path, schema, app_name)
        create_app_command.generate_urls_file(app_path, schema, app_name)
        create_app_command.generate_admin_file(app_path, schema, app_name)
        create_app_command.generate_tests_file(app_path, schema, app_name)

        # Handle migrations
        self.handle_migrations(app_name, schema)

    def handle_migrations(self, app_name, schema):
        """
        Create and apply migrations for the modified app.
        """
        from django.core.management import call_command

        self.stdout.write(self.style.SUCCESS(f"Generating migrations for '{app_name}'..."))
        call_command('makemigrations', app_name)
        self.stdout.write(self.style.SUCCESS(f"Applying migrations for '{app_name}'..."))
        call_command('migrate', app_name)
