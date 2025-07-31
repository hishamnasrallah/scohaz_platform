from django import forms
from django.core.exceptions import ValidationError
import json
import re

from .models import FlutterProject, Screen, ComponentTemplate
from admin_utils.json_widget import JSONEditorWidget


class FlutterProjectForm(forms.ModelForm):
    """Enhanced form for FlutterProject with validation"""

    class Meta:
        model = FlutterProject
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Brief description of your Flutter application'
            }),
            'package_name': forms.TextInput(attrs={
                'placeholder': 'com.example.myapp',
                'pattern': r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$'
            }),
            'supported_languages': forms.CheckboxSelectMultiple(),
            'primary_color': forms.TextInput(attrs={
                'type': 'color',
                'style': 'width: 80px; height: 40px;'
            })
        }

    def clean_package_name(self):
        package_name = self.cleaned_data.get('package_name')

        # Validate package name format
        pattern = r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$'
        if not re.match(pattern, package_name):
            raise ValidationError(
                'Package name must follow reverse domain notation (e.g., com.example.app). '
                'Use only lowercase letters, numbers, and underscores.'
            )

        # Check for reserved keywords
        reserved_words = ['flutter', 'dart', 'android', 'ios', 'web', 'test']
        parts = package_name.split('.')
        for part in parts:
            if part in reserved_words:
                raise ValidationError(
                    f'"{part}" is a reserved keyword and cannot be used in package names.'
                )

        return package_name

    # def clean_ui_structure(self):
    #     ui_structure = self.cleaned_data.get('ui_structure')
    #
    #     if not ui_structure:
    #         return {}
    #
    #     # Validate JSON structure
    #     if not isinstance(ui_structure, dict):
    #         raise ValidationError('UI structure must be a JSON object')
    #
    #     # Validate required fields
    #     if 'version' not in ui_structure:
    #         ui_structure['version'] = '1.0'
    #
    #     return ui_structure

    def clean(self):
        cleaned_data = super().clean()

        # Ensure at least one language is selected
        supported_languages = cleaned_data.get('supported_languages')
        if supported_languages and not supported_languages.exists():
            self.add_error('supported_languages', 'At least one language must be selected.')

        # Validate default language is in supported languages
        default_language = cleaned_data.get('default_language')
        if supported_languages and default_language:
            lang_codes = supported_languages.values_list('lang', flat=True)
            if default_language not in lang_codes:
                self.add_error(
                    'default_language',
                    'Default language must be one of the supported languages.'
                )

        return cleaned_data


class ScreenForm(forms.ModelForm):
    """Form for Screen model with component validation"""

    class Meta:
        model = Screen
        fields = '__all__'
        widgets = {
            'ui_structure': JSONEditorWidget(attrs={
                'style': 'height: 500px;',
                'data-schema': 'screen'
            }),
            'route': forms.TextInput(attrs={
                'placeholder': '/home',
                'pattern': r'^/[a-z][a-z0-9_/]*$'
            })
        }

    def clean_route(self):
        route = self.cleaned_data.get('route')

        if not route.startswith('/'):
            route = '/' + route

        # Validate route format
        if not re.match(r'^/[a-z][a-z0-9_/]*$', route):
            raise ValidationError(
                'Route must start with / and contain only lowercase letters, '
                'numbers, underscores, and forward slashes.'
            )

        return route

    def clean_ui_structure(self):
        ui_structure = self.cleaned_data.get('ui_structure')

        if not ui_structure:
            raise ValidationError('UI structure cannot be empty')

        # Validate component structure
        errors = self._validate_component(ui_structure)
        if errors:
            raise ValidationError(errors)

        return ui_structure

    def _validate_component(self, component, path='root'):
        """Recursively validate component structure"""
        errors = []

        if not isinstance(component, dict):
            errors.append(f'{path}: Component must be a JSON object')
            return errors

        # Check required fields
        if 'type' not in component:
            errors.append(f'{path}: Component must have a "type" field')

        # Validate children if present
        if 'children' in component:
            if not isinstance(component['children'], list):
                errors.append(f'{path}.children: Children must be an array')
            else:
                for i, child in enumerate(component['children']):
                    child_errors = self._validate_component(
                        child, f'{path}.children[{i}]'
                    )
                    errors.extend(child_errors)

        # Special validation for scaffold
        if component.get('type') == 'scaffold':
            if 'body' not in component:
                errors.append(f'{path}: Scaffold must have a "body" field')
            elif 'body' in component:
                body_errors = self._validate_component(
                    component['body'], f'{path}.body'
                )
                errors.extend(body_errors)

        return errors

    def clean(self):
        cleaned_data = super().clean()

        # Only one screen can be home per project
        is_home = cleaned_data.get('is_home')
        project = cleaned_data.get('project')

        if is_home and project:
            existing_home = Screen.objects.filter(
                project=project,
                is_home=True
            ).exclude(pk=self.instance.pk)

            if existing_home.exists():
                self.add_error(
                    'is_home',
                    f'Project already has a home screen: {existing_home.first().name}'
                )

        return cleaned_data


