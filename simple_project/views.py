from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import FlutterProject, Screen
from .serializers import FlutterProjectSerializer, ScreenSerializer
import uuid


class FlutterProjectViewSet(viewsets.ModelViewSet):
    serializer_class = FlutterProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FlutterProject.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        project = self.get_object()

        # Create duplicate with modified name and package
        new_project = FlutterProject.objects.create(
            name=f"{project.name} (Copy)",
            description=project.description,
            package_name=f"{project.package_name}.copy{uuid.uuid4().hex[:8]}",
            user=request.user,
            app_version=project.app_version,
            default_language=project.default_language,
            primary_color=project.primary_color,
            secondary_color=project.secondary_color
        )
        new_project.supported_languages.set(project.supported_languages.all())

        # Duplicate screens
        for screen in project.screens.all():
            Screen.objects.create(
                project=new_project,
                name=screen.name,
                route=screen.route,
                is_home=screen.is_home,
                ui_structure=screen.ui_structure
            )

        serializer = self.get_serializer(new_project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ScreenViewSet(viewsets.ModelViewSet):
    serializer_class = ScreenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Screen.objects.filter(project__user=self.request.user)
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset

    @action(detail=True, methods=['post'])
    def set_as_home(self, request, pk=None):
        screen = self.get_object()
        screen.is_home = True
        screen.save()
        return Response({'status': 'Screen set as home'})

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
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

    @action(detail=True, methods=['put'])
    def update_ui_structure(self, request, pk=None):
        screen = self.get_object()
        ui_structure = request.data.get('ui_structure')

        if not ui_structure:
            return Response(
                {'error': 'ui_structure is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(ui_structure, dict):
            return Response(
                {'error': 'ui_structure must be a dictionary'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if 'type' not in ui_structure:
            return Response(
                {'error': 'ui_structure must have a type field'},
                status=status.HTTP_400_BAD_REQUEST
            )

        screen.ui_structure = ui_structure
        screen.save()

        serializer = self.get_serializer(screen)
        return Response(serializer.data)