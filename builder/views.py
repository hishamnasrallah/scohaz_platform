# File: builder/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from projects.models import FlutterProject
from builder.models import WidgetMapping
from builder.generators.flutter_generator import FlutterGenerator
from builder.serializers import WidgetMappingSerializer
import zipfile
import io
import os
from django.http import HttpResponse


class WidgetMappingViewSet(viewsets.ModelViewSet):
    queryset = WidgetMapping.objects.filter(is_active=True)
    serializer_class = WidgetMappingSerializer
    permission_classes = [IsAuthenticated]


class CodeGeneratorViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def generate_code(self, request):
        """Generate Flutter code for a project"""
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

        return Response({
            'project': project.name,
            'files': files,
            'file_count': len(files)
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
```
flutter pub get
```

2. Generate localization files (if applicable):
```
flutter gen-l10n
```

3. Run the app:
```
flutter run
```

### Building APK

To build a release APK:
```
flutter build apk --release
```

The APK will be generated at `build/app/outputs/flutter-apk/app-release.apk`

## Features

- Package Name: {project.package_name}
- Default Language: {project.default_language}
- Supported Languages: {', '.join([lang.lang for lang in project.supported_languages.all()])}

Generated with Flutter Visual Builder"""