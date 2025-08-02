# File: projects/admin.py

from django.contrib import admin
from .models import FlutterProject, ComponentTemplate, Screen


@admin.register(FlutterProject)
class FlutterProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'package_name', 'user', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['name', 'package_name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['supported_languages']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'package_name', 'user')
        }),
        ('App Configuration', {
            'fields': ('app_version', 'default_language', 'supported_languages',
                       'primary_color', 'secondary_color', 'app_icon')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


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


@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'route', 'is_home', 'created_at']
    list_filter = ['is_home', 'created_at', 'updated_at']
    search_fields = ['name', 'route', 'project__name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('project', 'name', 'route', 'is_home')
        }),
        ('UI Structure', {
            'fields': ('ui_structure',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )