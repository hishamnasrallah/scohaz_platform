from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Count
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponse
import json
from django.shortcuts import get_object_or_404, render
from .models import FlutterProject, Screen, ComponentTemplate
from .forms import FlutterProjectForm, ScreenForm, ComponentTemplateForm
from .admin_actions import duplicate_project, generate_preview, export_project_json
from admin_utils.admin_mixins import JSONFieldMixin, ExportMixin, TimestampMixin

admin.site.site_header = "Flutter Visual Builder Admin"
admin.site.site_title = "Flutter Builder"
admin.site.index_title = "Welcome to Flutter Visual Builder"

class BuildCountFilter(SimpleListFilter):
    title = 'build count'
    parameter_name = 'build_count'

    def lookups(self, request, model_admin):
        return (
            ('0', 'No builds'),
            ('1-5', '1-5 builds'),
            ('6+', 'More than 5 builds'),
        )

    def queryset(self, request, queryset):
        if self.value() == '0':
            return queryset.annotate(build_count=Count('builds')).filter(build_count=0)
        elif self.value() == '1-5':
            return queryset.annotate(build_count=Count('builds')).filter(build_count__gte=1, build_count__lte=5)
        elif self.value() == '6+':
            return queryset.annotate(build_count=Count('builds')).filter(build_count__gt=5)

class ScreenInline(admin.TabularInline):
    model = Screen
    form = ScreenForm
    extra = 1
    fields = ('name', 'route', 'is_home', 'component_count', 'preview_button')
    readonly_fields = ('component_count', 'preview_button')

    def component_count(self, obj):
        if obj.ui_structure:
            return len(obj.ui_structure.get('components', []))
        return 0
    component_count.short_description = 'Components'

    def preview_button(self, obj):
        if obj.pk:
            url = reverse('admin:projects_screen_change', args=[obj.pk])
            return format_html(
                '<a class="button" href="{}">Edit Screen</a>',
                url
            )
        return '-'
    preview_button.short_description = 'Actions'


