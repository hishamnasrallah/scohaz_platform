# File: projects/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from .models import (
    FlutterProject,
    ComponentTemplate,
    Screen,
    CanvasState,
    ProjectAsset,
    WidgetTemplate,
    StylePreset
)


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
        """Add a Build APK button in the list view"""
        return format_html(
            '<a class="button" href="{}">Build APK</a>',
            reverse('admin:build_apk', args=[obj.pk])
        )

    build_apk_button.short_description = 'Actions'
    build_apk_button.allow_tags = True

    def download_zip_button(self, obj):
        """Add a Download ZIP button in the list view"""
        return format_html(
            '<a class="button" href="{}" style="background-color: #28a745; color: white; margin-left: 5px;">Download ZIP</a>',
            reverse('admin:download_project_zip', args=[obj.pk])
        )

    download_zip_button.short_description = 'Download'
    download_zip_button.allow_tags = True

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
            path('<int:project_id>/download-zip/', self.admin_site.admin_view(self.download_zip_view),
                 name='download_project_zip'),
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

    def download_zip_view(self, request, project_id):
        """Handle Download ZIP button click"""
        import zipfile
        import io
        from django.http import HttpResponse
        from builder.generators.flutter_generator import FlutterGenerator

        project = FlutterProject.objects.get(pk=project_id)

        # Generate code
        generator = FlutterGenerator(project)
        files = generator.generate_project()

        # Create ZIP file in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add each generated file to ZIP
            for filepath, content in files.items():
                zip_file.writestr(filepath, content)

            # Add additional Flutter project files
            zip_file.writestr('.gitignore', self._get_gitignore_content())
            zip_file.writestr('README.md', self._get_readme_content(project))

        # Prepare response
        zip_buffer.seek(0)
        response = HttpResponse(
            zip_buffer.getvalue(),
            content_type='application/zip'
        )
        response['Content-Disposition'] = f'attachment; filename="{project.package_name}.zip"'

        messages.success(request, f'Downloaded {project.name} project files')

        return response

    def _get_gitignore_content(self):
        """Get standard Flutter .gitignore content"""
        return """# Miscellaneous
*.class
*.log
*.pyc
*.swp
.DS_Store
.atom/
.buildlog/
.history
.svn/
migrate_working_dir/

# IntelliJ related
*.iml
*.ipr
*.iws
.idea/

# Flutter/Dart/Pub related
**/doc/api/
**/ios/Flutter/.last_build_id
.dart_tool/
.flutter-plugins
.flutter-plugins-dependencies
.packages
.pub-cache/
.pub/
/build/

# Web related
lib/generated_plugin_registrant.dart

# Symbolication related
app.*.symbols

# Obfuscation related
app.*.map.json

# Android Studio will place build artifacts here
/android/app/debug
/android/app/profile
/android/app/release"""

    def _get_readme_content(self, project):
        """Get README content for the project"""
        return f"""# {project.name}

{project.description or 'A Flutter project created with Visual Builder'}"""


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
    list_display = ['name', 'project', 'route', 'is_home', 'has_canvas_state', 'created_at']
    list_filter = ['is_home', 'created_at', 'updated_at', 'project__user']
    search_fields = ['name', 'route', 'project__name']
    readonly_fields = ['created_at', 'updated_at', 'ui_structure_preview']
    actions = ['create_canvas_states', 'reset_ui_structure']

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

    def has_canvas_state(self, obj):
        """Check if screen has canvas state"""
        return hasattr(obj, 'canvas_state')

    has_canvas_state.boolean = True
    has_canvas_state.short_description = 'Has Canvas State'

    def ui_structure_preview(self, obj):
        """Show a preview of UI structure"""
        import json
        if obj.ui_structure:
            # Format JSON for display
            formatted_json = json.dumps(obj.ui_structure, indent=2)
            return format_html(
                '<pre style="max-height: 300px; overflow-y: auto;">{}</pre>',
                formatted_json[:1000] + '...' if len(formatted_json) > 1000 else formatted_json
            )
        return "No UI structure"

    ui_structure_preview.short_description = 'UI Structure Preview'

    def create_canvas_states(self, request, queryset):
        """Create canvas states for selected screens"""
        count = 0
        for screen in queryset:
            if not hasattr(screen, 'canvas_state'):
                CanvasState.objects.create(screen=screen)
                count += 1

        messages.success(request, f'Created {count} canvas state(s)')

    create_canvas_states.short_description = 'Create canvas states for selected screens'

    def reset_ui_structure(self, request, queryset):
        """Reset UI structure to empty"""
        count = queryset.update(ui_structure={})
        messages.success(request, f'Reset UI structure for {count} screen(s)')

    reset_ui_structure.short_description = 'Reset UI structure'


