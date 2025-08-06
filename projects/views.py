# File: projects/views.py - Enhanced version with builder-specific endpoints

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from collections import defaultdict
from .models import FlutterProject, ComponentTemplate, Screen
from .serializers import (
    FlutterProjectSerializer,
    ComponentTemplateSerializer,
    ComponentTemplateBuilderSerializer,
    OrganizedComponentsSerializer,
    ScreenSerializer
)


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
    """
    Enhanced ComponentTemplate ViewSet with builder-specific endpoints
    """
    queryset = ComponentTemplate.objects.filter(is_active=True)
    serializer_class = ComponentTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use builder serializer for builder-specific actions"""
        if self.action in ['components_for_builder', 'organized']:
            return ComponentTemplateBuilderSerializer
        return ComponentTemplateSerializer

    @action(detail=False, methods=['get'], url_path='components')
    def components_for_builder(self, request):
        """
        GET /api/projects/component-templates/components/
        Return ComponentTemplate data organized for builder toolbox
        """
        # Get active components that should show in builder
        components = self.get_queryset().filter(
            default_properties__show_in_builder=True
        ).order_by('category')

        # Apply additional filters if needed
        category = request.query_params.get('category')
        if category:
            components = components.filter(category=category)

        search = request.query_params.get('search')
        if search:
            components = components.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(flutter_widget__icontains=search)
            )

        serializer = ComponentTemplateBuilderSerializer(
            components, many=True, context={'request': request}
        )
        return Response({
            'count': components.count(),
            'components': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='organized')
    def organized(self, request):
        """
        GET /api/projects/component-templates/organized/
        Return widgets grouped by widget_group for better UX
        """
        # Get active components that should show in builder
        components = self.get_queryset().filter(
            default_properties__show_in_builder=True
        )

        # Group components by widget_group
        organized_components = defaultdict(list)

        for component in components:
            widget_group = component.default_properties.get('widget_group', 'Other')
            display_order = component.default_properties.get('display_order', 999)

            organized_components[widget_group].append((component, display_order))

        # Sort components within each group by display_order
        for group_name in organized_components:
            organized_components[group_name].sort(key=lambda x: x[1])
            organized_components[group_name] = [comp[0] for comp in organized_components[group_name]]

        # Convert to regular dict and sort groups by name
        result = dict(sorted(organized_components.items()))

        # Serialize using the organized serializer
        serializer = OrganizedComponentsSerializer(result, context={'request': request})

        return Response({
            'groups': list(result.keys()),
            'total_components': sum(len(comps) for comps in result.values()),
            'components': serializer.data
        })

    @action(detail=False)
    def by_category(self, request):
        """Get components grouped by category (existing endpoint)"""
        components = self.get_queryset()
        result = {}
        for component in components:
            if component.category not in result:
                result[component.category] = []
            result[component.category].append(
                self.get_serializer(component).data
            )
        return Response(result)

    @action(detail=False, methods=['get'])
    def widget_groups(self, request):
        """
        GET /api/projects/component-templates/widget-groups/
        Return list of available widget groups
        """
        components = self.get_queryset().filter(
            default_properties__show_in_builder=True
        )

        groups = set()
        for component in components:
            group = component.default_properties.get('widget_group', 'Other')
            groups.add(group)

        return Response({
            'widget_groups': sorted(list(groups)),
            'count': len(groups)
        })

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """
        GET /api/projects/component-templates/categories/
        Return list of available categories
        """
        categories = self.get_queryset().values_list('category', flat=True).distinct()
        return Response({
            'categories': list(categories),
            'count': len(categories)
        })


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

    @action(detail=True, methods=['put'])
    def update_ui_structure(self, request, pk=None):
        """
        PUT /api/projects/screens/{id}/update_ui_structure/
        Update only the UI structure of a screen
        """
        screen = self.get_object()
        ui_structure = request.data.get('ui_structure')

        if not ui_structure:
            return Response(
                {'error': 'ui_structure is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate UI structure
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