from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count

from reporting.models import (
    Report, ReportDataSource, ReportField, ReportFilter,
    ReportJoin, ReportParameter, ReportExecution, ReportSchedule,
    SavedReportResult
)


class ReportDataSourceInline(admin.TabularInline):
    model = ReportDataSource
    extra = 0
    fields = ['app_name', 'model_name', 'alias', 'is_primary']


class ReportFieldInline(admin.TabularInline):
    model = ReportField
    extra = 0
    fields = ['data_source', 'field_path', 'display_name', 'field_type',
              'aggregation', 'order', 'is_visible']
    readonly_fields = ['field_type']


class ReportFilterInline(admin.TabularInline):
    model = ReportFilter
    extra = 0
    fields = ['data_source', 'field_path', 'operator', 'value',
              'value_type', 'logic_group', 'is_active']


class ReportParameterInline(admin.TabularInline):
    model = ReportParameter
    extra = 0
    fields = ['name', 'display_name', 'parameter_type', 'is_required',
              'default_value', 'order']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'category', 'is_active', 'is_public',
                    'created_by', 'created_at', 'field_count', 'execution_count',
                    'actions_column']
    list_filter = ['report_type', 'is_active', 'is_public', 'category',
                   'created_at', 'created_by']
    search_fields = ['name', 'description', 'tags']
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    filter_horizontal = ['shared_with_users', 'shared_with_groups']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'report_type', 'category', 'tags')
        }),
        ('Status', {
            'fields': ('is_active', 'is_public')
        }),
        ('Sharing', {
            'fields': ('shared_with_users', 'shared_with_groups')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Advanced Configuration', {
            'fields': ('config',),
            'classes': ('collapse',)
        }),
    )

    inlines = [ReportDataSourceInline, ReportFieldInline,
               ReportFilterInline, ReportParameterInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _field_count=Count('fields'),
            _execution_count=Count('executions')
        )
        return queryset

    def field_count(self, obj):
        return obj._field_count
    field_count.short_description = 'Fields'
    field_count.admin_order_field = '_field_count'

    def execution_count(self, obj):
        return obj._execution_count
    execution_count.short_description = 'Executions'
    execution_count.admin_order_field = '_execution_count'

    def actions_column(self, obj):
        return format_html(
            '<a class="button" href="{}">Execute</a>&nbsp;'
            '<a class="button" href="{}">Duplicate</a>',
            reverse('admin:reporting_report_execute', args=[obj.pk]),
            reverse('admin:reporting_report_duplicate', args=[obj.pk])
        )
    actions_column.short_description = 'Actions'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ['created_by']
        return self.readonly_fields


@admin.register(ReportDataSource)
class ReportDataSourceAdmin(admin.ModelAdmin):
    list_display = ['report', 'app_name', 'model_name', 'alias', 'is_primary']
    list_filter = ['app_name', 'is_primary']
    search_fields = ['report__name', 'app_name', 'model_name', 'alias']
    list_select_related = ['report']


@admin.register(ReportField)
class ReportFieldAdmin(admin.ModelAdmin):
    list_display = ['report', 'display_name', 'field_path', 'field_type',
                    'aggregation', 'order', 'is_visible']
    list_filter = ['field_type', 'aggregation', 'is_visible']
    search_fields = ['report__name', 'field_name', 'display_name', 'field_path']
    list_select_related = ['report', 'data_source']
    ordering = ['report', 'order']


@admin.register(ReportFilter)
class ReportFilterAdmin(admin.ModelAdmin):
    list_display = ['report', 'field_path', 'operator', 'value',
                    'value_type', 'logic_group', 'is_active']
    list_filter = ['operator', 'value_type', 'logic_group', 'is_active']
    search_fields = ['report__name', 'field_name', 'field_path']
    list_select_related = ['report', 'data_source']


@admin.register(ReportJoin)
class ReportJoinAdmin(admin.ModelAdmin):
    list_display = ['report', 'left_source', 'left_field', 'join_type',
                    'right_source', 'right_field']
    list_filter = ['join_type']
    search_fields = ['report__name']
    list_select_related = ['report', 'left_source', 'right_source']


@admin.register(ReportParameter)
class ReportParameterAdmin(admin.ModelAdmin):
    list_display = ['report', 'name', 'display_name', 'parameter_type',
                    'is_required', 'order']
    list_filter = ['parameter_type', 'is_required']
    search_fields = ['report__name', 'name', 'display_name']
    list_select_related = ['report']
    ordering = ['report', 'order']


@admin.register(ReportExecution)
class ReportExecutionAdmin(admin.ModelAdmin):
    list_display = ['report', 'executed_by', 'executed_at', 'execution_time',
                    'row_count', 'status', 'export_format']
    list_filter = ['status', 'export_format', 'executed_at']
    search_fields = ['report__name', 'executed_by__username', 'error_message']
    list_select_related = ['report', 'executed_by']
    readonly_fields = ['report', 'executed_by', 'executed_at', 'parameters_used',
                       'execution_time', 'row_count', 'status', 'error_message',
                       'query_count', 'peak_memory', 'result_cache_key',
                       'cached_until', 'export_format', 'export_file_size']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'report', 'schedule_type', 'is_active',
                    'last_run', 'next_run', 'created_by']
    list_filter = ['schedule_type', 'is_active', 'output_format']
    search_fields = ['name', 'report__name', 'email_subject']
    list_select_related = ['report', 'created_by']
    filter_horizontal = ['recipient_users', 'recipient_groups']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'report')
        }),
        ('Schedule Configuration', {
            'fields': ('schedule_type', 'cron_expression', 'time_of_day',
                       'day_of_week', 'day_of_month', 'timezone')
        }),
        ('Execution Settings', {
            'fields': ('parameters', 'output_format')
        }),
        ('Recipients', {
            'fields': ('recipient_emails', 'recipient_users', 'recipient_groups')
        }),
        ('Email Settings', {
            'fields': ('email_subject', 'email_body', 'include_in_body')
        }),
        ('Status', {
            'fields': ('is_active', 'last_run', 'last_status', 'next_run',
                       'retry_on_failure', 'max_retries')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_by', 'created_at', 'updated_at',
                       'last_run', 'last_status', 'next_run']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SavedReportResult)
class SavedReportResultAdmin(admin.ModelAdmin):
    list_display = ['name', 'report', 'saved_by', 'saved_at', 'row_count',
                    'expires_at', 'is_public']
    list_filter = ['is_public', 'saved_at', 'expires_at']
    search_fields = ['name', 'description', 'report__name', 'saved_by__username']
    list_select_related = ['report', 'saved_by', 'execution']
    filter_horizontal = ['shared_with_users', 'shared_with_groups']
    readonly_fields = ['saved_by', 'saved_at', 'parameters_used', 'row_count']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'report')
        }),
        ('Result Data', {
            'fields': ('execution', 'parameters_used', 'row_count'),
            'classes': ('collapse',)
        }),
        ('Sharing', {
            'fields': ('is_public', 'shared_with_users', 'shared_with_groups')
        }),
        ('Metadata', {
            'fields': ('saved_by', 'saved_at', 'expires_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.saved_by = request.user
        super().save_model(request, obj, form, change)