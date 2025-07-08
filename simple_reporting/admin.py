# reporting_templates/admin.py

from django.contrib import admin
from .models import PDFTemplate, PDFElement


class PDFElementInline(admin.TabularInline):
    model = PDFElement
    extra = 1
    fields = ['x_position', 'y_position', 'text_content', 'is_dynamic', 'font_size']


@admin.register(PDFTemplate)
class PDFTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'content_type', 'created_at', 'active']
    list_filter = ['active', 'content_type']
    search_fields = ['name', 'code']
    readonly_fields = ['created_by', 'created_at']

    inlines = [PDFElementInline]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)