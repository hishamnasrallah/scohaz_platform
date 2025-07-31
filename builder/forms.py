from django import forms
from django.core.exceptions import ValidationError
import json
import re
import yaml

from .models import WidgetMapping, GenerationConfig
from admin_utils.json_widget import JSONEditorWidget, YAMLEditorWidget


class WidgetMappingForm(forms.ModelForm):
    """Form for WidgetMapping with enhanced validation"""

    # Import statement template
    import_statements = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': "import 'package:flutter/material.dart';\nimport 'package:flutter/widgets.dart';"
        }),
        required=False,
        help_text='Import statements required for this widget'
    )

    # Code template for complex widgets
    code_template = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 10,
            'placeholder': '''${widget_name}(
  ${properties}
  ${children}
)''',
            'class': 'code-editor',
            'data-language': 'dart'
        }),
        required=False,
        help_text='Template for generating widget code. Use ${property_name} for placeholders.'
    )

    class Meta:
        model = WidgetMapping
        fields = '__all__'
        widgets = {
            'properties_mapping': JSONEditorWidget(attrs={
                'style': 'height: 400px;',
                'data-schema': 'widget_mapping'
            }),
            'default_properties': JSONEditorWidget(attrs={
                'style': 'height: 300px;',
                'data-schema': 'properties'
            }),
            'allowed_child_types': JSONEditorWidget(attrs={
                'style': 'height: 200px;',
                'placeholder': '["container", "column", "row", "text", "button"]'
            }),
            'description': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Describe how this UI component maps to Flutter widget'
            })
        }

    def clean_ui_type(self):
        ui_type = self.cleaned_data.get('ui_type')

        # Validate UI type format (lowercase with underscores)
        if not re.match(r'^[a-z][a-z0-9_]*$', ui_type):
            raise ValidationError(
                'UI type must be lowercase and contain only letters, numbers, and underscores.'
            )

        # Check for duplicates
        existing = WidgetMapping.objects.filter(ui_type=ui_type).exclude(pk=self.instance.pk)
        if existing.exists():
            raise ValidationError(f'A mapping for "{ui_type}" already exists.')

        return ui_type

    def clean_flutter_widget(self):
        flutter_widget = self.cleaned_data.get('flutter_widget')

        # Validate Flutter widget name
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', flutter_widget):
            raise ValidationError(
                'Flutter widget name must start with uppercase and contain only letters and numbers.'
            )

        return flutter_widget

    def clean_properties_mapping(self):
        mapping = self.cleaned_data.get('properties_mapping')

        if not mapping:
            return {}

        # Validate mapping structure
        for ui_prop, flutter_config in mapping.items():
            if isinstance(flutter_config, dict):
                # Validate complex mapping
                if 'name' not in flutter_config:
                    raise ValidationError(
                        f'Property mapping for "{ui_prop}" must include a "name" field.'
                    )

                # Validate type if specified
                if 'type' in flutter_config:
                    valid_types = [
                        'string', 'int', 'double', 'bool', 'color',
                        'edge_insets', 'alignment', 'text_style'
                    ]
                    if flutter_config['type'] not in valid_types:
                        raise ValidationError(
                            f'Invalid type "{flutter_config["type"]}" for property "{ui_prop}". '
                            f'Valid types are: {", ".join(valid_types)}'
                        )

                # Validate transform if specified
                if 'transform' in flutter_config:
                    self._validate_transform(flutter_config['transform'], ui_prop)

        return mapping

    def _validate_transform(self, transform, prop_name):
        """Validate transform expressions"""
        # Check for dangerous operations
        dangerous_patterns = ['__', 'eval', 'exec', 'import', 'open', 'file']
        for pattern in dangerous_patterns:
            if pattern in transform:
                raise ValidationError(
                    f'Transform for "{prop_name}" contains forbidden operation: {pattern}'
                )

        # Validate placeholder usage
        if '${value}' not in transform:
            raise ValidationError(
                f'Transform for "{prop_name}" must include ${"{value}"} placeholder'
            )

    def clean_allowed_child_types(self):
        allowed_types = self.cleaned_data.get('allowed_child_types')

        if not allowed_types:
            return []

        if not isinstance(allowed_types, list):
            raise ValidationError('Allowed child types must be a list')

        # Validate each type exists
        existing_types = set(WidgetMapping.objects.values_list('ui_type', flat=True))
        existing_types.update(['text', 'container', 'column', 'row', 'button'])  # Built-in types

        for child_type in allowed_types:
            if child_type not in existing_types:
                raise ValidationError(f'Unknown child type: {child_type}')

        return allowed_types

    def clean(self):
        cleaned_data = super().clean()

        # Validate has_children and allowed_child_types consistency
        has_children = cleaned_data.get('has_children')
        allowed_types = cleaned_data.get('allowed_child_types')

        if has_children and not allowed_types:
            self.add_error(
                'allowed_child_types',
                'Widgets that accept children must specify allowed child types.'
            )

        if not has_children and allowed_types:
            self.add_error(
                'allowed_child_types',
                'Widgets that do not accept children cannot have allowed child types.'
            )

        return cleaned_data


