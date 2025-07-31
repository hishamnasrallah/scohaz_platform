from django import forms
from django.utils.safestring import mark_safe
from django.forms.widgets import Textarea
import json


class JSONEditorWidget(Textarea):
    """Enhanced JSON editor widget with syntax highlighting and validation"""

    template_name = 'admin/widgets/json_editor.html'

    def __init__(self, attrs=None, schema=None):
        default_attrs = {
            'class': 'json-editor',
            'data-editor': 'json'
        }

        if attrs:
            default_attrs.update(attrs)

        super().__init__(attrs=default_attrs)
        self.schema = schema

    def render(self, name, value, attrs=None, renderer=None):
        # Format JSON for display
        if value:
            try:
                if isinstance(value, str):
                    value = json.loads(value)
                formatted_value = json.dumps(value, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                formatted_value = value
        else:
            formatted_value = '{}'

        # Get schema data if specified
        schema_attr = ''
        if self.schema:
            schema_attr = f'data-schema="{self.schema}"'

        # Render the widget
        attrs = self.build_attrs(self.attrs, attrs)
        attrs_str = ' '.join([f'{k}="{v}"' for k, v in attrs.items()])

        html = f'''
        <div class="json-editor-container">
            <div class="json-editor-toolbar">
                <button type="button" class="json-format-btn" onclick="formatJSON('{name}')">
                    Format JSON
                </button>
                <button type="button" class="json-validate-btn" onclick="validateJSON('{name}')">
                    Validate
                </button>
                <button type="button" class="json-fullscreen-btn" onclick="toggleFullscreen('{name}')">
                    Fullscreen
                </button>
                <span class="json-status" id="{name}_status"></span>
            </div>
            <textarea name="{name}" {attrs_str} {schema_attr}>{formatted_value}</textarea>
            <div class="json-error" id="{name}_error"></div>
        </div>
        '''

        return mark_safe(html)

    class Media:
        css = {
            'all': ('admin/css/json_editor.css',)
        }
        js = ('admin/js/json_editor.js',)


class YAMLEditorWidget(Textarea):
    """YAML editor widget for configuration files"""

    template_name = 'admin/widgets/yaml_editor.html'

    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'yaml-editor',
            'data-editor': 'yaml'
        }

        if attrs:
            default_attrs.update(attrs)

        super().__init__(attrs=default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        # Handle dict/list values
        if isinstance(value, (dict, list)):
            import yaml
            value = yaml.dump(value, default_flow_style=False, allow_unicode=True)

        attrs = self.build_attrs(self.attrs, attrs)
        attrs_str = ' '.join([f'{k}="{v}"' for k, v in attrs.items()])

        html = f'''
        <div class="yaml-editor-container">
            <div class="yaml-editor-toolbar">
                <button type="button" class="yaml-validate-btn" onclick="validateYAML('{name}')">
                    Validate YAML
                </button>
                <span class="yaml-status" id="{name}_status"></span>
            </div>
            <textarea name="{name}" {attrs_str}>{value or ""}</textarea>
            <div class="yaml-error" id="{name}_error"></div>
        </div>
        '''

        return mark_safe(html)

    class Media:
        css = {
            'all': ('admin/css/yaml_editor.css',)
        }
        js = ('admin/js/yaml_editor.js',)


class CodeEditorWidget(Textarea):
    """Code editor widget with syntax highlighting"""

    def __init__(self, attrs=None, language='javascript'):
        default_attrs = {
            'class': f'code-editor language-{language}',
            'data-language': language
        }

        if attrs:
            default_attrs.update(attrs)

        super().__init__(attrs=default_attrs)
        self.language = language

    def render(self, name, value, attrs=None, renderer=None):
        attrs = self.build_attrs(self.attrs, attrs)
        attrs_str = ' '.join([f'{k}="{v}"' for k, v in attrs.items()])

        html = f'''
        <div class="code-editor-container">
            <div class="code-editor-header">
                <span class="code-language">{self.language.upper()}</span>
                <button type="button" class="code-copy-btn" onclick="copyCode('{name}')">
                    Copy
                </button>
            </div>
            <textarea name="{name}" {attrs_str}>{value or ""}</textarea>
        </div>
        '''

        return mark_safe(html)

    class Media:
        css = {
            'all': (
                'admin/css/code_editor.css',
                '//cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css'
            )
        }
        js = (
            '//cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js',
            '//cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-dart.min.js',
            'admin/js/code_editor.js'
        )