@admin.register(FlutterProject)
class FlutterProjectAdmin(JSONFieldMixin, ExportMixin, TimestampMixin, admin.ModelAdmin):
    form = FlutterProjectForm
    list_display = ['name', 'user', 'package_name', 'version_display', 'language_count',
                    'screen_count', 'build_count', 'created_at', 'actions_display']
    list_filter = ['user', BuildCountFilter, 'app_version', 'created_at', 'updated_at']
    search_fields = ['name', 'package_name', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'project_info', 'build_history']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'package_name', 'user', 'description')
        }),
        ('Version & Localization', {
            'fields': ('app_version', 'supported_languages', 'default_language'),
            'classes': ('collapse',)
        }),
        ('Appearance', {
            'fields': ('primary_color', 'app_icon'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('project_info', 'build_history'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    inlines = [ScreenInline]
    actions = [duplicate_project, generate_preview, export_project_json]

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:project_id>/build/', self.build_project_view, name='build_project'),
            path('<int:project_id>/preview/', self.preview_project_view, name='preview_project'),
        ]
        return custom_urls + urls

    def build_project_view(self, request, project_id):
        """Quick build with default settings"""
        from builds.models import Build
        from builds.services.build_service import BuildService  # Add this import

        project = get_object_or_404(FlutterProject, pk=project_id)

        # Check permissions
        if project.user != request.user and not request.user.is_superuser:
            messages.error(request, 'You do not have permission to build this project.')
            return redirect('admin:projects_flutterproject_change', project_id)

        # Get last build number
        last_build = project.builds.order_by('-build_number').first()
        next_build_number = (last_build.build_number + 1) if last_build else 1

        # Create build with default settings
        build = Build.objects.create(
            project=project,
            build_type='debug',
            version_number='1.0.0',
            build_number=next_build_number,
            status='pending'
        )

        # Trigger build process immediately (for testing)
        try:
            build_service = BuildService()
            build_service.start_build(build)
            messages.success(request, f'Build #{build.build_number} started successfully!')
        except Exception as e:
            messages.error(request, f'Build failed to start: {str(e)}')

        # Redirect to build details
        return redirect('admin:builds_build_change', build.id)

    # def build_project_view(self, request, project_id):
    #     """Quick build with default settings"""
    #     from builds.models import Build
    #
    #     project = get_object_or_404(FlutterProject, pk=project_id)
    #
    #     # Check permissions
    #     if project.user != request.user and not request.user.is_superuser:
    #         messages.error(request, 'You do not have permission to build this project.')
    #         return redirect('admin:projects_flutterproject_change', project_id)
    #
    #     # Get last build number
    #     last_build = project.builds.order_by('-build_number').first()
    #     next_build_number = (last_build.build_number + 1) if last_build else 1
    #
    #     # Create build with default settings
    #     build = Build.objects.create(
    #         project=project,
    #         build_type='debug',  # Default to debug for testing
    #         version_number='1.0.0',
    #         build_number=next_build_number,
    #         status='pending'
    #     )
    #
    #     messages.success(request, f'Build #{build.build_number} created successfully!')
    #
    #     # Redirect to build details
    #     return redirect('admin:builds_build_change', build.id)


    def preview_project_view(self, request, project_id):
        """Preview project"""
        messages.info(request, 'Preview functionality not implemented yet')
        return redirect('admin:projects_flutterproject_change', project_id)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'app_version').prefetch_related(
            'supported_languages', 'screens', 'builds'
        ).annotate(
            build_count=Count('builds'),
            screen_count=Count('screens')
        )

    def version_display(self, obj):
        if obj.app_version:
            return format_html(
                '<span class="version-badge">{}</span>',
                obj.app_version.version_number
            )
        return '-'
    version_display.short_description = 'Version'
    version_display.admin_order_field = 'app_version__version_number'

    def language_count(self, obj):
        count = obj.supported_languages.count()
        if count > 0:
            languages = ', '.join(obj.supported_languages.values_list('lang', flat=True)[:3])
            if count > 3:
                languages += f' (+{count - 3} more)'
            return format_html(
                '<span title="{}">{} languages</span>',
                languages, count
            )
        return '0 languages'
    language_count.short_description = 'Languages'

    def screen_count(self, obj):
        return getattr(obj, 'screen_count', obj.screens.count())
    screen_count.short_description = 'Screens'
    screen_count.admin_order_field = 'screen_count'

    def build_count(self, obj):
        count = getattr(obj, 'build_count', obj.builds.count())
        if count > 0:
            url = reverse('admin:builds_build_changelist') + f'?project__id__exact={obj.pk}'
            return format_html('<a href="{}">{} builds</a>', url, count)
        return '0 builds'
    build_count.short_description = 'Builds'
    build_count.admin_order_field = 'build_count'

    def actions_display(self, obj):
        buttons = []

        # Build button
        build_url = reverse('admin:build_project', args=[obj.pk])
        buttons.append(f'<a class="button" href="{build_url}">Build APK</a>')

        # Preview button
        preview_url = reverse('admin:preview_project', args=[obj.pk])
        buttons.append(f'<a class="button" href="{preview_url}">Preview</a>')

        return format_html(' '.join(buttons))
    actions_display.short_description = 'Quick Actions'

    def project_info(self, obj):
        info = {
            'Screens': obj.screens.count(),
            'Total Components': sum(
                len(screen.ui_structure.get('components', []))
                for screen in obj.screens.all()
            ),
            'Languages': obj.supported_languages.count(),
            'Builds': obj.build_set.count(),
            'Last Build': obj.build_set.last().created_at.strftime('%Y-%m-%d %H:%M')
            if obj.build_set.exists() else 'Never'
        }

        html = '<table class="info-table">'
        for key, value in info.items():
            html += f'<tr><th>{key}:</th><td>{value}</td></tr>'
        html += '</table>'

        return mark_safe(html)
    project_info.short_description = 'Project Information'

    def build_history(self, obj):
        builds = obj.build_set.order_by('-created_at')[:5]
        if not builds:
            return 'No builds yet'

        html = '<table class="build-history-table">'
        html += '<tr><th>Version</th><th>Status</th><th>Date</th><th>Actions</th></tr>'

        for build in builds:
            status_class = {
                'success': 'success',
                'failed': 'error',
                'building': 'warning',
                'pending': 'info'
            }.get(build.status, '')

            download_link = '-'
            if build.apk_file:
                download_link = format_html(
                    '<a href="{}">Download</a>',
                    build.apk_file.url
                )

            html += f'''
            <tr>
                <td>{build.version}</td>
                <td><span class="status-badge status-{status_class}">{build.status}</span></td>
                <td>{build.created_at.strftime('%Y-%m-%d %H:%M')}</td>
                <td>{download_link}</td>
            </tr>
            '''

        html += '</table>'
        return mark_safe(html)
    build_history.short_description = 'Recent Builds'

    def save_model(self, request, obj, form, change):
        if not change:  # New project
            obj.user = request.user
        super().save_model(request, obj, form, change)

        if 'ui_structure' in form.changed_data:
            messages.info(request, 'UI structure updated. Remember to rebuild the APK.')

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
        js = ('admin/js/json_editor.js',)


@admin.register(Screen)
class ScreenAdmin(JSONFieldMixin, admin.ModelAdmin):
    form = ScreenForm
    list_display = ['name', 'project_link', 'route', 'is_home', 'component_count',
                    'last_modified', 'preview_link']
    list_filter = ['project', 'is_home', 'updated_at']
    search_fields = ['name', 'route', 'project__name']
    readonly_fields = ['created_at', 'updated_at', 'component_tree_view']

    fieldsets = (
        ('Basic Information', {
            'fields': ('project', 'name', 'route', 'is_home')
        }),
        ('UI Structure', {
            'fields': ('ui_structure', 'component_tree_view'),
            'classes': ('wide',),
            'description': 'Define the component tree structure using JSON format.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:screen_id>/preview/', self.preview_screen_view, name='preview_screen'),
        ]
        return custom_urls + urls

    def preview_screen_view(self, request, screen_id):
        """Preview screen"""
        messages.info(request, 'Screen preview functionality not implemented yet')
        return redirect('admin:projects_screen_change', screen_id)
    def project_link(self, obj):
        url = reverse('admin:projects_flutterproject_change', args=[obj.project.pk])
        return format_html('<a href="{}">{}</a>', url, obj.project.name)
    project_link.short_description = 'Project'
    project_link.admin_order_field = 'project__name'

    def component_count(self, obj):
        if obj.ui_structure:
            return self._count_components(obj.ui_structure)
        return 0
    component_count.short_description = 'Components'

    def _count_components(self, structure):
        count = 0
        if isinstance(structure, dict):
            if 'type' in structure:
                count += 1
            for key, value in structure.items():
                if key == 'children' and isinstance(value, list):
                    for child in value:
                        count += self._count_components(child)
                elif isinstance(value, dict):
                    count += self._count_components(value)
        return count

    def last_modified(self, obj):
        return obj.updated_at.strftime('%Y-%m-%d %H:%M')
    last_modified.short_description = 'Last Modified'
    last_modified.admin_order_field = 'updated_at'

    def preview_link(self, obj):
        url = reverse('admin:preview_screen', args=[obj.pk])
        return format_html(
            '<a class="button button-small" href="{}">Preview</a>',
            url
        )
    preview_link.short_description = 'Actions'

    def component_tree_view(self, obj):
        if not obj.ui_structure:
            return 'No components defined'

        def render_tree(component, level=0):
            indent = '&nbsp;' * (level * 4)
            type_name = component.get('type', 'unknown')
            props = component.get('properties', {})

            # Icon based on component type
            icons = {
                'scaffold': '🏗️',
                'container': '📦',
                'column': '⬇️',
                'row': '➡️',
                'text': '📝',
                'button': '🔘',
                'image': '🖼️',
                'textfield': '✏️',
                'listview': '📋'
            }
            icon = icons.get(type_name, '🔧')

            html = f'{indent}{icon} <strong>{type_name}</strong>'

            # Add key properties
            if type_name == 'text' and 'content' in props:
                html += f' - "{props["content"][:30]}..."' if len(props.get('content', '')) > 30 else f' - "{props.get("content", "")}"'
            elif type_name == 'button' and 'text' in props:
                html += f' - "{props["text"]}"'

            html += '<br>'

            # Render children
            if 'children' in component:
                for child in component['children']:
                    html += render_tree(child, level + 1)

            # Special handling for scaffold body
            if type_name == 'scaffold' and 'body' in component:
                html += render_tree(component['body'], level + 1)

            return html

        tree_html = render_tree(obj.ui_structure)
        return mark_safe(f'<div class="component-tree">{tree_html}</div>')
    component_tree_view.short_description = 'Component Tree'

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
        js = ('admin/js/json_editor.js',)


@admin.register(ComponentTemplate)
class ComponentTemplateAdmin(admin.ModelAdmin):
    form = ComponentTemplateForm
    list_display = ['icon_display', 'name', 'category', 'flutter_widget', 'property_count',
                    'is_active', 'usage_count', 'preview_button']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'flutter_widget', 'description']
    readonly_fields = ['created_at', 'updated_at', 'template_preview', 'usage_statistics']
    list_editable = ['is_active']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'flutter_widget', 'icon', 'description')
        }),
        ('Configuration', {
            'fields': ('default_properties', 'allowed_children', 'is_container', 'is_active')
        }),
        ('Preview', {
            'fields': ('template_preview',),
            'classes': ('wide',)
        }),
        ('Statistics', {
            'fields': ('usage_statistics',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:component_id>/preview/', self.preview_component_view, name='preview_component'),
        ]
        return custom_urls + urls

    def preview_component_view(self, request, component_id):
        """Preview component"""
        messages.info(request, 'Component preview functionality not implemented yet')
        return redirect('admin:projects_componenttemplate_change', component_id)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Add usage count annotation here if needed
        return qs

    def icon_display(self, obj):
        if obj.icon:
            return format_html(
                '<span class="component-icon" style="font-size: 24px;">{}</span>',
                obj.icon
            )
        return '🔧'
    icon_display.short_description = 'Icon'

    def property_count(self, obj):
        if obj.default_properties:
            return len(obj.default_properties)
        return 0
    property_count.short_description = 'Properties'

    def usage_count(self, obj):
        # This would count actual usage across projects
        return format_html('<span class="usage-count">0</span>')
    usage_count.short_description = 'Usage'

    def preview_button(self, obj):
        url = reverse('admin:preview_component', args=[obj.pk])
        return format_html(
            '<a class="button button-small" href="{}">Preview</a>',
            url
        )
    preview_button.short_description = 'Actions'

    def template_preview(self, obj):
        # Generate a preview of the Flutter widget
        code = f'''
class {obj.flutter_widget} extends StatelessWidget {{
  @override
  Widget build(BuildContext context) {{
    return {obj.flutter_widget}(
'''
        if obj.default_properties:
            for key, value in obj.default_properties.items():
                if isinstance(value, str):
                    code += f'      {key}: "{value}",\n'
                else:
                    code += f'      {key}: {value},\n'

        code += '''    );
  }
}'''

        return format_html(
            '<pre class="code-preview"><code class="language-dart">{}</code></pre>',
            code
        )
    template_preview.short_description = 'Flutter Code Preview'

    def usage_statistics(self, obj):
        # This would show actual statistics
        stats = {
            'Total Uses': 0,
            'Projects Using': 0,
            'Most Common Properties': 'N/A',
            'Last Used': 'Never'
        }

        html = '<table class="stats-table">'
        for key, value in stats.items():
            html += f'<tr><th>{key}:</th><td>{value}</td></tr>'
        html += '</table>'

        return mark_safe(html)
    usage_statistics.short_description = 'Usage Statistics'

    actions = ['activate_components', 'deactivate_components', 'duplicate_component']

    def activate_components(self, request, queryset):
        updated = queryset.update(is_active=True)
        messages.success(request, f'{updated} components activated.')
    activate_components.short_description = 'Activate selected components'

    def deactivate_components(self, request, queryset):
        updated = queryset.update(is_active=False)
        messages.success(request, f'{updated} components deactivated.')
    deactivate_components.short_description = 'Deactivate selected components'

    def duplicate_component(self, request, queryset):
        for component in queryset:
            component.pk = None
            component.name = f'{component.name} (Copy)'
            component.save()
        messages.success(request, f'{queryset.count()} components duplicated.')
    duplicate_component.short_description = 'Duplicate selected components'

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
        js = ('admin/js/json_editor.js', 'admin/js/prism.js')

    def changelist_view(self, request, extra_context=None):
        # Group by category in the changelist
        extra_context = extra_context or {}
        extra_context['categories'] = ComponentTemplate.objects.values_list(
            'category', flat=True
        ).distinct()
        return super().changelist_view(request, extra_context=extra_context)