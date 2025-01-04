from django.contrib import admin
from django.db import transaction
from dynamic_models.models import DynamicModel, DynamicField
from dynamic_models.utils.utils import apply_schema_changes_for_model, delete_table_for_model


class DynamicFieldInline(admin.TabularInline):
    model = DynamicField
    extra = 1


@admin.register(DynamicModel)
class DynamicModelAdmin(admin.ModelAdmin):
    inlines = [DynamicFieldInline]
    actions = ['apply_and_initialize_commands']

    def save_model(self, request, obj, form, change):
        """
        Save the parent DynamicModel instance first.
        """
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        """
        Save the inline DynamicField forms after the DynamicModel has been saved.
        """
        with transaction.atomic():
            # Ensure the parent model is saved before saving the inline forms
            form.instance.save()
            formset.save()

            # Apply schema changes for the updated model
            apply_schema_changes_for_model(form.instance)

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
        try:
            # Apply schema changes directly for selected models
            for dynamic_model in queryset:
                apply_schema_changes_for_model(dynamic_model)

            self.message_user(request, "Commands executed successfully.")
        except Exception as e:
            self.message_user(request, f"Error executing commands: {e}", level='error')

    apply_and_initialize_commands.short_description = "Run Initialize and Apply Schema Changes"
