from django.contrib import admin
from .models import ComponentTemplate, WidgetMapping


@admin.register(ComponentTemplate)
class ComponentTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'flutter_widget', 'can_have_children', 'is_active']
    list_filter = ['category', 'is_active', 'can_have_children']
    search_fields = ['name', 'flutter_widget', 'description']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'flutter_widget', 'icon', 'description')
        }),
        ('Widget Configuration', {
            'fields': ('default_properties', 'can_have_children', 'max_children')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at')
        }),
    )


@admin.register(WidgetMapping)
class WidgetMappingAdmin(admin.ModelAdmin):
    list_display = ['ui_type', 'flutter_widget', 'can_have_children', 'is_active', 'created_at']
    list_filter = ['is_active', 'can_have_children', 'created_at']
    search_fields = ['ui_type', 'flutter_widget']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('ui_type', 'flutter_widget')
        }),
        ('Widget Configuration', {
            'fields': ('can_have_children',)
        }),
        ('Mappings', {
            'fields': ('properties_mapping', 'import_statements', 'code_template')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at')
        }),
    )