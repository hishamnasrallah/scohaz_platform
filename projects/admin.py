# File: projects/admin.py

from django.contrib import admin
from .models import FlutterProject, ComponentTemplate, Screen


from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages

@admin.register(FlutterProject)
class FlutterProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'package_name', 'user', 'created_at', 'is_active', 'build_apk_button']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['name', 'package_name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['supported_languages']
    actions = ['build_apk_action']

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

    def build_apk_button(self, obj):
        """Add a Build APK button in the list view"""
        return format_html(
            '<a class="button" href="{}">Build APK</a>',
            reverse('admin:build_apk', args=[obj.pk])
        )
    build_apk_button.short_description = 'Actions'
    build_apk_button.allow_tags = True

    def build_apk_action(self, request, queryset):
        """Build APK for selected projects"""
        from builds.models import Build
        from builds.services.build_service import BuildService
        from django.conf import settings

        count = 0
        for project in queryset:
            # Check if there's already a pending build
            if Build.objects.filter(project=project, status__in=['pending', 'building']).exists():
                messages.warning(request, f'Build already in progress for {project.name}')
                continue

            # Create build
            build = Build.objects.create(
                project=project,
                build_type='release',
                version_number='1.0.0',
                build_number=1
            )

            # Run build (synchronously for admin)
            if getattr(settings, 'USE_CELERY_FOR_BUILDS', False):
                from builds.tasks import process_build_task
                process_build_task.delay(build.id)
            else:
                service = BuildService()
                service.start_build(build)

            count += 1

        if count > 0:
            messages.success(request, f'Started {count} build(s)')

    build_apk_action.short_description = 'Build APK for selected projects'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:project_id>/build/', self.admin_site.admin_view(self.build_apk_view), name='build_apk'),
        ]
        return custom_urls + urls

    def build_apk_view(self, request, project_id):
        """Handle Build APK button click"""
        from django.shortcuts import redirect
        from builds.models import Build
        from builds.services.build_service import BuildService
        from django.conf import settings

        project = FlutterProject.objects.get(pk=project_id)

        # Check for existing pending builds
        if Build.objects.filter(project=project, status__in=['pending', 'building']).exists():
            messages.warning(request, f'Build already in progress for {project.name}')
        else:
            # Create build
            build = Build.objects.create(
                project=project,
                build_type='release',
                version_number='1.0.0',
                build_number=1
            )

            # Run build
            if getattr(settings, 'USE_CELERY_FOR_BUILDS', False):
                from builds.tasks import process_build_task
                process_build_task.delay(build.id)
                messages.success(request, f'Build queued for {project.name}. Check Builds section for progress.')
            else:
                service = BuildService()
                service.start_build(build)
                build.refresh_from_db()

                if build.status == 'success':
                    messages.success(request, f'Build completed successfully for {project.name}')
                else:
                    messages.error(request, f'Build failed for {project.name}: {build.error_message}')

        # Redirect back to the change list
        return redirect('admin:projects_flutterproject_changelist')


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