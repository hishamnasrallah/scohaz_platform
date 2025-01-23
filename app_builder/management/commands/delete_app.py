import os
import shutil
from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction, IntegrityError, models


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
        """
        Remove references to the app from settings.py, including APPS_CURRENT_USER_MIDDLEWARE
        and APP_MIDDLEWARE_MAPPING.
        """
        import os

        settings_file_path = os.path.join(settings.BASE_DIR, 'scohaz_platform', 'settings', 'settings.py')
        if not os.path.exists(settings_file_path):
            self.stdout.write(self.style.WARNING("Could not find settings.py to update."))
            return

        with open(settings_file_path, 'r') as f:
            settings_content = f.readlines()

        updated_content = []
        in_app_middleware_mapping = False
        in_target_mapping_block = False
        in_user_middleware = False
        in_custom_apps = False

        for line in settings_content:
            # Handle APP_MIDDLEWARE_MAPPING cleanup
            if line.strip().startswith("APP_MIDDLEWARE_MAPPING = {"):
                in_app_middleware_mapping = True

            if in_app_middleware_mapping:
                if line.strip().startswith(f'"{app_name}": [') or line.strip().startswith(f"'{app_name}': ["):
                    # Begin skipping the entire app block
                    in_target_mapping_block = True
                    continue
                if in_target_mapping_block:
                    # Skip all lines until the block ends
                    if line.strip() == "],":
                        in_target_mapping_block = False
                        continue
                    continue
                if line.strip() == "],":  # End of APP_MIDDLEWARE_MAPPING
                    in_app_middleware_mapping = False

            # Handle APPS_CURRENT_USER_MIDDLEWARE cleanup
            if line.strip().startswith("APPS_CURRENT_USER_MIDDLEWARE = ["):
                in_user_middleware = True

            if in_user_middleware:
                if f"'{app_name}.middleware.CurrentUserMiddleware'," in line:
                    # Skip the CurrentUserMiddleware entry for the given app_name
                    continue
                if line.strip() == "]":  # End of APPS_CURRENT_USER_MIDDLEWARE
                    in_user_middleware = False

            # Handle CUSTOM_APPS cleanup
            if line.strip().startswith("CUSTOM_APPS = ["):
                in_custom_apps = True

            if in_custom_apps:
                if f"'{app_name}'," in line:
                    # Skip the CUSTOM_APPS entry for the given app_name
                    continue
                if line.strip() == "]":  # End of CUSTOM_APPS
                    in_custom_apps = False
            # Add non-skipped lines to the updated content
            updated_content.append(line)

        # Write updated content back to settings.py
        with open(settings_file_path, 'w') as f:
            f.writelines(updated_content)

        self.stdout.write(self.style.SUCCESS(f"Removed '{app_name}' references from settings."))


    def _cleanup_database(self, app_name):
        """
        Cleans up database records for a specified app.
        Deletes all related admin logs, permissions, and content types in the correct order.
        """
        with transaction.atomic():
            try:
                # 1. Delete admin logs
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM django_admin_log WHERE content_type_id IN ("
                        "SELECT id FROM django_content_type WHERE app_label = %s);",
                        [app_name]
                    )
                    self.stdout.write(f"Deleted {cursor.rowcount} admin log entries for '{app_name}'.")

                # 2. Delete group permissions
                with connection.cursor() as cursor:
                    cursor.execute("""
                    DELETE FROM auth_group_permissions
                    WHERE permission_id IN (SELECT id FROM auth_permission
                    WHERE content_type_id IN (SELECT id FROM django_content_type WHERE app_label = %s));
                    """, [app_name])
                    self.stdout.write(f"Deleted {cursor.rowcount} group permissions entries for '{app_name}'.")

                # 3. Delete permissions
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM auth_permission WHERE content_type_id IN ("
                        "SELECT id FROM django_content_type WHERE app_label = %s);",
                        [app_name]
                    )
                    self.stdout.write(f"Deleted {cursor.rowcount} permissions related to '{app_name}'.")

                # 7. Delete content types
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM django_content_type WHERE app_label = %s;", [app_name])
                    self.stdout.write(f"Deleted {cursor.rowcount} content types for '{app_name}'.")

                # 4. Delete CRUDPermission rows
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM authentication_crudpermission
                        WHERE content_type_id NOT IN (
                        SELECT id FROM django_content_type);"""
                    )
                    self.stdout.write(f"Deleted {cursor.rowcount} CRUDPermission entries for '{app_name}'.")

                # 5. Clean user permissions
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM authentication_customuser_user_permissions
                        WHERE customuser_id NOT IN (SELECT id FROM authentication_customuser)
                        OR permission_id NOT IN (SELECT id FROM auth_permission);
                        """
                    )
                    self.stdout.write(f"Deleted {cursor.rowcount} user permissions entries from 'authentication_customuser_user_permissions'.")

                # 6. Delete migrations (Optional)
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM django_migrations WHERE app = %s;", [app_name])
                    self.stdout.write(f"Deleted {cursor.rowcount} migration entries for '{app_name}'.")

            except IntegrityError as e:
                self.stdout.write(f"IntegrityError: {str(e)}")
                raise CommandError(f"ForeignKey constraint issue during cleanup of '{app_name}'. "
                                   "Inspect the database for dependent records.")
            except Exception as e:
                raise CommandError(f"Database cleanup failed for '{app_name}': {e}")


    def get_local_model_tables(self, app_name):
        """All DB tables owned by models in this app."""
        local_models = apps.get_app_config(app_name).get_models()
        local_tables = {m._meta.db_table for m in local_models}
        return local_tables

    def get_all_model_tables(self):
        """
        All DB tables owned by models in *any* installed app.
        (useful so we know which tables correspond to actual Django models)
        """
        all_tables = set()
        for app in apps.get_app_configs():
            for m in app.get_models():
                all_tables.add(m._meta.db_table)
        return all_tables

    def _drop_app_tables(self, app_name):
        try:
            with connection.cursor() as cursor:
                # Disable foreign key checks
                if connection.vendor == 'sqlite':
                    cursor.execute("PRAGMA foreign_keys=OFF;")
                elif connection.vendor == 'postgresql':
                    cursor.execute("SET session_replication_role = 'replica';")
                elif connection.vendor == 'mysql':
                    cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

                # 1. Gather the tables your app owns (via Django model introspection)
                app_tables = self._get_app_tables(app_name)

                # 2. Detect cross-app M2M join tables
                cross_app_m2m = self.find_suspected_m2m_tables(app_name)

                # 3. Drop them all
                all_tables = set(app_tables) | set(cross_app_m2m)
                for table in all_tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table};")
                    self.stdout.write(f"Dropped table: {table}")

                # Re-enable foreign key checks
                if connection.vendor == 'sqlite':
                    cursor.execute("PRAGMA foreign_keys=ON;")
                elif connection.vendor == 'postgresql':
                    cursor.execute("SET session_replication_role = 'origin';")
                elif connection.vendor == 'mysql':
                    cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

        except Exception as e:
            raise CommandError(f"Failed to drop tables for '{app_name}': {e}")

    def get_fk_references(self, table_name):
        """
        Return a set of all tables that `table_name` references via foreign keys.
        Works around the lack of or incomplete `get_constraints(...)` method
        by doing raw SQL on each backend.
        """
        with connection.cursor() as cursor:
            vendor = connection.vendor

            if vendor == 'sqlite':
                # Each row of PRAGMA foreign_key_list has schema:
                # (id, seq, table, from, to, on_update, on_delete, match)
                # 'table' is the referenced table name
                cursor.execute(f"PRAGMA foreign_key_list({table_name});")
                rows = cursor.fetchall()
                return {row[2] for row in rows}  # row[2] = the referenced table name

            elif vendor == 'mysql':
                # MySQL: Use INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                # to find rows where REFERENCED_TABLE_NAME is set
                cursor.execute("""
                    SELECT REFERENCED_TABLE_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = %s
                      AND REFERENCED_TABLE_NAME IS NOT NULL;
                """, [table_name])
                rows = cursor.fetchall()
                return {row[0] for row in rows}  # row[0] = the referenced table name

            elif vendor == 'postgresql':
                # PostgreSQL: Use information_schema to find FKs
                cursor.execute("""
                    SELECT ccu.table_name AS referenced_table
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.constraint_column_usage ccu
                         ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_name = tc.table_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                      AND tc.table_name = %s;
                """, [table_name])
                rows = cursor.fetchall()
                return {row[0] for row in rows}

            else:
                # Other DB engines or older Django versions:
                raise NotImplementedError(
                    f"FK introspection not implemented for DB vendor '{vendor}'. "
                    "You may need a custom approach."
                )

    def find_suspected_m2m_tables(self, app_name):
        """
        Inspect all tables in the database. If a table is *not* recognized as a
        normal model table, but references exactly 2 distinct tables via FKs (one
        of which belongs to app_name), we suspect it is an auto-created M2M table.
        """
        from django.apps import apps

        local_models = apps.get_app_config(app_name).get_models()
        local_tables = {m._meta.db_table for m in local_models}  # belongs to our app
        all_tables = connection.introspection.table_names()

        # Optionally gather every known Django model table across all apps:
        known_model_tables = set()
        for app in apps.get_app_configs():
            for model in app.get_models():
                known_model_tables.add(model._meta.db_table)

        suspected_m2m = []

        for table in all_tables:
            # If it's already recognized as a known model table, skip it
            if table in known_model_tables:
                continue

            # Try to see which tables this table references
            try:
                fk_targets = self.get_fk_references(table)
            except NotImplementedError:
                continue

            # If it references exactly 2 distinct tables, and at least one is local...
            if len(fk_targets) == 2 and (fk_targets & local_tables):
                suspected_m2m.append(table)

        return suspected_m2m

    def _drop_app_tables(self, app_name):
        """
        Drops all recognized tables for the given app,
        plus any 'suspected' M2M tables crossing to other apps.
        """
        try:
            with connection.cursor() as cursor:
                # Disable foreign key checks
                if connection.vendor == 'sqlite':
                    cursor.execute("PRAGMA foreign_keys=OFF;")
                elif connection.vendor == 'postgresql':
                    cursor.execute("SET session_replication_role = 'replica';")
                elif connection.vendor == 'mysql':
                    cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

                # Gather known local tables (normal models + direct M2Ms)
                app_tables = self._get_app_tables(app_name)

                # Also find any 'suspected' cross-app M2M tables
                cross_app_m2m_tables = self.find_suspected_m2m_tables(app_name)

                # Combine them
                all_tables_to_drop = set(app_tables).union(cross_app_m2m_tables)

                for table in all_tables_to_drop:
                    cursor.execute(f"DROP TABLE IF EXISTS {table};")
                    self.stdout.write(f"Dropped table: {table}")

                # Re-enable foreign key checks
                if connection.vendor == 'sqlite':
                    cursor.execute("PRAGMA foreign_keys=ON;")
                elif connection.vendor == 'postgresql':
                    cursor.execute("SET session_replication_role = 'origin';")
                elif connection.vendor == 'mysql':
                    cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

        except Exception as e:
            raise CommandError(f"Failed to drop tables for '{app_name}': {e}")

    def _get_app_tables(self, app_name):
        """
        Retrieves all tables for the given app, including many-to-many intermediate tables.
        """
        app_models = apps.get_app_config(app_name).get_models()
        existing_tables = connection.introspection.table_names()

        # Collect model tables
        app_tables = [model._meta.db_table for model in app_models if model._meta.db_table in existing_tables]
        return app_tables
