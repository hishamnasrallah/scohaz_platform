# File: projects/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.db import transaction
from collections import defaultdict
import uuid
import copy
from .models import (
    FlutterProject, ComponentTemplate, Screen,
    CanvasState, ProjectAsset, WidgetTemplate, StylePreset
)
from .serializers import (
    FlutterProjectSerializer,
    ComponentTemplateSerializer,
    ComponentTemplateBuilderSerializer,
    OrganizedComponentsSerializer,
    ScreenSerializer,
    CanvasStateSerializer,
    ProjectAssetSerializer,
    WidgetTemplateSerializer,
    StylePresetSerializer
)
from .validators import WidgetValidator


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

    @action(detail=True, methods=['post'], url_path='widgets/add')
    def add_widget(self, request, pk=None):
        """
        Add a widget to the UI structure at a specific position

        Request body:
        {
            "widget_type": "container",
            "parent_id": "uuid-of-parent" or null,
            "index": 0,  # position within parent's children
            "properties": {
                "width": 200,
                "height": 200,
                "color": "#FFFFFF"
            }
        }
        """
        screen = self.get_object()
        widget_type = request.data.get('widget_type')
        parent_id = request.data.get('parent_id')
        index = request.data.get('index', 0)
        properties = request.data.get('properties', {})

        # Generate new widget ID
        widget_id = str(uuid.uuid4())

        # Create widget object
        new_widget = {
            'id': widget_id,
            'type': widget_type,
            'properties': properties,
            'children': []
        }

        # Add to UI structure
        if not parent_id and not screen.ui_structure:
            # Set as root
            screen.ui_structure = new_widget
        else:
            # Add to parent
            self._add_widget_to_parent(screen.ui_structure, parent_id, new_widget, index)

        screen.save()
        return Response({'widget_id': widget_id, 'ui_structure': screen.ui_structure})

    @action(detail=True, methods=['delete'], url_path='widgets/(?P<widget_id>[^/.]+)')
    def remove_widget(self, request, pk=None, widget_id=None):
        """Remove a widget from the UI structure"""
        screen = self.get_object()

        if not screen.ui_structure:
            return Response({'error': 'No UI structure'}, status=400)

        # If removing root
        if screen.ui_structure.get('id') == widget_id:
            screen.ui_structure = {}
        else:
            self._remove_widget_from_tree(screen.ui_structure, widget_id)

        screen.save()
        return Response({'ui_structure': screen.ui_structure})

    @action(detail=True, methods=['post'], url_path='widgets/move')
    def move_widget(self, request, pk=None):
        """
        Move a widget to a new parent/position

        Request body:
        {
            "widget_id": "uuid",
            "new_parent_id": "uuid" or null,
            "index": 0
        }
        """
        screen = self.get_object()
        widget_id = request.data.get('widget_id')
        new_parent_id = request.data.get('new_parent_id')
        index = request.data.get('index', 0)

        # Extract widget
        widget = self._extract_widget(screen.ui_structure, widget_id)
        if not widget:
            return Response({'error': 'Widget not found'}, status=404)

        # Add to new position
        if not new_parent_id:
            # Moving to root - not allowed if root exists
            return Response({'error': 'Cannot have multiple root widgets'}, status=400)
        else:
            self._add_widget_to_parent(screen.ui_structure, new_parent_id, widget, index)

        screen.save()
        return Response({'ui_structure': screen.ui_structure})

    @action(detail=True, methods=['post'], url_path='widgets/reorder')
    def reorder_children(self, request, pk=None):
        """
        Reorder children within the same parent

        Request body:
        {
            "parent_id": "uuid" or null for root,
            "old_index": 0,
            "new_index": 1
        }
        """
        screen = self.get_object()
        parent_id = request.data.get('parent_id')
        old_index = request.data.get('old_index')
        new_index = request.data.get('new_index')

        if parent_id:
            parent = self._find_widget(screen.ui_structure, parent_id)
        else:
            parent = screen.ui_structure

        if not parent or 'children' not in parent:
            return Response({'error': 'Parent not found'}, status=404)

        # Reorder children
        children = parent['children']
        if 0 <= old_index < len(children) and 0 <= new_index < len(children):
            widget = children.pop(old_index)
            children.insert(new_index, widget)

        screen.save()
        return Response({'ui_structure': screen.ui_structure})

    @action(detail=True, methods=['post'], url_path='widgets/update-properties')
    def update_widget_properties(self, request, pk=None):
        """
        Update properties of a specific widget

        Request body:
        {
            "widget_id": "uuid",
            "properties": {
                "width": 300,
                "color": "#FF0000"
            }
        }
        """
        screen = self.get_object()
        widget_id = request.data.get('widget_id')
        properties = request.data.get('properties', {})

        widget = self._find_widget(screen.ui_structure, widget_id)
        if not widget:
            return Response({'error': 'Widget not found'}, status=404)

        # Update properties
        widget['properties'].update(properties)

        screen.save()
        return Response({'widget': widget})

    @action(detail=True, methods=['post'], url_path='widgets/batch-delete')
    def batch_delete_widgets(self, request, pk=None):
        """
        Delete multiple widgets at once

        Request body:
        {
            "widget_ids": ["uuid1", "uuid2", "uuid3"]
        }
        """
        screen = self.get_object()
        widget_ids = request.data.get('widget_ids', [])

        if not widget_ids:
            return Response({'error': 'widget_ids required'}, status=400)

        deleted_count = 0
        for widget_id in widget_ids:
            if screen.ui_structure.get('id') == widget_id:
                # Can't delete root in batch operation
                continue

            self._remove_widget_from_tree(screen.ui_structure, widget_id)
            deleted_count += 1

        screen.save()

        # Save to history
        if hasattr(screen, 'canvas_state'):
            screen.canvas_state.push_history(screen.ui_structure)

        return Response({
            'deleted_count': deleted_count,
            'ui_structure': screen.ui_structure
        })

    @action(detail=True, methods=['post'], url_path='widgets/batch-update')
    def batch_update_properties(self, request, pk=None):
        """
        Update properties for multiple widgets

        Request body:
        {
            "updates": [
                {
                    "widget_id": "uuid1",
                    "properties": {"color": "#FF0000"}
                },
                {
                    "widget_id": "uuid2",
                    "properties": {"fontSize": 18}
                }
            ]
        }
        """
        screen = self.get_object()
        updates = request.data.get('updates', [])

        updated_count = 0
        for update in updates:
            widget_id = update.get('widget_id')
            properties = update.get('properties', {})

            widget = self._find_widget(screen.ui_structure, widget_id)
            if widget:
                widget['properties'].update(properties)
                updated_count += 1

        screen.save()

        return Response({
            'updated_count': updated_count,
            'ui_structure': screen.ui_structure
        })

    # Helper methods
    def _find_widget(self, node, widget_id):
        """Recursively find widget by ID"""
        if not node or not isinstance(node, dict):
            return None

        if node.get('id') == widget_id:
            return node

        for child in node.get('children', []):
            result = self._find_widget(child, widget_id)
            if result:
                return result

        return None

    def _add_widget_to_parent(self, root, parent_id, widget, index):
        """Add widget to parent at specific index"""
        parent = self._find_widget(root, parent_id)
        if parent:
            if 'children' not in parent:
                parent['children'] = []
            parent['children'].insert(index, widget)
            return True
        return False

    def _remove_widget_from_tree(self, node, widget_id):
        """Remove widget from tree"""
        if 'children' in node:
            node['children'] = [
                child for child in node['children']
                if child.get('id') != widget_id
            ]
            for child in node['children']:
                self._remove_widget_from_tree(child, widget_id)

    def _extract_widget(self, root, widget_id):
        """Extract and remove widget from tree"""
        widget = self._find_widget(root, widget_id)
        if widget:
            # Deep copy the widget
            widget_copy = copy.deepcopy(widget)
            # Remove from tree
            self._remove_widget_from_tree(root, widget_id)
            return widget_copy
        return None


class CanvasStateViewSet(viewsets.ModelViewSet):
    serializer_class = CanvasStateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CanvasState.objects.filter(
            screen__project__user=self.request.user
        )

    @action(detail=False, methods=['get'])
    def by_screen(self, request):
        """Get canvas state for a specific screen"""
        screen_id = request.query_params.get('screen_id')
        if not screen_id:
            return Response({'error': 'screen_id required'}, status=400)

        state, created = CanvasState.objects.get_or_create(
            screen_id=screen_id
        )
        serializer = self.get_serializer(state)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def undo(self, request, pk=None):
        """Undo last action"""
        state = self.get_object()
        ui_structure = state.undo()

        if ui_structure:
            state.screen.ui_structure = ui_structure
            state.screen.save()
            return Response({'ui_structure': ui_structure})

        return Response({'error': 'Nothing to undo'}, status=400)

    @action(detail=True, methods=['post'])
    def redo(self, request, pk=None):
        """Redo last undone action"""
        state = self.get_object()
        ui_structure = state.redo()

        if ui_structure:
            state.screen.ui_structure = ui_structure
            state.screen.save()
            return Response({'ui_structure': ui_structure})

        return Response({'error': 'Nothing to redo'}, status=400)


class ValidationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def validate_structure(self, request):
        """Validate a UI structure"""
        structure = request.data.get('structure')
        if not structure:
            return Response({'valid': False, 'errors': ['No structure provided']}, status=400)

        valid, errors = WidgetValidator.validate_tree_structure(structure)
        return Response({
            'valid': valid,
            'errors': errors
        })

    @action(detail=False, methods=['post'])
    def can_add_child(self, request):
        """Check if a child can be added to parent"""
        parent_type = request.data.get('parent_type')
        child_type = request.data.get('child_type')

        if not parent_type or not child_type:
            return Response({'error': 'parent_type and child_type required'}, status=400)

        can_add, error = WidgetValidator.can_add_child(parent_type, child_type)
        return Response({
            'can_add': can_add,
            'error': error
        })

    @action(detail=False, methods=['post'])
    def validate_properties(self, request):
        """Validate widget properties"""
        widget_type = request.data.get('widget_type')
        properties = request.data.get('properties', {})

        if not widget_type:
            return Response({'error': 'widget_type required'}, status=400)

        valid, errors = WidgetValidator.validate_properties(widget_type, properties)
        return Response({
            'valid': valid,
            'errors': errors
        })


class ProjectAssetViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectAssetSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        project_id = self.request.query_params.get('project')
        queryset = ProjectAsset.objects.filter(
            project__user=self.request.user
        )
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset

    @action(detail=False, methods=['post'])
    def upload_image(self, request):
        """Upload image for Image widget"""
        project_id = request.data.get('project_id')
        file = request.FILES.get('file')

        if not project_id or not file:
            return Response({'error': 'project_id and file required'}, status=400)

        # Validate image
        if not file.content_type.startswith('image/'):
            return Response({'error': 'File must be an image'}, status=400)

        # Create asset
        asset = ProjectAsset.objects.create(
            project_id=project_id,
            name=file.name,
            asset_type='image',
            file=file,
            metadata={
                'size': file.size,
                'content_type': file.content_type
            }
        )

        serializer = self.get_serializer(asset)
        return Response(serializer.data)


class WidgetTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = WidgetTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = WidgetTemplate.objects.filter(
            Q(user=self.request.user) | Q(is_public=True)
        )

        # Optional filtering
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class StylePresetViewSet(viewsets.ModelViewSet):
    serializer_class = StylePresetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = StylePreset.objects.filter(
            Q(user=self.request.user) | Q(is_public=True)
        )

        # Optional filtering
        widget_type = self.request.query_params.get('widget_type')
        if widget_type:
            queryset = queryset.filter(widget_type=widget_type)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)