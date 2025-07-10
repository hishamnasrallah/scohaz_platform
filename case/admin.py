import json

from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html

from .models import Case, ApprovalRecord, MapperFieldRule, MapperTarget, CaseMapper, MapperExecutionLog, \
    MapperFieldRuleLog
from lookup.models import Lookup
from .services import preview_mapping


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    # Define fields to display in the list view
    list_display = [
        'serial_number', 'applicant', 'applicant_type', 'case_type',
        'assigned_group', 'assigned_emp', 'status', 'sub_status',
        'created_at', 'updated_at'
    ]
    search_fields = ['serial_number', 'applicant__username',
                     'applicant_type__name', 'case_type__name', 'status__name']
    list_filter = ['applicant_type', 'case_type', 'status',
                   'assigned_group', 'assigned_emp']
    ordering = ('created_at',)
    date_hierarchy = 'created_at'
    actions = ['run_mapping']

    # Fields for the form in the admin (to display in the add/edit page)
    fields = [
        'applicant', 'applicant_type', 'case_type',
        'serial_number', 'assigned_group', 'assigned_emp',
        'current_approval_step', 'status', 'sub_status',
        'last_action', 'case_data', 'created_at', 'updated_at',
        'created_by', 'updated_by'
    ]
    readonly_fields = ['serial_number', 'created_at',
                       'updated_at', 'created_by', 'updated_by']

    # Inline configuration for related models (if needed)
    # Example: If you have a related model,
    # you can include an Inline (e.g., CaseHistoryInline)
    # inlines = [CaseHistoryInline]

    # Handling the "serial_number" field
    # (readonly and auto-generated on creation)
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    # Overriding the formfield for specific fields
    # like 'applicant_type', 'case_type', etc.
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'applicant_type':
            kwargs['queryset'] = Lookup.objects.filter(
                parent_lookup__name='Applicant Type')
        elif db_field.name == 'case_type':
            kwargs['queryset'] = Lookup.objects.filter(
                parent_lookup__name='Service')
        elif db_field.name == 'status':
            kwargs['queryset'] = Lookup.objects.filter(
                parent_lookup__name='Case Status')
        elif db_field.name == 'sub_status':
            kwargs['queryset'] = Lookup.objects.filter(
                parent_lookup__name='Case Sub Status')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # Optional: Search for specific fields in related models
    search_fields = ('serial_number', 'applicant__username',
                     'applicant_type__name', 'case_type__name', 'status__name')

    # Handle the readonly status for some fields
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['serial_number']
        return self.readonly_fields

    def run_mapping(self, request, queryset):
        from case.plugins.default_plugin import process_records
        for case in queryset:
            for target in MapperTarget.objects.filter(case_type=case.case_type):
                try:
                    process_records(case, target, found_object=None)
                except Exception as e:
                    self.message_user(request, f"❌ Error for Case {case.id}: {e}", level='error')
        self.message_user(request, "✅ Mapping executed.")
    run_mapping.short_description = "▶️ Run Mapping for Selected Cases"

@admin.register(ApprovalRecord)
class ApprovalRecordAdmin(admin.ModelAdmin):
    list_display = ('case', 'approval_step', 'action_taken',  'approved_by', 'approved_at')
    list_filter = ('approval_step__service_type', 'approved_by')
    search_fields = ('case__id', 'approval_step__service_type__name', 'approved_by__username')
    readonly_fields = ('approved_at',)
    fieldsets = (
        ('Approval Details', {
            'fields': ('case', 'approval_step', 'action_taken', 'approved_by')
        }),
        ('Timestamp', {
            'fields': ('approved_at',)
        }),
    )



# 1) An inline for MapperFieldRule under MapperTarget
class MapperFieldRuleInline(admin.TabularInline):
    model = MapperFieldRule
    extra = 1
    # You can customize fields, readonly_fields, etc. here if desired.

# 2) An inline for MapperTarget under CaseMapper
class MapperTargetInline(admin.TabularInline):
    model = MapperTarget
    extra = 1
    # You won't see MapperFieldRule here directly unless you do nested inlines
    # (which requires a 3rd-party library).

# 3) CaseMapper Admin
@admin.register(CaseMapper)
class CaseMapperAdmin(admin.ModelAdmin):
    list_display = ("name", "case_type", "version", "active_ind")
    search_fields = ("name", "case_type")
    readonly_fields = ("version", "parent")
    list_filter = ("case_type", "active_ind")
    inlines = [MapperTargetInline]

# 4) MapperTarget Admin
@admin.register(MapperTarget)
class MapperTargetAdmin(admin.ModelAdmin):
    list_display = (
        "case_mapper",
        "content_type",
        "finder_function_path",
        "processor_function_path",
        "preview_button",  # ✅ New
    )
    search_fields = ("finder_function_path", "processor_function_path")
    inlines = [MapperFieldRuleInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="case_mappertarget_preview",
            ),
        ]
        return custom_urls + urls

    def preview_button(self, obj):
        return format_html(
            '<a class="button" href="{}">🔍 Preview</a>',
            f"{obj.id}/preview/"
        )
    preview_button.short_description = "Preview"
    preview_button.allow_tags = True

    def preview_view(self, request, object_id):
        from case.models import MapperTarget, Case

        try:
            target = MapperTarget.objects.get(pk=object_id)
            case = Case.objects.filter(case_type=target.case_mapper.case_type).first()
            if not case:
                messages.warning(request, "No case found for this mapper to preview.")
                return redirect(request.META.get("HTTP_REFERER"))

            result = preview_mapping(case)
            return HttpResponse(
                f"<pre>{format_html(json.dumps(result, indent=2))}</pre>"
            )

        except Exception as e:
            messages.error(request, f"Error previewing: {str(e)}")
            return redirect(request.META.get("HTTP_REFERER"))
# 5) MapperFieldRule Admin
@admin.register(MapperFieldRule)
class MapperFieldRuleAdmin(admin.ModelAdmin):
    list_display = (
        "mapper_target",
        "target_field",
        "json_path",
        "transform_function_path",
        "source_lookup",
        "target_lookup",
    )
    search_fields = ("target_field", "json_path")

    def save_model(self, request, obj, form, change):
        obj.save(user=request.user)

@admin.register(MapperExecutionLog)
class MapperExecutionLogAdmin(admin.ModelAdmin):
    list_display = ('case', 'mapper_target', 'executed_at', 'success')
    list_filter = ('success', 'executed_at', 'mapper_target')
    search_fields = ('case__serial_number', 'mapper_target__id')
    readonly_fields = ('case', 'mapper_target', 'executed_at', 'success', 'result_data', 'error_trace')

    fieldsets = (
        (None, {
            'fields': ('case', 'mapper_target', 'executed_at', 'success')
        }),
        ('Details', {
            'fields': ('result_data', 'error_trace')
        }),
    )


@admin.register(MapperFieldRuleLog)
class MapperFieldRuleLogAdmin(admin.ModelAdmin):
    list_display = ('rule', 'user', 'changed_at')
    readonly_fields = ('rule', 'user', 'changed_at', 'old_data', 'new_data')
    search_fields = ('rule__target_field', 'user__username')
    list_filter = ('user', 'changed_at')
