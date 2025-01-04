from django.contrib import admin
from django.core.management import call_command
from dynamic_models.models import DynamicModel, DynamicField
from dynamic_models.utils.utils import sync_model_fields, delete_table_for_model
from dynamic_models.utils.database import disable_foreign_keys, enable_foreign_keys


class DynamicFieldInline(admin.TabularInline):
    model = DynamicField
    extra = 1


@admin.register(DynamicModel)
class DynamicModelAdmin(admin.ModelAdmin):
    inlines = [DynamicFieldInline]
    actions = ['apply_and_initialize_commands']

    def delete_model(self, request, obj):
        """
        Ensure schema changes are handled safely when deleting a model.
        """
        from dynamic_models.models import DynamicField

        # Disable foreign key constraints temporarily
        from dynamic_models.utils.database import disable_foreign_keys, enable_foreign_keys
        disable_foreign_keys()

        try:
            # Delete all related fields
            DynamicField.objects.filter(model=obj).delete()

            # Delete the database table
            delete_table_for_model(obj.get_dynamic_model_class())
        finally:
            enable_foreign_keys()

        # Proceed with the standard model deletion
        super().delete_model(request, obj)

    def apply_and_initialize_commands(self, request, queryset):
        """
        Admin action to initialize and apply schema changes.
        """
        from django.core.management import call_command

        try:
            call_command('initialize_dynamic_models')
            call_command('apply_dynamic_model_changes')
            self.message_user(request, "Commands executed successfully.")
        except Exception as e:
            self.message_user(request, f"Error executing commands: {e}", level='error')

    apply_and_initialize_commands.short_description = "Run Initialize and Apply Schema Changes"