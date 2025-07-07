# reporting_templates/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect
from django.contrib import messages
import json

from .models import (
    PDFTemplate, PDFTemplateElement, PDFTemplateVariable,
    PDFTemplateParameter, PDFTemplateDataSource, PDFGenerationLog
)


class PDFTemplateParameterInline(admin.TabularInline):
    model = PDFTemplateParameter
    extra = 0
    fields = [
        'parameter_key', 'display_name', 'parameter_type', 'is_required',
        'widget_type', 'query_field', 'query_operator', 'order', 'active_ind'
    ]
    ordering = ['order', 'parameter_key']


class PDFTemplateDataSourceInline(admin.TabularInline):
    model = PDFTemplateDataSource
    extra = 0
    fields = [
        'source_key', 'display_name', 'fetch_method', 'content_type',
        'query_path', 'cache_timeout', 'order', 'active_ind'
    ]
    ordering = ['order', 'source_key']


class PDFTemplateElementInline(admin.TabularInline):
    model = PDFTemplateElement
    extra = 0
    fields = [
        'element_type', 'element_key', 'x_position', 'y_position',
        'width', 'height', 'z_index', 'page_number', 'active_ind'
    ]
    ordering = ['page_number', 'z_index', 'y_position']


class PDFTemplateVariableInline(admin.TabularInline):
    model = PDFTemplateVariable
    extra = 0
    fields = [
        'variable_key', 'display_name', 'data_type',
        'data_source', 'is_required', 'transform_function'
    ]


