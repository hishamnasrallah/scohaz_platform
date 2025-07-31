from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from builder.generators import FlutterGenerator
from .models import WidgetMapping, GenerationConfig
from .serializers import (
    WidgetMappingSerializer, GenerationConfigSerializer,
    CodePreviewSerializer, GeneratedCodeSerializer,
    FlutterProjectStructureSerializer, ProjectFileSerializer
)
# from .generators import FlutterCodeGenerator
from projects.models import FlutterProject, Screen
from utils.multilangual_helpers import read_translation


class WidgetMappingViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for WidgetMapping read operations"""
    serializer_class = WidgetMappingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['ui_type', 'is_active']

    def get_queryset(self):
        """Get active widget mappings"""
        return WidgetMapping.objects.filter(is_active=True)

    @action(detail=False, methods=['get'])
    def ui_types(self, request):
        """Get available UI types"""
        ui_types = WidgetMapping.objects.filter(
            is_active=True
        ).values_list('ui_type', flat=True).distinct()

        return Response({
            'ui_types': list(ui_types)
        })


class GenerationConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for GenerationConfig CRUD operations"""
    serializer_class = GenerationConfigSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter configs by user's projects"""
        return GenerationConfig.objects.filter(
            project__user=self.request.user
        ).select_related('project')

    def perform_create(self, serializer):
        """Validate project ownership before creating config"""
        project = serializer.validated_data['project']
        if project.user != self.request.user:
            raise PermissionError("You don't have permission to create config for this project")

        serializer.save()


class CodePreviewAPIView(APIView):
    """API view for generating Flutter code preview"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate Flutter code preview from UI structure"""
        serializer = CodePreviewSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            data = serializer.validated_data

            # Get project if specified
            project = None
            if data.get('project_id'):
                project = get_object_or_404(
                    FlutterProject,
                    id=data['project_id'],
                    user=request.user
                )

            # Initialize code generator
            generator = FlutterGenerator(project)

            # Generate code for the screen
            screen_data = data['screen_data']
            code_result = generator.generate_screen_code(
                screen_name=screen_data['name'],
                ui_structure=screen_data['ui_structure'],
                include_imports=data['include_imports']
            )

            # Prepare response
            response_data = {
                'dart_code': code_result['code'],
                'imports': code_result['imports'],
                'widget_tree': code_result['widget_tree']
            }

            # Add translations if project has them
            if project and code_result.get('translations_used'):
                response_data['translations_used'] = code_result['translations_used']

            result_serializer = GeneratedCodeSerializer(data=response_data)
            if result_serializer.is_valid():
                return Response(result_serializer.data)

            return Response(
                result_serializer.errors,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GenerateProjectAPIView(APIView):
    """API view for generating complete Flutter project structure"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate complete Flutter project files"""
        serializer = FlutterProjectStructureSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            data = serializer.validated_data

            # Get project
            project = get_object_or_404(
                FlutterProject,
                id=data['project_id'],
                user=request.user
            )

            # Initialize generator with project
            generator = FlutterGenerator(project)

            # Generate complete project structure
            try:
                project_files = generator.generate_flutter_project(
                    include_translations=data['include_translations'],
                    build_config=data.get('build_config', {})
                )

                # Convert to serializable format
                files_data = []
                for file_path, content in project_files.items():
                    files_data.append({
                        'path': file_path,
                        'content': content,
                        'is_binary': False
                    })

                # Add success response
                return Response({
                    'project': {
                        'name': project.name,
                        'package_name': project.package_name,
                        'version': project.app_version.version_number if project.app_version else '1.0.0'
                    },
                    'files': files_data,
                    'file_count': len(files_data)
                })

            except Exception as e:
                return Response(
                    {'error': f'Failed to generate project: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TranslationKeysAPIView(APIView):
    """API view for getting available translation keys"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get available translation keys for a language"""
        lang = request.query_params.get('lang', 'en')

        try:
            translations = read_translation(lang)

            # Format keys with preview values
            keys_data = []
            for key, value in translations.items():
                keys_data.append({
                    'key': key,
                    'value': value[:50] + '...' if len(value) > 50 else value,
                    'length': len(value)
                })

            return Response({
                'language': lang,
                'keys': keys_data,
                'total_keys': len(keys_data)
            })

        except Exception as e:
            return Response(
                {'error': f'Failed to load translations: {str(e)}'},
                status=status.HTTP_404_NOT_FOUND
            )