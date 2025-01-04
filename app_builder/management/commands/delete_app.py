import os
import shutil
from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

class Command(BaseCommand):
    help = "Delete a Django app dynamically with full cleanup and logging."

    def add_arguments(self, parser):
        parser.add_argument('app_name', type=str, help="Name of the app to delete")

    def handle(self, *args, **kwargs):
        app_name = kwargs['app_name']

        if not app_name.isidentifier():
            raise CommandError(f"Invalid app name: {app_name}")

        self.stdout.write(f"Starting deletion process for app '{app_name}'...")

        try:
            # Step 1: Remove app folder
            self._remove_app_folder(app_name)

            # Step 2: Remove app references in settings
            self._remove_from_settings(app_name)

            # Step 3: Delete associated database records
            self._cleanup_database(app_name)

            # Step 4: Drop app tables
            self._drop_app_tables(app_name)

            self.stdout.write(self.style.SUCCESS(f"App '{app_name}' deleted successfully."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error during deletion of app '{app_name}': {e}"))
            raise CommandError(f"Deletion failed: {e}")

    def _remove_app_folder(self, app_name):
        app_path = os.path.join(settings.BASE_DIR, app_name)
        if os.path.exists(app_path):
            shutil.rmtree(app_path)
            self.stdout.write(self.style.SUCCESS(f"Removed app folder: {app_path}"))
        else:
            self.stdout.write(self.style.WARNING(f"App folder '{app_path}' does not exist."))

    def _remove_from_settings(self, app_name):
        settings_file_path = os.path.join(settings.BASE_DIR, 'scohaz_platform', 'settings', 'settings.py')
        if not os.path.exists(settings_file_path):
            self.stdout.write(self.style.WARNING("Could not find settings.py to update."))
            return

        with open(settings_file_path, 'r') as f:
            settings_content = f.readlines()

        updated_content = []
        for line in settings_content:
            if app_name not in line:
                updated_content.append(line)

        with open(settings_file_path, 'w') as f:
            f.writelines(updated_content)

        self.stdout.write(self.style.SUCCESS(f"Removed '{app_name}' references from settings."))

    def _cleanup_database(self, app_name):
        with transaction.atomic():
            try:
                # Delete permissions
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM auth_permission WHERE content_type_id IN ("
                        "SELECT id FROM django_content_type WHERE app_label = %s);",
                        [app_name]
                    )
                    self.stdout.write(f"Deleted {cursor.rowcount} permissions related to '{app_name}'.")

                # Delete admin logs
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM django_admin_log WHERE content_type_id IN ("
                        "SELECT id FROM django_content_type WHERE app_label = %s);",
                        [app_name]
                    )
                    self.stdout.write(f"Deleted {cursor.rowcount} admin log entries for '{app_name}'.")

                # Delete content types
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM django_content_type WHERE app_label = %s;", [app_name])
                    self.stdout.write(f"Deleted {cursor.rowcount} content types for '{app_name}'.")

                # Delete migrations
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM django_migrations WHERE app = %s;", [app_name])
                    self.stdout.write(f"Deleted {cursor.rowcount} migration entries for '{app_name}'.")
            except Exception as e:
                raise CommandError(f"Database cleanup failed for '{app_name}': {e}")

    def _drop_app_tables(self, app_name):
        try:
            with connection.cursor() as cursor:
                # Disable foreign key checks
                if connection.vendor == 'sqlite':
                    cursor.execute("PRAGMA foreign_keys=OFF;")
                elif connection.vendor in ['postgresql', 'mysql']:
                    cursor.execute("SET session_replication_role = 'replica';")  # PostgreSQL
                    # MySQL: Use "SET FOREIGN_KEY_CHECKS=0;"

                # Drop tables
                app_tables = self._get_app_tables(app_name)
                for table in app_tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table};")
                    self.stdout.write(f"Dropped table: {table}")

                # Re-enable foreign key checks
                if connection.vendor == 'sqlite':
                    cursor.execute("PRAGMA foreign_keys=ON;")
                elif connection.vendor in ['postgresql', 'mysql']:
                    cursor.execute("SET session_replication_role = 'origin';")  # PostgreSQL
                    # MySQL: Use "SET FOREIGN_KEY_CHECKS=1;"
        except Exception as e:
            raise CommandError(f"Failed to drop tables for '{app_name}': {e}")

    def _get_app_tables(self, app_name):
        app_models = apps.get_app_config(app_name).get_models()
        existing_tables = connection.introspection.table_names()
        app_tables = [model._meta.db_table for model in app_models if model._meta.db_table in existing_tables]
        return app_tables