@admin.register(PDFTemplate)
class PDFTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'data_source_type', 'primary_language',
        'requires_parameters', 'allow_self_generation',
        'allow_other_generation', 'active_ind', 'created_by',
        'created_at', 'action_buttons'
    ]
    list_filter = [
        'primary_language', 'data_source_type', 'page_size',
        'orientation', 'active_ind', 'is_system_template',
        'requires_parameters', 'allow_self_generation',
        'allow_other_generation'
    ]
    search_fields = ['name', 'name_ara', 'code', 'description']
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    filter_horizontal = ['groups']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'name_ara', 'code', 'description',
                'description_ara', 'primary_language', 'supports_bilingual'
            )
        }),
        ('Data Source Configuration', {
            'fields': (
                'data_source_type', 'content_type', 'query_filter',
                'custom_function_path', 'raw_sql_query', 'related_models'
            )
        }),
        ('Access Control', {
            'fields': (
                'requires_parameters', 'allow_self_generation',
                'allow_other_generation', 'groups'
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
        ('System Information', {
            'fields': (
                'is_system_template', 'active_ind',
                'created_by', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )

    inlines = [
        PDFTemplateParameterInline,
        PDFTemplateDataSourceInline,
        PDFTemplateElementInline,
        PDFTemplateVariableInline
    ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def action_buttons(self, obj):
        buttons = []

        # Preview button
        preview_url = reverse('admin:pdf_template_preview', args=[obj.pk])
        buttons.append(
            f'<a class="button" href="{preview_url}">👁️ Preview</a>'
        )

        # Test generate button
        test_url = reverse('admin:pdf_template_test', args=[obj.pk])
        buttons.append(
            f'<a class="button" href="{test_url}">🧪 Test</a>'
        )

        # Duplicate button
        duplicate_url = reverse('admin:pdf_template_duplicate', args=[obj.pk])
        buttons.append(
            f'<a class="button" href="{duplicate_url}">📋 Duplicate</a>'
        )

        # Designer button
        designer_url = reverse('admin:pdf_template_designer', args=[obj.pk])
        buttons.append(
            f'<a class="button" href="{designer_url}">🎨 Designer</a>'
        )

        return mark_safe(' '.join(buttons))

    action_buttons.short_description = 'Actions'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pk>/preview/',
                self.admin_site.admin_view(self.preview_template),
                name='pdf_template_preview'
            ),
            path(
                '<int:pk>/test/',
                self.admin_site.admin_view(self.test_template),
                name='pdf_template_test'
            ),
            path(
                '<int:pk>/duplicate/',
                self.admin_site.admin_view(self.duplicate_template),
                name='pdf_template_duplicate'
            ),
            path(
                '<int:pk>/designer/',
                self.admin_site.admin_view(self.template_designer),
                name='pdf_template_designer'
            ),
        ]
        return custom_urls + urls

    def preview_template(self, request, pk):
        """Preview template configuration"""
        template = self.get_object(request, pk)

        # Get sample data structure
        from reporting_templates.services.data_service import DataFetchingService

        try:
            service = DataFetchingService(
                template=template,
                user=request.user,
                parameters={}
            )

            # Get parameter schema
            parameter_schema = []
            for param in template.parameters.filter(active_ind=True):
                parameter_schema.append({
                    'key': param.parameter_key,
                    'name': param.display_name,
                    'type': param.parameter_type,
                    'required': param.is_required,
                    'default': param.default_value,
                    'widget': param.widget_type
                })

            # Get data sources
            data_sources = []
            for source in template.data_sources.filter(active_ind=True):
                data_sources.append({
                    'key': source.source_key,
                    'name': source.display_name,
                    'method': source.fetch_method,
                    'model': str(source.content_type) if source.content_type else None
                })

            context = {
                'template': template,
                'parameter_schema': parameter_schema,
                'data_sources': data_sources,
                'opts': self.model._meta,
                'has_view_permission': True,
            }

            return render(
                request,
                'admin/reporting_templates/pdftemplate/preview.html',
                context
            )

        except Exception as e:
            messages.error(request, f"Error loading template preview: {e}")
            return redirect('admin:reporting_templates_pdftemplate_changelist')

    def test_template(self, request, pk):
        """Test template generation"""
        template = self.get_object(request, pk)

        if request.method == 'POST':
            # Get parameters from form
            parameters = {}
            for param in template.parameters.filter(active_ind=True):
                value = request.POST.get(f'param_{param.parameter_key}')
                if value:
                    parameters[param.parameter_key] = value

            # Generate test PDF
            from reporting_templates.services.data_service import DataFetchingService
            from reporting_templates.services.pdf_generator import PDFGenerator

            try:
                # Fetch data
                service = DataFetchingService(
                    template=template,
                    user=request.user,
                    parameters=parameters
                )
                context_data = service.fetch_all_data()

                # Generate PDF
                generator = PDFGenerator(template)
                pdf_buffer = generator.generate_pdf(context_data)

                # Return PDF
                response = HttpResponse(
                    pdf_buffer.getvalue(),
                    content_type='application/pdf'
                )
                response['Content-Disposition'] = f'inline; filename="{template.code}_test.pdf"'
                return response

            except Exception as e:
                messages.error(request, f"Error generating PDF: {e}")

        # Show test form
        context = {
            'template': template,
            'parameters': template.parameters.filter(active_ind=True),
            'opts': self.model._meta,
        }

        return render(
            request,
            'admin/reporting_templates/pdftemplate/test.html',
            context
        )

    def duplicate_template(self, request, pk):
        """Duplicate a template"""
        template = self.get_object(request, pk)

        try:
            from reporting_templates.services.pdf_generator import PDFTemplateService

            new_name = f"{template.name} (Copy)"
            new_template = PDFTemplateService.duplicate_template(
                template, new_name
            )

            messages.success(
                request,
                f"Template duplicated successfully as '{new_name}'"
            )

            return redirect(
                'admin:reporting_templates_pdftemplate_change',
                new_template.pk
            )

        except Exception as e:
            messages.error(request, f"Error duplicating template: {e}")
            return redirect('admin:reporting_templates_pdftemplate_changelist')

    def template_designer(self, request, pk):
        """Visual template designer"""
        template = self.get_object(request, pk)

        context = {
            'template': template,
            'opts': self.model._meta,
        }

        return render(
            request,
            'admin/reporting_templates/pdftemplate/designer.html',
            context
        )


@admin.register(PDFTemplateParameter)
class PDFTemplateParameterAdmin(admin.ModelAdmin):
    list_display = [
        'template', 'parameter_key', 'display_name', 'parameter_type',
        'is_required', 'widget_type', 'order', 'active_ind'
    ]
    list_filter = [
        'parameter_type', 'widget_type', 'is_required', 'active_ind'
    ]
    search_fields = ['parameter_key', 'display_name', 'template__name']
    ordering = ['template', 'order', 'parameter_key']
    filter_horizontal = ['restricted_to_groups']


@admin.register(PDFTemplateDataSource)
class PDFTemplateDataSourceAdmin(admin.ModelAdmin):
    list_display = [
        'template', 'source_key', 'display_name', 'fetch_method',
        'content_type', 'cache_timeout', 'order', 'active_ind'
    ]
    list_filter = ['fetch_method', 'active_ind']
    search_fields = ['source_key', 'display_name', 'template__name']
    ordering = ['template', 'order', 'source_key']


@admin.register(PDFTemplateElement)
class PDFTemplateElementAdmin(admin.ModelAdmin):
    list_display = [
        'template', 'element_type', 'element_key',
        'x_position', 'y_position', 'z_index',
        'page_number', 'active_ind'
    ]
    list_filter = ['element_type', 'active_ind', 'template']
    search_fields = ['element_key', 'text_content']
    ordering = ['template', 'page_number', 'z_index', 'y_position']


@admin.register(PDFGenerationLog)
class PDFGenerationLogAdmin(admin.ModelAdmin):
    list_display = [
        'template', 'generated_by', 'generated_for', 'status',
        'created_at', 'generation_time', 'file_size_display'
    ]
    list_filter = ['status', 'template', 'created_at']
    search_fields = [
        'file_name', 'error_message', 'generated_by__username',
        'generated_for__username'
    ]
    readonly_fields = [
        'template', 'generated_by', 'generated_for', 'parameters',
        'context_data', 'file_name', 'file_path', 'file_size',
        'status', 'error_message', 'created_at', 'completed_at',
        'generation_time', 'ip_address', 'user_agent'
    ]
    ordering = ['-created_at']

    def file_size_display(self, obj):
        """Display file size in human-readable format"""
        if not obj.file_size:
            return '-'

        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0

        return f"{size:.1f} TB"

    file_size_display.short_description = 'File Size'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Non-superusers only see their own logs
        return qs.filter(generated_by=request.user)