@admin.register(CanvasState)
class CanvasStateAdmin(admin.ModelAdmin):
    list_display = ['screen', 'history_count', 'history_index', 'zoom_level', 'updated_at']
    list_filter = ['updated_at', 'zoom_level']
    search_fields = ['screen__name', 'screen__project__name']
    readonly_fields = ['history_preview', 'selected_widgets_preview', 'updated_at']
    actions = ['clear_history', 'reset_to_default']

    fieldsets = (
        ('Screen', {
            'fields': ('screen',)
        }),
        ('UI State', {
            'fields': ('selected_widget_ids', 'selected_widgets_preview', 'expanded_tree_nodes', 'zoom_level')
        }),
        ('History', {
            'fields': ('history_index', 'max_history_size', 'history_preview')
        }),
        ('Recovery', {
            'fields': ('last_drag_state',)
        }),
        ('Metadata', {
            'fields': ('updated_at',)
        }),
    )

    def history_count(self, obj):
        """Show number of history items"""
        return len(obj.history_stack)

    history_count.short_description = 'History Items'

    def history_preview(self, obj):
        """Show preview of history stack"""
        if obj.history_stack:
            return format_html(
                '<div>Current Index: {}<br>Total Items: {}</div>',
                obj.history_index,
                len(obj.history_stack)
            )
        return "No history"

    history_preview.short_description = 'History Status'

    def selected_widgets_preview(self, obj):
        """Show selected widgets"""
        if obj.selected_widget_ids:
            widgets = ', '.join(obj.selected_widget_ids[:5])
            if len(obj.selected_widget_ids) > 5:
                widgets += f'... (+{len(obj.selected_widget_ids) - 5} more)'
            return widgets
        return "None selected"

    selected_widgets_preview.short_description = 'Selected Widgets'

    def clear_history(self, request, queryset):
        """Clear history for selected canvas states"""
        for state in queryset:
            state.history_stack = []
            state.history_index = -1
            state.save()

        messages.success(request, f'Cleared history for {queryset.count()} canvas state(s)')

    clear_history.short_description = 'Clear history'

    def reset_to_default(self, request, queryset):
        """Reset canvas states to default"""
        queryset.update(
            selected_widget_ids=[],
            expanded_tree_nodes=[],
            history_stack=[],
            history_index=-1,
            zoom_level=100,
            last_drag_state={}
        )
        messages.success(request, f'Reset {queryset.count()} canvas state(s) to default')

    reset_to_default.short_description = 'Reset to default'


@admin.register(ProjectAsset)
class ProjectAssetAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'asset_type', 'file_size', 'created_at', 'download_link']
    list_filter = ['asset_type', 'created_at', 'project__user']
    search_fields = ['name', 'project__name']
    readonly_fields = ['created_at', 'metadata_preview', 'file_preview']

    fieldsets = (
        ('Basic Information', {
            'fields': ('project', 'name', 'asset_type')
        }),
        ('File Information', {
            'fields': ('file', 'url', 'file_preview')
        }),
        ('Metadata', {
            'fields': ('metadata', 'metadata_preview', 'created_at')
        }),
    )

    def file_size(self, obj):
        """Display file size in human-readable format"""
        if obj.file:
            size = obj.file.size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.2f} KB"
            else:
                return f"{size / (1024 * 1024):.2f} MB"
        return "-"

    file_size.short_description = 'File Size'

    def download_link(self, obj):
        """Provide download link for the asset"""
        if obj.file:
            return format_html(
                '<a href="{}" download>Download</a>',
                obj.file.url
            )
        elif obj.url:
            return format_html(
                '<a href="{}" target="_blank">External Link</a>',
                obj.url
            )
        return "-"

    download_link.short_description = 'Download'

    def metadata_preview(self, obj):
        """Show formatted metadata"""
        import json
        if obj.metadata:
            return format_html(
                '<pre>{}</pre>',
                json.dumps(obj.metadata, indent=2)
            )
        return "No metadata"

    metadata_preview.short_description = 'Metadata Details'

    def file_preview(self, obj):
        """Show file preview for images"""
        if obj.asset_type == 'image' and obj.file:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px;" />',
                obj.file.url
            )
        return "No preview available"

    file_preview.short_description = 'Preview'


@admin.register(WidgetTemplate)
class WidgetTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'category', 'is_public', 'tags_display', 'created_at']
    list_filter = ['category', 'is_public', 'created_at', 'updated_at']
    search_fields = ['name', 'description', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'structure_preview', 'thumbnail_preview']
    filter_horizontal = []

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'category', 'description')
        }),
        ('Template Structure', {
            'fields': ('structure', 'structure_preview')
        }),
        ('Visual', {
            'fields': ('thumbnail', 'thumbnail_preview')
        }),
        ('Settings', {
            'fields': ('is_public', 'tags')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def tags_display(self, obj):
        """Display tags as comma-separated string"""
        if obj.tags:
            return ', '.join(obj.tags[:5])
        return "-"

    tags_display.short_description = 'Tags'

    def structure_preview(self, obj):
        """Show preview of widget structure"""
        import json
        if obj.structure:
            formatted = json.dumps(obj.structure, indent=2)
            return format_html(
                '<pre style="max-height: 300px; overflow-y: auto;">{}</pre>',
                formatted[:500] + '...' if len(formatted) > 500 else formatted
            )
        return "No structure"

    structure_preview.short_description = 'Structure Preview'

    def thumbnail_preview(self, obj):
        """Show thumbnail preview"""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 150px;" />',
                obj.thumbnail.url
            )
        return "No thumbnail"

    thumbnail_preview.short_description = 'Thumbnail Preview'


@admin.register(StylePreset)
class StylePresetAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'widget_type', 'is_public', 'created_at']
    list_filter = ['widget_type', 'is_public', 'created_at']
    search_fields = ['name', 'user__username', 'widget_type']
    readonly_fields = ['created_at', 'properties_preview']

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'widget_type')
        }),
        ('Style Properties', {
            'fields': ('properties', 'properties_preview')
        }),
        ('Settings', {
            'fields': ('is_public',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )

    def properties_preview(self, obj):
        """Show formatted properties"""
        import json
        if obj.properties:
            return format_html(
                '<pre>{}</pre>',
                json.dumps(obj.properties, indent=2)
            )
        return "No properties"

    properties_preview.short_description = 'Properties Preview'