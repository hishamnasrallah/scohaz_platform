# File: builder/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from projects.models import FlutterProject, Screen
from builder.models import WidgetMapping
from builder.generators.flutter_generator import FlutterGenerator
from builder.generators.code_generator_service import (
    EnhancedCodeGenerator,
    CodeGeneratorOptions,
    CodeFormat,
    generate_flutter_code
)
from builder.serializers import WidgetMappingSerializer
import zipfile
import io
import json


class WidgetMappingViewSet(viewsets.ModelViewSet):
    queryset = WidgetMapping.objects.filter(is_active=True)
    serializer_class = WidgetMappingSerializer
    permission_classes = [IsAuthenticated]


class CodeGeneratorViewSet(viewsets.ViewSet):
    """Enhanced code generation with full feature parity"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def generate_code(self, request):
        """Generate Flutter code for a project (existing functionality)"""
        project_id = request.data.get('project_id')

        if not project_id:
            return Response(
                {'error': 'project_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get project
        project = get_object_or_404(
            FlutterProject,
            id=project_id,
            user=request.user
        )

        # Generate code
        generator = FlutterGenerator(project)
        files = generator.generate_project()

        # Also generate statistics for each screen
        statistics = {}
        for screen in project.screens.all():
            if screen.ui_structure:
                result = generate_flutter_code(screen.ui_structure)
                statistics[screen.name] = {
                    'lineCount': result.lineCount,
                    'widgetCount': result.widgetCount,
                    'depth': result.depth
                }

        return Response({
            'project': project.name,
            'files': files,
            'file_count': len(files),
            'statistics': statistics
        })

    @action(detail=False, methods=['post'])
    def download_project(self, request):
        """Download generated Flutter project as ZIP"""
        project_id = request.data.get('project_id')

        if not project_id:
            return Response(
                {'error': 'project_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get project
        project = get_object_or_404(
            FlutterProject,
            id=project_id,
            user=request.user
        )

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

        return response

    @action(detail=False, methods=['post'], url_path='generate-widget')
    def generate_widget_code(self, request):
        """
        Generate code for a single widget/screen with options

        Request body:
        {
            "widget_data": {...},  // Widget tree structure
            "options": {
                "includeImports": true,
                "includeComments": true,
                "indentSize": 2,
                "useConstConstructors": true,
                "widgetName": "MyWidget",
                "isStateful": false,
                "includeKeys": false,
                "format": "expanded",
                "wrapInClass": true
            }
        }
        """
        widget_data = request.data.get('widget_data')
        options = request.data.get('options', {})

        if not widget_data:
            return Response(
                {'error': 'widget_data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate code
        result = generate_flutter_code(widget_data, options)

        return Response({
            'code': result.code,
            'lineCount': result.lineCount,
            'widgetCount': result.widgetCount,
            'depth': result.depth,
            'imports': result.imports,
            'statistics': result.statistics,
        })

    @action(detail=False, methods=['post'], url_path='generate-screen')
    def generate_screen_code(self, request):
        """Generate code for a specific screen with options"""
        screen_id = request.data.get('screen_id')
        options = request.data.get('options', {})

        if not screen_id:
            return Response(
                {'error': 'screen_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get screen
        screen = get_object_or_404(Screen, id=screen_id, project__user=request.user)

        # Generate code
        generator = EnhancedCodeGenerator()

        # Convert options dict to CodeGeneratorOptions
        code_options = CodeGeneratorOptions(
            includeImports=options.get('includeImports', True),
            includeComments=options.get('includeComments', True),
            indentSize=options.get('indentSize', 2),
            useConstConstructors=options.get('useConstConstructors', True),
            widgetName=options.get('widgetName', screen.name.replace(' ', '')),
            isStateful=options.get('isStateful', False),
            includeKeys=options.get('includeKeys', False),
            format=CodeFormat(options.get('format', 'expanded')),
            wrapInClass=options.get('wrapInClass', True)
        )

        result = generator.generate_code(screen.ui_structure, code_options)

        return Response({
            'screen': screen.name,
            'code': result.code,
            'lineCount': result.lineCount,
            'widgetCount': result.widgetCount,
            'depth': result.depth,
            'imports': result.imports,
            'statistics': result.statistics,
        })

    @action(detail=False, methods=['post'], url_path='validate-code')
    def validate_code(self, request):
        """Validate generated code structure"""
        widget_data = request.data.get('widget_data')

        if not widget_data:
            return Response(
                {'error': 'widget_data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate structure
        errors = []
        warnings = []

        def validate_widget(widget, path='root'):
            if not isinstance(widget, dict):
                errors.append(f"{path}: Invalid widget structure")
                return

            if 'type' not in widget:
                errors.append(f"{path}: Missing 'type' field")

            widget_type = widget.get('type')

            # Check for deprecated widgets
            if widget_type in ['RaisedButton', 'FlatButton']:
                warnings.append(f"{path}: {widget_type} is deprecated, use ElevatedButton or TextButton")

            # Validate children
            children = widget.get('children', [])
            for i, child in enumerate(children):
                validate_widget(child, f"{path}.children[{i}]")

        validate_widget(widget_data)

        return Response({
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        })

    @action(detail=False, methods=['post'], url_path='download-widget')
    def download_widget_code(self, request):
        """Download generated widget code as .dart file"""
        widget_data = request.data.get('widget_data')
        options = request.data.get('options', {})
        filename = request.data.get('filename', 'widget.dart')

        if not widget_data:
            return Response(
                {'error': 'widget_data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate code
        result = generate_flutter_code(widget_data, options)

        # Prepare response
        response = HttpResponse(
            result.code,
            content_type='text/plain'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    @action(detail=False, methods=['post'], url_path='copy-code')
    def copy_code(self, request):
        """Prepare code for clipboard copy (frontend handles actual copy)"""
        widget_data = request.data.get('widget_data')
        options = request.data.get('options', {})

        if not widget_data:
            return Response(
                {'error': 'widget_data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate code
        result = generate_flutter_code(widget_data, options)

        return Response({
            'code': result.code,
            'message': 'Code ready for copying'
        })

    @action(detail=False, methods=['get'], url_path='code-templates')
    def get_code_templates(self, request):
        """Get available widget code templates"""
        templates = [
            {
                'name': 'Basic Container',
                'description': 'Simple container with padding and color',
                'widget_data': {
                    'type': 'Container',
                    'properties': {
                        'width': 200,
                        'height': 200,
                        'color': '#2196F3',
                        'padding': {'all': 16}
                    },
                    'children': [{
                        'type': 'Text',
                        'properties': {
                            'text': 'Hello World',
                            'fontSize': 18,
                            'color': '#FFFFFF'
                        }
                    }]
                }
            },
            {
                'name': 'Login Form',
                'description': 'Basic login form with text fields and button',
                'widget_data': {
                    'type': 'Column',
                    'properties': {
                        'mainAxisAlignment': 'center',
                        'crossAxisAlignment': 'stretch'
                    },
                    'children': [
                        {
                            'type': 'TextField',
                            'properties': {
                                'hintText': 'Email',
                                'keyboardType': 'emailAddress'
                            }
                        },
                        {
                            'type': 'SizedBox',
                            'properties': {'height': 16}
                        },
                        {
                            'type': 'TextField',
                            'properties': {
                                'hintText': 'Password',
                                'obscureText': True
                            }
                        },
                        {
                            'type': 'SizedBox',
                            'properties': {'height': 24}
                        },
                        {
                            'type': 'Button',
                            'properties': {
                                'text': 'Login'
                            }
                        }
                    ]
                }
            },
            {
                'name': 'Card List Item',
                'description': 'Material Design card with content',
                'widget_data': {
                    'type': 'Card',
                    'properties': {
                        'elevation': 4,
                        'margin': {'all': 8}
                    },
                    'children': [{
                        'type': 'Padding',
                        'properties': {
                            'padding': {'all': 16}
                        },
                        'children': [{
                            'type': 'Column',
                            'properties': {
                                'crossAxisAlignment': 'start'
                            },
                            'children': [
                                {
                                    'type': 'Text',
                                    'properties': {
                                        'text': 'Card Title',
                                        'fontSize': 20,
                                        'fontWeight': 'bold'
                                    }
                                },
                                {
                                    'type': 'SizedBox',
                                    'properties': {'height': 8}
                                },
                                {
                                    'type': 'Text',
                                    'properties': {
                                        'text': 'Card description goes here',
                                        'fontSize': 14,
                                        'color': '#757575'
                                    }
                                }
                            ]
                        }]
                    }]
                }
            }
        ]

        return Response(templates)

    @action(detail=False, methods=['post'], url_path='optimize-code')
    def optimize_code(self, request):
        """Optimize widget tree for const constructors"""
        widget_data = request.data.get('widget_data')

        if not widget_data:
            return Response(
                {'error': 'widget_data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate optimized code
        options = {
            'useConstConstructors': True,
            'format': 'expanded',
            'includeComments': False
        }

        result = generate_flutter_code(widget_data, options)

        # Calculate optimization metrics
        original_result = generate_flutter_code(widget_data, {'useConstConstructors': False})

        return Response({
            'optimized_code': result.code,
            'original_lines': original_result.lineCount,
            'optimized_lines': result.lineCount,
            'const_widgets': result.statistics.get('const_eligible', 0),
            'savings_percentage': round(
                (1 - result.lineCount / original_result.lineCount) * 100, 2
            ) if original_result.lineCount > 0 else 0
        })

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

{project.description}

## Getting Started

This project was generated using the Flutter Visual Builder.

### Prerequisites

- Flutter SDK
- Android Studio or VS Code
- Android/iOS emulator or physical device

### Installation

1. Install dependencies:
flutter pub get

2. Generate localization files (if applicable):
flutter gen-l10n

3. Run the app:
flutter run

### Building APK

To build a release APK:
flutter build apk --release

The APK will be generated at `build/app/outputs/flutter-apk/app-release.apk`

## Features

- Package Name: {project.package_name}
- Default Language: {project.default_language}
- Supported Languages: {', '.join([lang.lang for lang in project.supported_languages.all()])}

Generated with Flutter Visual Builder"""
