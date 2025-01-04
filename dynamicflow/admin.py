from django.contrib import admin
from dynamicflow.models import Page, Category, Field, FieldType, Condition
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe

# Register your models here.

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    # raw_id_fields = ['service_flow',]
    ordering = ['sequence_number']
    list_display = ('sequence_number', 'service_name',
                    'applicant_type', 'name', 'name_ara', 'active_ind')
    # radio_fields = ('multiple_services_ind',)
    raw_id_fields = ('service', 'sequence_number', 'applicant_type')

    def service_name(self, obj):
        try:
            name = obj.service.name
        except AttributeError:
            name = None
        return name


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    ordering = ['name']
    list_display = ('name', 'name_ara', 'code', 'description', 'active_ind')
    filter_horizontal = ('page',)


class ConditionInline(admin.TabularInline):
    model = Condition
    extra = 1
    fields = ('target_field', 'active_ind', 'condition_logic', 'preview_condition_logic')
    readonly_fields = ('preview_condition_logic',)

    # Method to preview the condition logic
    def preview_condition_logic(self, obj):
        if obj.pk:  # Only render for existing conditions
            try:
                logic_preview = "<br>".join([f"<strong>Field:</strong> {cond.get('field', 'N/A')} <strong>Operation:</strong> {cond.get('operation', 'N/A')} <strong>Value:</strong> {cond.get('value', 'N/A')}" for cond in obj.condition_logic])
                return mark_safe(logic_preview)
            except Exception as e:
                return f"Error rendering logic: {e}"
        return "Save the condition to preview the logic."

    preview_condition_logic.short_description = "Condition Logic Preview"


@admin.register(Field)
class FieldFlowAdmin(admin.ModelAdmin):
    fieldsets = (
        # Basic Field Information
        (_('Field Information'), {
            'fields': (
                ('_field_type', 'service', '_lookup'),
                '_field_name',
                '_parent_field',
                ('_field_display_name', '_field_display_name_ara', '_sequence'),
                '_category',
            )
        }),

        # Text Validators
        (_('Text Validators'), {
            'fields': (
                ('_max_length', '_min_length'),
                '_regex_pattern',
                '_allowed_characters',
                '_forbidden_words',
                '_unique',
            )
        }),

        # Number Validators
        (_('Number Validators'), {
            'fields': (
                ('_value_greater_than', '_value_less_than'),
                '_integer_only',
                '_positive_only',
            )
        }),

        # Date Validators
        (_('Date Validators'), {
            'fields': (
                ('_date_greater_than', '_date_less_than'),
                '_future_only',
                '_past_only',
            )
        }),

        # Boolean Validators
        (_('Boolean Validators'), {
            'fields': (
                '_default_boolean',
            )
        }),

        # File Validators
        (_('File Validators'), {
            'fields': (
                '_file_types',
                '_max_file_size',
            )
        }),

        # Image Validators
        (_('Image Validators'), {
            'fields': (
                '_image_max_width',
                '_image_max_height',
            )
        }),

        # Choice Validators
        (_('Choice Validators'), {
            'fields': (
                'allowed_lookups',
                ('_max_selections', '_min_selections'),
            )
        }),

        # Advanced Validators
        (_('Advanced Validators'), {
            'fields': (
                '_precision',
                '_default_value',
                '_coordinates_format',
                '_uuid_format',
            )
        }),

        # Visibility and Control
        (_('Visibility and Control'), {
            'fields': (
                '_mandatory',
                '_is_hidden',
                '_is_disabled',
                'active_ind',
            )
        }),
    )

    filter_horizontal = ('_category', 'service', 'allowed_lookups')

    list_display = (
        '_sequence', '_field_name', '_field_display_name',
        '_field_display_name_ara', '_field_type', '_lookup',
        '_is_hidden', '_is_disabled'
    )

    inlines = (ConditionInline, )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "_parent_field":
            obj_id = request.resolver_match.kwargs.get('object_id')
            if obj_id:
                # Exclude self and its descendants
                current_field = Field.objects.filter(id=obj_id).first()
                if current_field:
                    descendant_ids = current_field.get_descendant_ids()
                    kwargs["queryset"] = Field.objects.exclude(id__in=descendant_ids)
            else:
                kwargs["queryset"] = Field.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# Recursive function to fetch descendants
def get_descendant_ids(field):
    """
    Recursively fetch all descendant field IDs for a given field.
    """
    descendant_ids = {field.id}
    for subfield in field.sub_fields.all():
        descendant_ids.update(get_descendant_ids(subfield))
    return descendant_ids


@admin.register(FieldType)
class FieldTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_ara', 'code', 'active_ind']


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('target_field', 'active_ind', 'target_field', 'preview_condition_logic')
    list_filter = ('target_field', 'target_field')
    search_fields = ('target_field___field_name', 'condition_logic')
    ordering = ('target_field___field_name',)

    # Method to preview the condition logic in a readable format
    def preview_condition_logic(self, obj):
        try:
            logic_preview = "<br>".join([f"<strong>Field:</strong> {cond.get('field', 'N/A')} <strong>Operation:</strong> {cond.get('operation', 'N/A')} <strong>Value:</strong> {cond.get('value', 'N/A')}" for cond in obj.condition_logic])
            return mark_safe(logic_preview)
        except Exception as e:
            return f"Error rendering logic: {e}"

    preview_condition_logic.short_description = "Condition Logic Preview"

    # Override save_model to validate condition logic on save
    def save_model(self, request, obj, form, change):
        try:
            # Example validation to ensure valid structure for condition_logic
            if not isinstance(obj.condition_logic, list):
                raise ValidationError("Condition logic must be a list of conditions.")
            for condition in obj.condition_logic:
                if 'field' not in condition or 'operation' not in condition or 'value' not in condition:
                    raise ValidationError("Each condition must include 'field', 'operation', and 'value'.")
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            self.message_user(request, f"Error saving condition: {e.message}", level="error")

