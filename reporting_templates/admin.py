from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    PDFTemplate, PDFTemplateElement,
    PDFTemplateVariable, PDFGenerationLog
)


class PDFTemplateElementInline(admin.TabularInline):
    model = PDFTemplateElement
    extra = 0
    fields = [
        'element_type', 'element_key', 'x_position', 'y_position',
        'width', 'height', 'z_index', 'active_ind'
    ]
    ordering = ['page_number', 'z_index', 'y_position']


class PDFTemplateVariableInline(admin.TabularInline):
    model = PDFTemplateVariable
    extra = 0
    fields = [
        'variable_key', 'display_name', 'data_type',
        'data_source', 'is_required'
    ]


@admin.register(PDFTemplate)
class PDFTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'primary_language', 'page_size',
        'active_ind', 'created_by', 'created_at'
    ]
    list_filter = [
        'primary_language', 'page_size', 'orientation',
        'active_ind', 'is_system_template'
    ]
    search_fields = ['name', 'name_ara', 'code', 'description']
    readonly_fields = ['created_by', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'name_ara', 'code', 'description',
                'description_ara', 'primary_language', 'supports_bilingual'
            )
        }),
        ('Page Configuration', {
            'fields': (
                'page_size', 'orientation',
                ('margin_top', 'margin_bottom'),
                ('margin_left', 'margin_right')
            )
        }),
        ('Template Options', {
            'fields': (
                'header_enabled', 'footer_enabled',
                'watermark_enabled', 'watermark_text'
            )
        }),
        ('Permissions', {
            'fields': ('groups', 'content_type', 'is_system_template')
        }),
        ('Metadata', {
            'fields': (
                'active_ind', 'created_by', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )

    inlines = [PDFTemplateElementInline, PDFTemplateVariableInline]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pk>/preview/',
                self.admin_site.admin_view(self.preview_template),
                name='pdf_template_preview'
            ),
        ]
        return custom_urls + urls

    def preview_template(self, request, pk):
        """Preview template in admin"""
        from django.shortcuts import render
        template = self.get_object(request, pk)

        # You can create a preview page here
        context = {
            'template': template,
            'opts': self.model._meta,
        }
        return render(request, 'admin/pdf_templates/preview.html', context)


@admin.register(PDFTemplateElement)
class PDFTemplateElementAdmin(admin.ModelAdmin):
    list_display = [
        'template', 'element_type', 'element_key',
        'x_position', 'y_position', 'z_index', 'active_ind'
    ]
    list_filter = ['element_type', 'active_ind', 'template']
    search_fields = ['element_key', 'text_content']
    ordering = ['template', 'page_number', 'z_index', 'y_position']


@admin.register(PDFGenerationLog)
class PDFGenerationLogAdmin(admin.ModelAdmin):
    list_display = [
        'template', 'generated_by', 'status',
        'created_at', 'generation_time'
    ]
    list_filter = ['status', 'template', 'created_at']
    search_fields = ['file_name', 'error_message']
    readonly_fields = [
        'template', 'generated_by', 'context_data',
        'file_name', 'file_path', 'file_size', 'status',
        'error_message', 'created_at', 'completed_at',
        'generation_time', 'ip_address', 'user_agent'
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False