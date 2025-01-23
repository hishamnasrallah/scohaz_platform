from django.contrib import admin
from .models import Case, ApprovalRecord, MapperFieldRule, MapperTarget, CaseMapper
from lookup.models import Lookup


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


@admin.register(ApprovalRecord)
class ApprovalRecordAdmin(admin.ModelAdmin):
    list_display = ('case', 'approval_step', 'approved_by', 'approved_at')
    list_filter = ('approval_step__service_type', 'approved_by')
    search_fields = ('case__id', 'approval_step__service_type__name', 'approved_by__username')
    readonly_fields = ('approved_at',)
    fieldsets = (
        ('Approval Details', {
            'fields': ('case', 'approval_step', 'approved_by')
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
    list_display = ("name", "case_type")
    search_fields = ("name", "case_type")
    inlines = [MapperTargetInline]

# 4) MapperTarget Admin
@admin.register(MapperTarget)
class MapperTargetAdmin(admin.ModelAdmin):
    list_display = (
        "case_mapper",
        "content_type",
        "finder_function_path",
        "processor_function_path",
    )
    search_fields = ("finder_function_path", "processor_function_path")
    inlines = [MapperFieldRuleInline]

# 5) MapperFieldRule Admin
@admin.register(MapperFieldRule)
class MapperFieldRuleAdmin(admin.ModelAdmin):
    list_display = (
        "mapper_target",
        "target_field",
        "json_path",
        "transform_function_path",
    )
    search_fields = ("target_field", "json_path")