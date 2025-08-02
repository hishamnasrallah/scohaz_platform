# File: projects/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import FlutterProject, ComponentTemplate, Screen
from .serializers import FlutterProjectSerializer, ComponentTemplateSerializer, ScreenSerializer


class FlutterProjectViewSet(viewsets.ModelViewSet):
    serializer_class = FlutterProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FlutterProject.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a project"""
        project = self.get_object()
        new_project = FlutterProject.objects.create(
            name=f"{project.name} (Copy)",
            description=project.description,
            package_name=f"{project.package_name}.copy",
            user=request.user,
            app_version=project.app_version,
            default_language=project.default_language,
            primary_color=project.primary_color,
            secondary_color=project.secondary_color
        )
        new_project.supported_languages.set(project.supported_languages.all())

        serializer = self.get_serializer(new_project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ComponentTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ComponentTemplate.objects.filter(is_active=True)
    serializer_class = ComponentTemplateSerializer
    permission_classes = [IsAuthenticated]

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


class ScreenViewSet(viewsets.ModelViewSet):
    serializer_class = ScreenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.query_params.get('project')
        queryset = Screen.objects.filter(project__user=self.request.user)

        if project_id:
            queryset = queryset.filter(project_id=project_id)

        return queryset

    @action(detail=True, methods=['post'])
    def set_as_home(self, request, pk=None):
        """Set this screen as home screen"""
        screen = self.get_object()
        screen.is_home = True
        screen.save()
        return Response({'status': 'Screen set as home'})

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a screen"""
        screen = self.get_object()
        new_screen = Screen.objects.create(
            project=screen.project,
            name=f"{screen.name} (Copy)",
            route=f"{screen.route}-copy",
            is_home=False,
            ui_structure=screen.ui_structure
        )
        serializer = self.get_serializer(new_screen)
        return Response(serializer.data, status=status.HTTP_201_CREATED)