from django.contrib import admin, messages
from dynamicflow.models import Workflow, WorkflowConnection, Page, Category, Field, FieldType, Condition
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.html import format_html

from integration.models import Integration


# Register your models here.

@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'version', 'is_active', 'is_draft', 'created_by', 'updated_at')
    list_filter = ('is_active', 'is_draft', 'service', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'service__name', 'service_code')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    raw_id_fields = ('service', 'created_by', 'updated_by')
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'service', 'service_code')
        }),
        (_('Status'), {
            'fields': ('is_active', 'is_draft', 'version')
        }),
        (_('Metadata'), {
            'fields': ('metadata', 'canvas_state'),
            'classes': ('collapse',)
        }),
        (_('Tracking'), {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(WorkflowConnection)
class WorkflowConnectionAdmin(admin.ModelAdmin):
    list_display = ('workflow', 'source_type', 'source_id', 'target_type', 'target_id')
    list_filter = ('workflow', 'source_type', 'target_type')
    search_fields = ('workflow__name',)
    raw_id_fields = ('workflow',)
    fieldsets = (
        (_('Connection Details'), {
            'fields': ('workflow', 'source_type', 'source_id', 'target_type', 'target_id', 'connection_metadata')
        }),
    )


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    ordering = ['sequence_number__code']
    list_display = ('sequence_number_code', 'service_name', 'applicant_type_name',
                    'name', 'name_ara', 'is_review_page', 'workflow', 'active_ind')
    list_filter = ('active_ind', 'workflow', 'service', 'applicant_type')
    search_fields = ('name', 'name_ara', 'description')
    raw_id_fields = ('service', 'sequence_number', 'applicant_type', 'workflow')
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                ('service', 'workflow', 'is_review_page'),
                ('sequence_number', 'applicant_type'),
                ('name', 'name_ara'),
                ('description', 'description_ara')
            )
        }),
        (_('Position and Display'), {
            'fields': (
                ('position_x', 'position_y'),
                'is_expanded',
                'active_ind'
            )
        }),
    )

    def service_name(self, obj):
        return obj.service.name if obj.service else '-'
    service_name.short_description = 'Service'

    def applicant_type_name(self, obj):
        return obj.applicant_type.name if obj.applicant_type else '-'
    applicant_type_name.short_description = 'Applicant Type'

    def sequence_number_code(self, obj):
        return obj.sequence_number.code if obj.sequence_number else '-'
    sequence_number_code.short_description = 'Sequence'
    sequence_number_code.admin_order_field = 'sequence_number__code'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    ordering = ['name']
    list_display = ('name', 'name_ara', 'code', 'is_repeatable', 'workflow', 'active_ind')
    list_filter = ('active_ind', 'is_repeatable', 'workflow')
    search_fields = ('name', 'name_ara', 'code', 'description')
    filter_horizontal = ('page',)
    raw_id_fields = ('workflow',)
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'workflow',
                ('name', 'name_ara'),
                'code',
                'description',
                'is_repeatable'
            )
        }),
        (_('Pages'), {
            'fields': ('page',)
        }),
        (_('Position and Status'), {
            'fields': (
                ('relative_position_x', 'relative_position_y'),
                'active_ind'
            )
        }),
    )


