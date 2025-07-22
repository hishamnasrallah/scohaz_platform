from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import *

class InquiryFieldInline(admin.TabularInline):
    model = InquiryField
    extra = 1
    fields = [
        'field_path', 'display_name', 'field_type',
        'is_visible', 'is_searchable', 'is_sortable',
        'is_filterable', 'order'
    ]

class InquiryFilterInline(admin.TabularInline):
    model = InquiryFilter
    extra = 1
    fields = [
        'name', 'code', 'field_path', 'operator',
        'filter_type', 'default_value', 'is_visible', 'order'
    ]

class InquiryRelationInline(admin.TabularInline):
    model = InquiryRelation
    extra = 0
    fields = [
        'relation_path', 'display_name', 'relation_type',
        'use_select_related', 'use_prefetch_related', 'order'
    ]

class InquirySortInline(admin.TabularInline):
    model = InquirySort
    extra = 1
    fields = ['field_path', 'direction', 'order']

@admin.register(InquiryConfiguration)
class InquiryConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'content_type', 'active',
        'field_count', 'execution_count', 'test_link'
    ]
    list_filter = ['active', 'content_type__app_label']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by']

    inlines = [
        InquiryFieldInline,
        InquiryFilterInline,
        InquiryRelationInline,
        InquirySortInline
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'display_name', 'icon')
        }),
        ('Model Configuration', {
            'fields': ('content_type',)
        }),
        ('Permissions', {
            'fields': ('is_public', 'allowed_groups')
        }),
        ('Query Configuration', {
            'fields': (
                'default_page_size', 'max_page_size',
                'allow_export', 'export_formats', 'distinct',
                'enable_search', 'search_fields'
            )
        }),
        ('Status', {
            'fields': ('active', 'created_at', 'updated_at', 'created_by')
        })
    )

    def field_count(self, obj):
        return obj.fields.count()
    field_count.short_description = 'Fields'

    def execution_count(self, obj):
        return obj.inquiryexecution_set.count()
    execution_count.short_description = 'Executions'

    def test_link(self, obj):
        if obj.pk:
            url = f"/api/inquiry/execute/{obj.code}/"
            return format_html(
                '<a href="{}" target="_blank">Test API</a>',
                url
            )
        return '-'
    test_link.short_description = 'Test'

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(InquiryField)
class InquiryFieldAdmin(admin.ModelAdmin):
    list_display = [
        'inquiry', 'field_path', 'display_name',
        'field_type', 'is_visible', 'is_searchable',
        'is_sortable', 'order'
    ]
    list_filter = [
        'inquiry', 'field_type', 'is_visible',
        'is_searchable', 'is_sortable'
    ]
    search_fields = ['field_path', 'display_name']
    list_editable = ['order', 'is_visible', 'is_searchable', 'is_sortable']

@admin.register(InquiryFilter)
class InquiryFilterAdmin(admin.ModelAdmin):
    list_display = [
        'inquiry', 'name', 'code', 'field_path',
        'operator', 'filter_type', 'is_visible', 'order'
    ]
    list_filter = ['inquiry', 'operator', 'filter_type', 'is_visible']
    search_fields = ['name', 'code', 'field_path']
    list_editable = ['order', 'is_visible']

@admin.register(InquiryExecution)
class InquiryExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'inquiry', 'user', 'executed_at',
        'result_count', 'execution_time_ms',
        'success', 'export_format'
    ]
    list_filter = [
        'inquiry', 'success', 'export_format',
        'executed_at'
    ]
    readonly_fields = [
        'inquiry', 'user', 'executed_at', 'filters_applied',
        'sort_applied', 'search_query', 'result_count',
        'page_size', 'page_number', 'execution_time_ms',
        'query_count', 'export_format', 'success',
        'error_message', 'ip_address', 'user_agent'
    ]
    date_hierarchy = 'executed_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(InquiryTemplate)
class InquiryTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'inquiry', 'is_public', 'created_by', 'created_at']
    list_filter = ['inquiry', 'is_public', 'created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']