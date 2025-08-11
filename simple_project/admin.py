from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponse
from .models import FlutterProject, Screen
from simple_builds.models import Build
import zipfile
import io


@admin.register(FlutterProject)
class FlutterProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'package_name', 'user', 'created_at', 'is_active', 'build_apk_button',
                    'download_zip_button']
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
        return format_html(
            '<a class="button" href="{}">Build APK</a>',
            reverse('admin:simple_project_flutterproject_build_apk', args=[obj.pk])
        )

    build_apk_button.short_description = 'Build'

    def download_zip_button(self, obj):
        return format_html(
            '<a class="button" href="{}" style="background-color: #28a745;">Download ZIP</a>',
            reverse('admin:simple_project_flutterproject_download_zip', args=[obj.pk])
        )

    download_zip_button.short_description = 'Download'

    def build_apk_action(self, request, queryset):
        from simple_builds.services.build_service import BuildService

        count = 0
        for project in queryset:
            if not Build.objects.filter(project=project, status__in=['pending', 'building']).exists():
                build = Build.objects.create(
                    project=project,
                    build_type='release'
                )
                service = BuildService()
                service.start_build(build)
                count += 1

        messages.success(request, f'Started {count} build(s)')

    build_apk_action.short_description = 'Build APK for selected projects'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:project_id>/build-apk/',
                 self.admin_site.admin_view(self.build_apk_view),
                 name='simple_project_flutterproject_build_apk'),
            path('<int:project_id>/download-zip/',
                 self.admin_site.admin_view(self.download_zip_view),
                 name='simple_project_flutterproject_download_zip'),
        ]
        return custom_urls + urls

    def build_apk_view(self, request, project_id):
        from simple_builds.services.build_service import BuildService

        project = FlutterProject.objects.get(pk=project_id)

        if not Build.objects.filter(project=project, status__in=['pending', 'building']).exists():
            build = Build.objects.create(project=project, build_type='release')
            service = BuildService()
            service.start_build(build)
            messages.success(request, f'Build started for {project.name}')
        else:
            messages.warning(request, f'Build already in progress for {project.name}')

        return redirect('admin:simple_project_flutterproject_changelist')

    def download_zip_view(self, request, project_id):
        from simple_builder.generators.flutter_generator import FlutterGenerator

        project = FlutterProject.objects.get(pk=project_id)
        generator = FlutterGenerator(project)
        files = generator.generate_project()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filepath, content in files.items():
                zip_file.writestr(filepath, content)
            zip_file.writestr('.gitignore', self._get_gitignore_content())
            zip_file.writestr('README.md', self._get_readme_content(project))

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{project.package_name}.zip"'
        return response

    def _get_gitignore_content(self):
        return """.dart_tool/
.packages
.pub/
/build/
*.iml
*.ipr
*.iws
.idea/
.DS_Store"""

    def _get_readme_content(self, project):
        return f"""# {project.name}

{project.description or 'A Flutter project'}

## Getting Started

This project was generated using the Flutter Visual Builder.

Run `flutter pub get` to install dependencies.
Run `flutter run` to start the app."""


@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'route', 'is_home', 'ui_structure_preview']
    list_filter = ['is_home', 'created_at', 'updated_at', 'project__user']
    search_fields = ['name', 'route', 'project__name']
    readonly_fields = ['created_at', 'updated_at', 'ui_structure_preview']

    fieldsets = (
        ('Basic Information', {
            'fields': ('project', 'name', 'route', 'is_home')
        }),
        ('UI Structure', {
            'fields': ('ui_structure', 'ui_structure_preview')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def ui_structure_preview(self, obj):
        import json
        if obj.ui_structure:
            formatted = json.dumps(obj.ui_structure, indent=2)
            return format_html('<pre>{}</pre>', formatted[:500] + '...' if len(formatted) > 500 else formatted)
        return "Empty"

    ui_structure_preview.short_description = 'UI Preview'