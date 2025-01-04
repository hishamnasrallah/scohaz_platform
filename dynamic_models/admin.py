from django.contrib import admin
from django.db import transaction
from dynamic_models.models import DynamicModel, DynamicField
from dynamic_models.utils.utils import apply_schema_changes_for_model, delete_table_for_model


class DynamicFieldInline(admin.TabularInline):
    model = DynamicField
    extra = 1

    def save_new_objects(self, formset):
        """
        Save inline objects before they are validated.
        """
        for form in formset.initial_forms + formset.extra_forms:
            if form.instance.pk is None:
                form.instance.save()

    def save_formset(self, request, form, formset, change):
        """
        Save inlines after ensuring their parent instance is saved.
        """
        with transaction.atomic():
            # Save new objects to avoid validation errors
            self.save_new_objects(formset)
            formset.save()


@admin.register(DynamicModel)
class DynamicModelAdmin(admin.ModelAdmin):
    inlines = [DynamicFieldInline]
    actions = ['apply_and_initialize_commands']

    def save_model(self, request, obj, form, change):
        """
        Save the parent model explicitly before the inlines.
        """
        if not obj.pk:
            obj.save()

        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        """
        Save related inline objects after the parent model has been saved.
        """
        with transaction.atomic():
            form.save(commit=True)
            for formset in formsets:
                formset.save()

    def delete_model(self, request, obj):
        """
        Safely delete a model and its associated database table.
        """
        try:
            # Delete the database table
            delete_table_for_model(obj.get_dynamic_model_class())
            super().delete_model(request, obj)
            self.message_user(request, f"Model '{obj.name}' and its table deleted successfully.")
        except Exception as e:
            self.message_user(request, f"Error deleting model '{obj.name}': {e}", level='error')

    def apply_and_initialize_commands(self, request, queryset):
        """
        Admin action to initialize and apply schema changes.
        """
        try:
            for dynamic_model in queryset:
                apply_schema_changes_for_model(dynamic_model)
            self.message_user(request, "Schema changes applied successfully.")
        except Exception as e:
            self.message_user(request, f"Error applying schema changes: {e}", level='error')

    apply_and_initialize_commands.short_description = "Apply Schema Changes for Selected Models"
