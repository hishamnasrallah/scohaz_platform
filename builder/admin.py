from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
import json

from .models import WidgetMapping, GenerationConfig
from .forms import WidgetMappingForm, GenerationConfigForm
from admin_utils.admin_mixins import JSONFieldMixin, TimestampMixin


@admin.register(WidgetMapping)
class WidgetMappingAdmin(JSONFieldMixin, TimestampMixin, admin.ModelAdmin):
    form = WidgetMappingForm
    list_display = ['ui_type', 'flutter_widget', 'category', 'property_count',
                    'has_children', 'is_active', 'test_mapping']
    list_filter = ['category', 'is_active', 'has_children', 'created_at']
    search_fields = ['ui_type', 'flutter_widget', 'description']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at', 'mapping_preview', 'example_usage']

    fieldsets = (
        ('Mapping Configuration', {
            'fields': ('ui_type', 'flutter_widget', 'category', 'description')
        }),
        ('Properties Mapping', {
            'fields': ('properties_mapping', 'default_properties'),
            'classes': ('wide',),
            'description': 'Define how UI properties map to Flutter widget properties'
        }),
        ('Widget Configuration', {
            'fields': ('has_children', 'allowed_child_types', 'is_active'),
            'description': 'Configure widget behavior and constraints'
        }),
        ('Code Templates', {
            'fields': ('import_statements', 'code_template'),
            'classes': ('collapse',)
        }),
        ('Preview & Examples', {
            'fields': ('mapping_preview', 'example_usage'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def property_count(self, obj):
        if obj.properties_mapping:
            return len(obj.properties_mapping)
        return 0
    property_count.short_description = 'Mapped Properties'

    def test_mapping(self, obj):
        url = reverse('admin:test_widget_mapping', args=[obj.pk])
        return format_html(
            '<a class="button button-small" href="{}">Test</a>',
            url
        )
    test_mapping.short_description = 'Actions'

    def mapping_preview(self, obj):
        """Show a preview of how properties are mapped"""
        if not obj.properties_mapping:
            return 'No properties mapped'

        html = '<table class="mapping-preview-table">'
        html += '<tr><th>UI Property</th><th>→</th><th>Flutter Property</th><th>Type</th></tr>'

        for ui_prop, flutter_info in obj.properties_mapping.items():
            if isinstance(flutter_info, dict):
                flutter_prop = flutter_info.get('name', ui_prop)
                prop_type = flutter_info.get('type', 'dynamic')
                transform = flutter_info.get('transform', '')

                transform_html = f'<br><small>Transform: {transform}</small>' if transform else ''

                html += f'''
                <tr>
                    <td><code>{ui_prop}</code></td>
                    <td>→</td>
                    <td><code>{flutter_prop}</code>{transform_html}</td>
                    <td><span class="type-badge">{prop_type}</span></td>
                </tr>
                '''
            else:
                html += f'''
                <tr>
                    <td><code>{ui_prop}</code></td>
                    <td>→</td>
                    <td><code>{flutter_info}</code></td>
                    <td><span class="type-badge">string</span></td>
                </tr>
                '''

        html += '</table>'
        return mark_safe(html)
    mapping_preview.short_description = 'Property Mapping Preview'

    def example_usage(self, obj):
        """Generate example usage code"""
        example_ui = {
            'type': obj.ui_type,
            'properties': {}
        }

        # Add example properties
        if obj.properties_mapping:
            for prop in list(obj.properties_mapping.keys())[:3]:
                if prop == 'text' or prop == 'content':
                    example_ui['properties'][prop] = 'Hello World'
                elif prop == 'color':
                    example_ui['properties'][prop] = '#2196F3'
                elif prop == 'size' or prop == 'fontSize':
                    example_ui['properties'][prop] = 16
                else:
                    example_ui['properties'][prop] = 'value'

        # Generate Flutter code
        flutter_code = self._generate_flutter_code(obj, example_ui['properties'])

        html = f'''
        <div class="example-usage">
            <h4>Input UI JSON:</h4>
            <pre class="code-preview"><code class="language-json">{json.dumps(example_ui, indent=2)}</code></pre>
            
            <h4>Generated Flutter Code:</h4>
            <pre class="code-preview"><code class="language-dart">{flutter_code}</code></pre>
        </div>
        '''

        return mark_safe(html)
    example_usage.short_description = 'Example Usage'

    def _generate_flutter_code(self, mapping, properties):
        """Generate example Flutter code based on mapping"""
        code = f'{mapping.flutter_widget}(\n'

        if mapping.default_properties:
            for key, value in mapping.default_properties.items():
                if isinstance(value, str):
                    code += f'  {key}: "{value}",\n'
                else:
                    code += f'  {key}: {value},\n'

        for ui_prop, value in properties.items():
            if ui_prop in mapping.properties_mapping:
                flutter_info = mapping.properties_mapping[ui_prop]
                if isinstance(flutter_info, dict):
                    flutter_prop = flutter_info.get('name', ui_prop)
                else:
                    flutter_prop = flutter_info

                if isinstance(value, str):
                    code += f'  {flutter_prop}: "{value}",\n'
                else:
                    code += f'  {flutter_prop}: {value},\n'

        code += ')'
        return code

    actions = ['activate_mappings', 'deactivate_mappings', 'validate_mappings']

    def activate_mappings(self, request, queryset):
        updated = queryset.update(is_active=True)
        messages.success(request, f'{updated} mappings activated.')
    activate_mappings.short_description = 'Activate selected mappings'

    def deactivate_mappings(self, request, queryset):
        updated = queryset.update(is_active=False)
        messages.success(request, f'{updated} mappings deactivated.')
    deactivate_mappings.short_description = 'Deactivate selected mappings'

    def validate_mappings(self, request, queryset):
        """Validate that mappings are correctly configured"""
        errors = []
        for mapping in queryset:
            if not mapping.properties_mapping:
                errors.append(f'{mapping.ui_type}: No properties mapped')
            if not mapping.flutter_widget:
                errors.append(f'{mapping.ui_type}: No Flutter widget specified')

        if errors:
            messages.error(request, f'Validation errors found:\n' + '\n'.join(errors))
        else:
            messages.success(request, f'{queryset.count()} mappings validated successfully.')
    validate_mappings.short_description = 'Validate selected mappings'

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
        js = ('admin/js/json_editor.js', 'admin/js/prism.js')


@admin.register(GenerationConfig)
class GenerationConfigAdmin(TimestampMixin, admin.ModelAdmin):
    form = GenerationConfigForm
    list_display = ['name', 'project', 'flutter_version', 'target_platform',
                    'is_active', 'last_used', 'generate_button']
    list_filter = ['flutter_version', 'target_platform', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'project__name']
    readonly_fields = ['created_at', 'updated_at', 'last_used', 'config_preview']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'project', 'description', 'is_active')
        }),
        ('Flutter Configuration', {
            'fields': ('flutter_version', 'dart_version', 'target_platform', 'min_sdk_version')
        }),
        ('Build Settings', {
            'fields': ('enable_proguard', 'enable_multidex', 'build_mode'),
            'classes': ('collapse',)
        }),
        ('Dependencies', {
            'fields': ('dependencies', 'dev_dependencies'),
            'classes': ('wide',),
            'description': 'Specify package dependencies in YAML format'
        }),
        ('Assets & Resources', {
            'fields': ('assets_config', 'fonts_config'),
            'classes': ('collapse',)
        }),
        ('Advanced Settings', {
            'fields': ('gradle_config', 'ios_config', 'additional_config'),
            'classes': ('collapse',)
        }),
        ('Preview', {
            'fields': ('config_preview',),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_used'),
            'classes': ('collapse',)
        })
    )

    def generate_button(self, obj):
        if obj.project:
            url = reverse('admin:generate_with_config', args=[obj.pk])
            return format_html(
                '<a class="button button-small" href="{}">Generate</a>',
                url
            )
        return '-'
    generate_button.short_description = 'Actions'

    def config_preview(self, obj):
        """Preview the generated pubspec.yaml"""
        pubspec = {
            'name': obj.project.package_name if obj.project else 'app',
            'description': obj.project.description if obj.project else 'Flutter app',
            'version': '1.0.0+1',
            'environment': {
                'sdk': f'>={obj.dart_version} <3.0.0',
                'flutter': f'>={obj.flutter_version}'
            },
            'dependencies': {
                'flutter': {'sdk': 'flutter'},
                'flutter_localizations': {'sdk': 'flutter'}
            },
            'dev_dependencies': {
                'flutter_test': {'sdk': 'flutter'},
                'flutter_lints': '^2.0.0'
            },
            'flutter': {
                'uses-material-design': True,
                'generate': True
            }
        }

        # Add custom dependencies
        if obj.dependencies:
            pubspec['dependencies'].update(obj.dependencies)

        if obj.dev_dependencies:
            pubspec['dev_dependencies'].update(obj.dev_dependencies)

        # Add assets
        if obj.assets_config:
            pubspec['flutter']['assets'] = obj.assets_config.get('paths', [])

        # Add fonts
        if obj.fonts_config:
            pubspec['flutter']['fonts'] = obj.fonts_config.get('fonts', [])

        import yaml
        yaml_content = yaml.dump(pubspec, default_flow_style=False, sort_keys=False)

        return format_html(
            '<pre class="code-preview"><code class="language-yaml">{}</code></pre>',
            yaml_content
        )
    config_preview.short_description = 'Generated pubspec.yaml Preview'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if not change:
            messages.success(
                request,
                f'Generation config "{obj.name}" created. You can now use it to generate Flutter projects.'
            )

    actions = ['duplicate_config', 'set_as_default']

    def duplicate_config(self, request, queryset):
        for config in queryset:
            config.pk = None
            config.name = f'{config.name} (Copy)'
            config.is_active = False
            config.save()

        messages.success(request, f'{queryset.count()} configurations duplicated.')
    duplicate_config.short_description = 'Duplicate selected configurations'

    def set_as_default(self, request, queryset):
        # Deactivate all configs for the same projects
        projects = queryset.values_list('project', flat=True).distinct()
        GenerationConfig.objects.filter(project__in=projects).update(is_active=False)

        # Activate selected configs
        queryset.update(is_active=True)
        messages.success(request, f'{queryset.count()} configurations set as default.')
    set_as_default.short_description = 'Set as default for project'

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
        js = ('admin/js/json_editor.js', 'admin/js/prism.js')