class ConditionInline(admin.TabularInline):
    model = Condition
    extra = 1
    fields = ('target_field', 'workflow', 'active_ind', 'condition_logic', 'preview_condition_logic')
    readonly_fields = ('preview_condition_logic',)
    raw_id_fields = ('workflow',)

    def preview_condition_logic(self, obj):
        if obj.pk and obj.condition_logic:
            try:
                logic_preview = "<br>".join([
                    f"<strong>Field:</strong> {cond.get('field', 'N/A')} "
                    f"<strong>Operation:</strong> {cond.get('operation', 'N/A')} "
                    f"<strong>Value:</strong> {cond.get('value', 'N/A')}"
                    for cond in obj.condition_logic
                ])
                return mark_safe(logic_preview)
            except Exception as e:
                return f"Error rendering logic: {e}"
        return "Save the condition to preview the logic."
    preview_condition_logic.short_description = "Condition Logic Preview"


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    fieldsets = (

        (_('Field Information'), {
            'fields': (
                'workflow',
                ('_field_type', 'service', '_lookup'),
                '_field_name',
                '_parent_field',
                ('_field_display_name', '_field_display_name_ara', '_sequence'),
                '_category',
            )
        }),
        (_('Integration Information'), {
            'fields': (
                '_api_call_config',
            )
        }),
        (_('Text Validators'), {
            'fields': (
                ('_max_length', '_min_length'),
                '_regex_pattern',
                '_allowed_characters',
                '_forbidden_words',
                '_unique',
            ),
            'classes': ('collapse',)
        }),
        (_('Number Validators'), {
            'fields': (
                ('_value_greater_than', '_value_less_than'),
                '_integer_only',
                '_positive_only',
                '_precision',
            ),
            'classes': ('collapse',)
        }),
        (_('Date Validators'), {
            'fields': (
                ('_date_greater_than', '_date_less_than'),
                '_future_only',
                '_past_only',
            ),
            'classes': ('collapse',)
        }),
        (_('Boolean Validators'), {
            'fields': (
                '_default_boolean',
            ),
            'classes': ('collapse',)
        }),
        (_('File Validators'), {
            'fields': (
                '_file_types',
                '_max_file_size',
            ),
            'classes': ('collapse',)
        }),
        (_('Image Validators'), {
            'fields': (
                '_image_max_width',
                '_image_max_height',
            ),
            'classes': ('collapse',)
        }),
        (_('Choice Validators'), {
            'fields': (
                'allowed_lookups',
                ('_max_selections', '_min_selections'),
            ),
            'classes': ('collapse',)
        }),
        (_('Advanced Validators'), {
            'fields': (
                '_default_value',
                '_coordinates_format',
                '_uuid_format',
            ),
            'classes': ('collapse',)
        }),
        (_('Visibility and Control'), {
            'fields': (
                '_mandatory',
                '_is_hidden',
                '_is_disabled',
                ('relative_position_x', 'relative_position_y'),
                'active_ind',
            )
        }),
    )

    filter_horizontal = ('_category', 'service', 'allowed_lookups')
    raw_id_fields = ('_field_type', '_lookup', '_parent_field', 'workflow')
    list_display = ('_field_name', '_field_display_name', '_field_type',
                    'get_service_names', '_mandatory', '_is_hidden', '_is_disabled',
                    'workflow', 'active_ind')
    list_filter = ('active_ind', '_mandatory', '_is_hidden', '_is_disabled',
                   '_field_type', 'workflow')
    search_fields = ('_field_name', '_field_display_name', '_field_display_name_ara')
    ordering = ('_sequence', '_field_name')
    actions = ['test_api_config']
    inlines = (ConditionInline,)

    @admin.action(description='Test API Configuration')
    def test_api_config(self, request, queryset):
        for field in queryset:
            if field._api_call_config:
                test_case_data = {field._field_name: "test_value"}

                for config in field._api_call_config:
                    try:
                        integration = Integration.objects.get(id=config['integration_id'])
                        self.message_user(
                            request,
                            f"✓ Configuration for {integration.name} is valid",
                            messages.SUCCESS
                        )
                    except Exception as e:
                        self.message_user(
                            request,
                            f"✗ Configuration error: {str(e)}",
                            messages.ERROR
                        )
    def get_service_names(self, obj):
        return ", ".join([s.name for s in obj.service.all()[:3]])
    get_service_names.short_description = 'Services'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "_parent_field":
            obj_id = request.resolver_match.kwargs.get('object_id')
            if obj_id:
                current_field = Field.objects.filter(id=obj_id).first()
                if current_field:
                    descendant_ids = current_field.get_descendant_ids()
                    descendant_ids.add(obj_id)  # Also exclude self
                    kwargs["queryset"] = Field.objects.exclude(id__in=descendant_ids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(FieldType)
class FieldTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_ara', 'code', 'active_ind')
    list_filter = ('active_ind',)
    search_fields = ('name', 'name_ara', 'code')
    ordering = ('name',)


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('target_field', 'workflow', 'active_ind', 'preview_condition_logic')
    list_filter = ('active_ind', 'workflow')
    search_fields = ('target_field___field_name',)
    ordering = ('target_field___field_name',)
    raw_id_fields = ('target_field', 'workflow')
    fieldsets = (
        (_('Condition Details'), {
            'fields': (
                'workflow',
                'target_field',
                'condition_logic',
                'active_ind'
            )
        }),
        (_('Position'), {
            'fields': (
                ('position_x', 'position_y'),
            )
        }),
    )

    def preview_condition_logic(self, obj):
        if obj.condition_logic:
            try:
                logic_preview = "<br>".join([
                    f"<strong>Field:</strong> {cond.get('field', 'N/A')} "
                    f"<strong>Operation:</strong> {cond.get('operation', 'N/A')} "
                    f"<strong>Value:</strong> {cond.get('value', 'N/A')}"
                    for cond in obj.condition_logic
                ])
                return format_html(logic_preview)
            except Exception as e:
                return f"Error rendering logic: {e}"
        return "-"
    preview_condition_logic.short_description = "Condition Logic Preview"

    def save_model(self, request, obj, form, change):
        try:
            if not isinstance(obj.condition_logic, list):
                raise ValidationError("Condition logic must be a list of conditions.")
            for condition in obj.condition_logic:
                if not all(key in condition for key in ['field', 'operation', 'value']):
                    raise ValidationError("Each condition must include 'field', 'operation', and 'value'.")
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            self.message_user(request, f"Error saving condition: {str(e)}", level="error")