class ComponentTemplateForm(forms.ModelForm):
    """Form for ComponentTemplate with property validation"""

    # Category choices
    CATEGORY_CHOICES = [
        ('layout', 'Layout'),
        ('input', 'Input'),
        ('display', 'Display'),
        ('navigation', 'Navigation'),
        ('feedback', 'Feedback'),
        ('custom', 'Custom')
    ]

    category = forms.ChoiceField(choices=CATEGORY_CHOICES)

    class Meta:
        model = ComponentTemplate
        fields = '__all__'
        widgets = {
            'default_properties': JSONEditorWidget(attrs={
                'style': 'height: 300px;',
                'data-schema': 'properties'
            }),
            'allowed_children': JSONEditorWidget(attrs={
                'style': 'height: 200px;',
                'placeholder': '["container", "column", "row", "text", "button"]'
            }),
            'description': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Brief description of the component'
            }),
            'icon': forms.TextInput(attrs={
                'placeholder': 'e.g., 📦 or 🔘',
                'style': 'font-size: 24px; width: 80px;'
            })
        }

    def clean_flutter_widget(self):
        flutter_widget = self.cleaned_data.get('flutter_widget')

        # Validate Flutter widget name
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', flutter_widget):
            raise ValidationError(
                'Flutter widget name must start with uppercase and contain only letters and numbers.'
            )

        return flutter_widget

    def clean_default_properties(self):
        properties = self.cleaned_data.get('default_properties')

        if not properties:
            return {}

        # Validate property types
        valid_types = [str, int, float, bool, list, dict]
        for key, value in properties.items():
            if not any(isinstance(value, t) for t in valid_types):
                raise ValidationError(
                    f'Invalid type for property "{key}". '
                    f'Only strings, numbers, booleans, lists, and objects are allowed.'
                )

        return properties

    def clean_allowed_children(self):
        allowed_children = self.cleaned_data.get('allowed_children')

        if not allowed_children:
            return []

        if not isinstance(allowed_children, list):
            raise ValidationError('Allowed children must be a list of component types')

        # Validate each type
        for child_type in allowed_children:
            if not isinstance(child_type, str):
                raise ValidationError('Each allowed child must be a string')

        return allowed_children

    def clean(self):
        cleaned_data = super().clean()

        # Container validation
        is_container = cleaned_data.get('is_container')
        allowed_children = cleaned_data.get('allowed_children')

        if is_container and not allowed_children:
            self.add_error(
                'allowed_children',
                'Container components must specify allowed children types.'
            )

        if not is_container and allowed_children:
            self.add_error(
                'allowed_children',
                'Non-container components cannot have allowed children.'
            )

        return cleaned_data