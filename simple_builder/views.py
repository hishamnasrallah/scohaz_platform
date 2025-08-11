from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from simple_project.models import FlutterProject, Screen
from simple_builder.models import WidgetMapping, ComponentTemplate
from simple_builder.generators.flutter_generator import FlutterGenerator
from simple_builder.generators.code_generator_service import generate_flutter_code
from simple_builder.serializers import (
    WidgetMappingSerializer,
    ComponentTemplateSerializer,
    ComponentTemplateBuilderSerializer,
    OrganizedComponentsSerializer
)
from collections import defaultdict
import zipfile
import io
import json


class WidgetMappingViewSet(viewsets.ModelViewSet):
    queryset = WidgetMapping.objects.filter(is_active=True)
    serializer_class = WidgetMappingSerializer
    permission_classes = [IsAuthenticated]


class ComponentTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ComponentTemplate.objects.filter(is_active=True)
    serializer_class = ComponentTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['components_for_builder', 'organized']:
            return ComponentTemplateBuilderSerializer
        return ComponentTemplateSerializer

    @action(detail=False, methods=['get'], url_path='components')
    def components_for_builder(self, request):
        """Get components optimized for builder"""
        components = self.get_queryset()

        category = request.query_params.get('category')
        if category:
            components = components.filter(category=category)

        serializer = ComponentTemplateBuilderSerializer(
            components, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def organized(self, request):
        """Get components organized by widget group"""
        components = self.get_queryset()

        organized_components = defaultdict(list)
        for component in components:
            widget_group = component.default_properties.get('widget_group', 'Other')
            organized_components[widget_group].append(component)

        result = dict(sorted(organized_components.items()))
        serializer = OrganizedComponentsSerializer(result, context={'request': request})

        return Response(serializer.data)

    @action(detail=False)
    def by_category(self, request):
        """Get components grouped by category"""
        components = self.get_queryset()
        result = {}
        for component in components:
            if component.category not in result:
                result[component.category] = []
            result[component.category].append(
                self.get_serializer(component).data
            )
        return Response(result)


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

        project = get_object_or_404(
            FlutterProject,
            id=project_id,
            user=request.user
        )

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

        project = get_object_or_404(
            FlutterProject,
            id=project_id,
            user=request.user
        )

        generator = FlutterGenerator(project)
        files = generator.generate_project()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filepath, content in files.items():
                zip_file.writestr(filepath, content)

        zip_buffer.seek(0)
        response = HttpResponse(
            zip_buffer.getvalue(),
            content_type='application/zip'
        )
        response['Content-Disposition'] = f'attachment; filename="{project.package_name}.zip"'

        return response

    @action(detail=False, methods=['post'], url_path='generate-widget')
    def generate_widget_code(self, request):
        """Generate code for a single widget"""
        widget_data = request.data.get('widget_data')
        options = request.data.get('options', {})

        if not widget_data:
            return Response(
                {'error': 'widget_data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = generate_flutter_code(widget_data, options)

        return Response({
            'code': result.code,
            'lineCount': result.lineCount,
            'widgetCount': result.widgetCount,
            'depth': result.depth,
            'imports': result.imports,
            'statistics': result.statistics,
        })