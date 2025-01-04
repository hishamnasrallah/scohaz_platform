import os
import shutil
from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

class Command(BaseCommand):
    help = 'Delete a Django app dynamically'

    def add_arguments(self, parser):
        parser.add_argument('app_name', type=str, help='Name of the app to delete')

    def handle(self, *args, **kwargs):
        app_name = kwargs['app_name']

        if not app_name.isidentifier():
            raise CommandError(f"Invalid app name: {app_name}")

        # Step 1: Remove app folder
        app_path = os.path.join(settings.BASE_DIR, app_name)
        if os.path.exists(app_path):
            shutil.rmtree(app_path)
            self.stdout.write(self.style.SUCCESS(f"Removed app folder: {app_path}"))
        else:
            self.stdout.write(self.style.WARNING(f"App folder '{app_path}' does not exist."))

        # Step 2: Remove app from CUSTOM_APPS in settings
        settings_file_path = os.path.join(settings.BASE_DIR, 'scohaz_platform', 'settings', 'settings.py')
        if os.path.exists(settings_file_path):
            with open(settings_file_path, 'r') as f:
                settings_content = f.read()

            updated_content = settings_content.replace(f"    '{app_name}',\n", '')

            with open(settings_file_path, 'w') as f:
                f.write(updated_content)

            self.stdout.write(self.style.SUCCESS(f"Removed '{app_name}' from CUSTOM_APPS in settings."))
        else:
            self.stdout.write(self.style.WARNING("Could not find settings.py to update CUSTOM_APPS."))

        # Step 3: Delete permissions related to the app
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM auth_permission WHERE content_type_id IN ("
                "SELECT id FROM django_content_type WHERE app_label = %s);",
                [app_name]
            )
            deleted_permissions = cursor.rowcount
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_permissions} permissions related to '{app_name}'."))

        # Step 3: Remove middleware entries associated with the app
        middleware_removed = self.remove_middleware(app_name, settings_file_path)
        if middleware_removed:
            self.stdout.write(self.style.SUCCESS(f"Removed middleware entries for '{app_name}'."))


        # Step 4: Delete admin logs related to the app
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM django_admin_log WHERE content_type_id IN ("
                "SELECT id FROM django_content_type WHERE app_label = %s);",
                [app_name]
            )
            deleted_admin_logs = cursor.rowcount
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_admin_logs} admin log entries related to '{app_name}'."))

        # Step 5: Delete content types related to the app
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM django_content_type WHERE app_label = %s;", [app_name])
            deleted_content_types = cursor.rowcount
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_content_types} content types related to '{app_name}'."))

        # Step 6: Delete migration entries related to the app
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM django_migrations WHERE app = %s;", [app_name])
            deleted_migrations = cursor.rowcount
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_migrations} migration entries for '{app_name}' from django_migrations table."))

        # Step 8: Drop all tables created by the app
        try:
            with connection.cursor() as cursor:
                # Disable foreign key checks (SQLite, PostgreSQL, MySQL, etc.)
                if connection.vendor == 'sqlite':
                    cursor.execute("PRAGMA foreign_keys=OFF;")
                elif connection.vendor in ['postgresql', 'mysql']:
                    cursor.execute("SET session_replication_role = 'replica';")  # PostgreSQL
                    # For MySQL, you may use "SET FOREIGN_KEY_CHECKS=0;"

                # Identify tables using `db_table` or default naming convention
                model_tables = self.get_app_tables(app_name)
                for table in model_tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    self.stdout.write(self.style.SUCCESS(f"Dropped table: {table}"))

                # Re-enable foreign key checks
                if connection.vendor == 'sqlite':
                    cursor.execute("PRAGMA foreign_keys=ON;")
                elif connection.vendor in ['postgresql', 'mysql']:
                    cursor.execute("SET session_replication_role = 'origin';")  # PostgreSQL
                    # For MySQL, you may use "SET FOREIGN_KEY_CHECKS=1;"

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to drop tables for '{app_name}': {e}"))


        self.stdout.write(self.style.SUCCESS(f"App '{app_name}' deleted successfully."))


    def remove_middleware(self, app_name, settings_file_path):
        """
        Remove middleware entries associated with the app from settings.py.
        """
        if not os.path.exists(settings_file_path):
            self.stdout.write(self.style.WARNING("Could not find settings.py to update MIDDLEWARE."))
            return False

        with open(settings_file_path, 'r') as f:
            settings_content = f.readlines()

        # Remove middleware entries related to the app
        updated_content = []
        middleware_removed = False
        for line in settings_content:
            if f"{app_name}.middleware" in line:
                middleware_removed = True
            else:
                updated_content.append(line)

        # Write the updated settings back to the file
        if middleware_removed:
            with open(settings_file_path, 'w') as f:
                f.writelines(updated_content)

        return middleware_removed

    def get_app_tables(self, app_name):
        """
        Identify all tables associated with the app, accounting for custom db_table values.
        Supports SQLite, PostgreSQL, Oracle, and SQL Server.
        """
        app_models = apps.get_app_config(app_name).get_models()
        model_tables = []

        # Get the database backend
        db_backend = connection.settings_dict["ENGINE"]

        # Fetch all existing tables from the database
        with connection.cursor() as cursor:
            if "sqlite3" in db_backend:
                # SQLite query to list all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            elif "postgresql" in db_backend:
                # PostgreSQL query to list all tables
                cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public';")
            elif "oracle" in db_backend:
                # Oracle query to list all tables
                cursor.execute("SELECT table_name FROM user_tables;")
            elif "mysql" in db_backend:
                # MySQL query to list all tables
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE();")
            elif "microsoft" in db_backend:  # SQL Server
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE';")
            else:
                raise CommandError(f"Unsupported database backend: {db_backend}")

            existing_tables = {row[0] for row in cursor.fetchall()}

        # Determine the tables created by the app
        for model in app_models:
            meta = model._meta

            # Use the custom db_table if provided; otherwise, default naming convention
            table_name = meta.db_table if meta.db_table else f"{app_name}_{meta.model_name}"
            if table_name in existing_tables:
                model_tables.append(table_name)

        return model_tables