class GenerationConfigForm(forms.ModelForm):
    """Form for GenerationConfig with YAML validation"""

    # Flutter and Dart version choices
    FLUTTER_VERSION_CHOICES = [
        ('3.0.0', 'Flutter 3.0.0'),
        ('3.3.0', 'Flutter 3.3.0'),
        ('3.7.0', 'Flutter 3.7.0'),
        ('3.10.0', 'Flutter 3.10.0'),
        ('3.13.0', 'Flutter 3.13.0'),
        ('3.16.0', 'Flutter 3.16.0 (Latest Stable)'),
    ]

    DART_VERSION_CHOICES = [
        ('2.17.0', 'Dart 2.17.0'),
        ('2.18.0', 'Dart 2.18.0'),
        ('2.19.0', 'Dart 2.19.0'),
        ('3.0.0', 'Dart 3.0.0'),
        ('3.1.0', 'Dart 3.1.0'),
        ('3.2.0', 'Dart 3.2.0 (Latest)'),
    ]

    flutter_version = forms.ChoiceField(
        choices=FLUTTER_VERSION_CHOICES,
        initial='3.16.0'
    )

    dart_version = forms.ChoiceField(
        choices=DART_VERSION_CHOICES,
        initial='3.2.0'
    )

    class Meta:
        model = GenerationConfig
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Description of this configuration preset'
            }),
            'dependencies': YAMLEditorWidget(attrs={
                'style': 'height: 300px;',
                'placeholder': '''cupertino_icons: ^1.0.5
http: ^1.1.0
provider: ^6.0.5
shared_preferences: ^2.2.0'''
            }),
            'dev_dependencies': YAMLEditorWidget(attrs={
                'style': 'height: 200px;',
                'placeholder': '''flutter_lints: ^3.0.0
build_runner: ^2.4.6
json_serializable: ^6.7.1'''
            }),
            'assets_config': JSONEditorWidget(attrs={
                'style': 'height: 200px;',
                'data-schema': 'assets'
            }),
            'fonts_config': JSONEditorWidget(attrs={
                'style': 'height: 250px;',
                'data-schema': 'fonts'
            }),
            'gradle_config': JSONEditorWidget(attrs={
                'style': 'height: 200px;',
                'data-schema': 'gradle'
            }),
            'ios_config': JSONEditorWidget(attrs={
                'style': 'height: 200px;',
                'data-schema': 'ios'
            }),
            'additional_config': JSONEditorWidget(attrs={
                'style': 'height: 300px;'
        })
        }

        def clean_min_sdk_version(self):
            version = self.cleaned_data.get('min_sdk_version')

            if version < 21:
                raise ValidationError(
                    'Minimum SDK version must be 21 or higher for Flutter apps.'
                )

            if version > 33:
                raise ValidationError(
                    'SDK version 33 is the current maximum. Please use a valid version.'
                )

            return version

        def clean_dependencies(self):
            dependencies = self.cleaned_data.get('dependencies')

            if not dependencies:
                return {}

            # Validate YAML format
            try:
                if isinstance(dependencies, str):
                    parsed = yaml.safe_load(dependencies)
                else:
                    parsed = dependencies
            except yaml.YAMLError as e:
                raise ValidationError(f'Invalid YAML format: {str(e)}')

            # Validate package names and versions
            for package, version in parsed.items():
                if not re.match(r'^[a-z][a-z0-9_]*$', package):
                    raise ValidationError(
                        f'Invalid package name: {package}. '
                        'Package names must be lowercase with underscores.'
                    )

                # Validate version constraints
                if isinstance(version, str) and not self._validate_version_constraint(version):
                    raise ValidationError(
                        f'Invalid version constraint for {package}: {version}'
                    )

            return parsed

        def clean_dev_dependencies(self):
            # Same validation as dependencies
            dev_deps = self.cleaned_data.get('dev_dependencies')

            if not dev_deps:
                return {}

            try:
                if isinstance(dev_deps, str):
                    parsed = yaml.safe_load(dev_deps)
                else:
                    parsed = dev_deps
            except yaml.YAMLError as e:
                raise ValidationError(f'Invalid YAML format: {str(e)}')

            return parsed

        def _validate_version_constraint(self, constraint):
            """Validate pub version constraint format"""
            # Simple validation for common patterns
            patterns = [
                r'^\^?\d+\.\d+\.\d+$',  # ^1.0.0 or 1.0.0
                r'^>=\d+\.\d+\.\d+ <\d+\.\d+\.\d+$',  # >=1.0.0 <2.0.0
                r'^any$',  # any
            ]

            return any(re.match(pattern, constraint) for pattern in patterns)

        def clean_assets_config(self):
            config = self.cleaned_data.get('assets_config')

            if not config:
                return {'paths': []}

            # Validate structure
            if 'paths' not in config:
                config['paths'] = []

            # Validate asset paths
            for path in config['paths']:
                if not isinstance(path, str):
                    raise ValidationError('Asset paths must be strings')

                # Check for common issues
                if path.startswith('/'):
                    raise ValidationError(
                        f'Asset path "{path}" should not start with /'
                    )

            return config

        def clean_fonts_config(self):
            config = self.cleaned_data.get('fonts_config')

            if not config:
                return {'fonts': []}

            # Validate font configuration
            if 'fonts' not in config:
                config['fonts'] = []

            for font in config['fonts']:
                if not isinstance(font, dict):
                    raise ValidationError('Each font must be a configuration object')

                if 'family' not in font:
                    raise ValidationError('Each font must have a "family" name')

                if 'fonts' in font:
                    for font_asset in font['fonts']:
                        if 'asset' not in font_asset:
                            raise ValidationError(
                                f'Font {font["family"]} is missing asset path'
                            )

            return config

        def clean(self):
            cleaned_data = super().clean()

            # Validate Flutter and Dart version compatibility
            flutter_version = cleaned_data.get('flutter_version')
            dart_version = cleaned_data.get('dart_version')

            # Simple compatibility check
            if flutter_version and dart_version:
                if flutter_version.startswith('3.') and dart_version.startswith('2.'):
                    if float(dart_version[:3]) < 2.17:
                        self.add_error(
                            'dart_version',
                            'Flutter 3.x requires Dart 2.17 or higher'
                        )

            return cleaned_data