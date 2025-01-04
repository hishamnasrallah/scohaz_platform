import os
import json
from time import time
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.apps import apps
from django.conf import settings
from django.db import connection


APP_COUNT = 5  # Increase this for scalability testing
MODEL_DEFINITIONS = {
    "name": "TestModel",
    "fields": [
        {"name": "name", "type": "CharField", "options": "max_length=100"},
        {"name": "description", "type": "TextField", "options": "blank=True, null=True"},
        {"name": "created_at", "type": "DateTimeField", "options": "auto_now_add=True"}
    ],
    "meta": {
        "verbose_name": "'Test Model'",
        "verbose_name_plural": "'Test Models'",
        "ordering": "['-created_at']"
    }
}


class Command(BaseCommand):
    help = "Run scalability tests for dynamic applications"

    def handle(self, *args, **kwargs):
        created_apps = []
        log_file = "scalability_test.log"

        with open(log_file, "w") as log:
            log.write("Scalability Test Log\n")
            log.write("=" * 40 + "\n")

            # 1. Create Apps
            for i in range(APP_COUNT):
                app_name = f"test_app_{i}"
                start_time = time()
                if self.create_app(app_name):
                    created_apps.append(app_name)
                    elapsed_time = time() - start_time
                    log.write(f"Created {app_name} in {elapsed_time:.2f} seconds\n")

            # 2. Modify Apps
            for app_name in created_apps:
                start_time = time()
                self.modify_app(app_name)
                elapsed_time = time() - start_time
                log.write(f"Modified {app_name} in {elapsed_time:.2f} seconds\n")

            # 3. Delete Apps
            for app_name in created_apps:
                start_time = time()
                self.delete_app(app_name)
                elapsed_time = time() - start_time
                log.write(f"Deleted {app_name} in {elapsed_time:.2f} seconds\n")

            log.write("Scalability Test Completed\n")
            log.write("=" * 40 + "\n")

        self.stdout.write(self.style.SUCCESS("Scalability test completed. Logs saved to scalability_test.log."))

    def create_app(self, app_name):
        models_file = f"{app_name}_models.json"
        with open(models_file, "w") as f:
            json.dump([MODEL_DEFINITIONS], f, indent=4)

        try:
            self.stdout.write(f"Creating app: {app_name}")
            call_command("create_app", app_name, models_file=models_file)
            os.remove(models_file)

            # Refresh app registry
            self.refresh_app_registry()

            # Generate and apply migrations
            call_command("makemigrations", app_name)
            call_command("migrate", app_name)

            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to create app {app_name}: {e}"))
            if os.path.exists(models_file):
                os.remove(models_file)
            return False

    def modify_app(self, app_name):
        models_file = f"{app_name}_models_modified.json"
        modified_model = MODEL_DEFINITIONS.copy()
        modified_model["fields"].append(
            {"name": "status", "type": "CharField", "options": "max_length=50, default='Active'"}
        )
        with open(models_file, "w") as f:
            json.dump([modified_model], f, indent=4)

        try:
            self.stdout.write(f"Modifying app: {app_name}")
            self.delete_app(app_name)  # Ensure the app is fully deleted before recreating
            call_command("create_app", app_name, models_file=models_file)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to modify app {app_name}: {e}"))
        finally:
            os.remove(models_file)

    def delete_app(self, app_name):
        """Delete an app by removing its folder, cleaning settings, dropping tables, and refreshing the app registry."""
        try:
            self.stdout.write(f"Deleting app: {app_name}")

            # Step 1: Call the standalone delete_app command
            call_command("delete_app", app_name)

            # Step 2: Refresh app registry after deletion
            self.refresh_app_registry()

            self.stdout.write(self.style.SUCCESS(f"App '{app_name}' deleted successfully."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to delete app '{app_name}': {e}"))

    def refresh_app_registry(self):
        """Refresh Django's app registry to reflect changes."""
        from django.apps import apps
        try:
            apps.clear_cache()
            apps.all_models.clear()
            apps.populate(settings.INSTALLED_APPS)
            self.stdout.write(self.style.SUCCESS("App registry refreshed."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to refresh app registry: {e}"))

