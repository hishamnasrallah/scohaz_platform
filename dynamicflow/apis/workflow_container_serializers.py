# dynamicflow/apis/workflow_container_serializers.py

from rest_framework import serializers
from dynamicflow.models import Workflow, WorkflowConnection
from dynamicflow.apis.workflow_serializers import (
    WorkflowPageSerializer, WorkflowCategorySerializer,
    WorkflowFieldSerializer, WorkflowConditionSerializer
)


class WorkflowConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowConnection
        fields = ['id', 'source_type', 'source_id', 'target_type', 'target_id', 'connection_metadata']


class WorkflowSerializer(serializers.ModelSerializer):
    """Main workflow serializer"""
    pages = WorkflowPageSerializer(many=True, read_only=True)
    categories = WorkflowCategorySerializer(many=True, read_only=True)
    fields = WorkflowFieldSerializer(many=True, read_only=True)
    conditions = WorkflowConditionSerializer(many=True, read_only=True)
    connections = WorkflowConnectionSerializer(many=True, read_only=True)

    service_name = serializers.CharField(source='service.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'service', 'service_code', 'service_name',
            'is_active', 'is_draft', 'version', 'metadata', 'canvas_state',
            'pages', 'categories', 'fields', 'conditions', 'connections',
            'created_by', 'created_by_name', 'updated_by', 'updated_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']


class WorkflowListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing workflows"""
    service_name = serializers.CharField(source='service.name', read_only=True)
    element_count = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'service', 'service_code', 'service_name',
            'is_active', 'is_draft', 'version', 'element_count',
            'created_at', 'updated_at'
        ]

    def get_element_count(self, obj):
        return {
            'pages': obj.pages.count(),
            'categories': obj.categories.count(),
            'fields': obj.fields.count(),
            'conditions': obj.conditions.count()
        }


# dynamicflow/apis/workflow_container_views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from dynamicflow.models import (
    Workflow, WorkflowConnection, Page, Category, Field, Condition
)
from dynamicflow.apis.workflow_container_serializers import (
    WorkflowSerializer, WorkflowListSerializer, WorkflowConnectionSerializer
)


class WorkflowViewSet(viewsets.ModelViewSet):
    """Main workflow management API"""
    queryset = Workflow.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['service', 'is_active', 'is_draft']
    search_fields = ['name', 'description']
    ordering = ['-updated_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowListSerializer
        return WorkflowSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=['post'])
    def save_complete_workflow(self, request, pk=None):
        """
        Save complete workflow with all elements in a single transaction
        """
        workflow = self.get_object()
        data = request.data

        with transaction.atomic():
            # Update workflow metadata
            workflow.name = data.get('name', workflow.name)
            workflow.description = data.get('description', workflow.description)
            workflow.metadata = data.get('metadata', workflow.metadata)
            workflow.canvas_state = data.get('canvas_state', workflow.canvas_state)
            workflow.updated_by = request.user
            workflow.save()

            # Clear existing connections
            workflow.connections.all().delete()

            # Process elements
            elements_data = data.get('elements', [])
            element_mapping = {}  # Map frontend IDs to backend IDs

            # First pass: Create/update all elements
            for element_data in elements_data:
                element_type = element_data.get('type')
                frontend_id = element_data.get('id')
                properties = element_data.get('properties', {})
                position = element_data.get('position', {})

                if element_type == 'page':
                    page_id = properties.get('page_id')
                    if page_id:
                        # Update existing page
                        page = Page.objects.get(id=page_id)
                        self._update_page(page, properties, position, workflow)
                    else:
                        # Create new page
                        page = self._create_page(properties, position, workflow)
                    element_mapping[frontend_id] = ('page', page.id)

                elif element_type == 'category':
                    category_id = properties.get('category_id')
                    if category_id:
                        category = Category.objects.get(id=category_id)
                        self._update_category(category, properties, position, workflow)
                    else:
                        category = self._create_category(properties, position, workflow)
                    element_mapping[frontend_id] = ('category', category.id)

                elif element_type == 'field':
                    field_id = properties.get('_field_id')
                    if field_id:
                        field = Field.objects.get(id=field_id)
                        self._update_field(field, properties, position, workflow)
                    else:
                        field = self._create_field(properties, position, workflow)
                    element_mapping[frontend_id] = ('field', field.id)

                elif element_type == 'condition':
                    condition_id = properties.get('condition_id')
                    if condition_id:
                        condition = Condition.objects.get(id=condition_id)
                        self._update_condition(condition, properties, position, workflow)
                    else:
                        condition = self._create_condition(properties, position, workflow)
                    element_mapping[frontend_id] = ('condition', condition.id)

            # Second pass: Handle parent-child relationships
            for element_data in elements_data:
                frontend_id = element_data.get('id')
                parent_id = element_data.get('parentId')
                children = element_data.get('children', [])

                if parent_id and frontend_id in element_mapping:
                    # Set parent relationship
                    element_type, element_id = element_mapping[frontend_id]
                    parent_type, parent_backend_id = element_mapping.get(parent_id, (None, None))

                    if parent_type == 'page' and element_type == 'category':
                        category = Category.objects.get(id=element_id)
                        category.page.add(parent_backend_id)
                    elif parent_type == 'category' and element_type == 'field':
                        field = Field.objects.get(id=element_id)
                        field._category.add(parent_backend_id)

            # Save connections
            connections_data = data.get('connections', [])
            for conn_data in connections_data:
                source_id = conn_data.get('sourceId')
                target_id = conn_data.get('targetId')

                if source_id in element_mapping and target_id in element_mapping:
                    source_type, source_backend_id = element_mapping[source_id]
                    target_type, target_backend_id = element_mapping[target_id]

                    WorkflowConnection.objects.create(
                        workflow=workflow,
                        source_type=source_type,
                        source_id=source_backend_id,
                        target_type=target_type,
                        target_id=target_backend_id,
                        connection_metadata=conn_data.get('metadata', {})
                    )

            # Handle deletions
            deleted_elements = data.get('deleted_elements', {})
            self._handle_deletions(deleted_elements, workflow)

        return Response(WorkflowSerializer(workflow).data)

    def _create_page(self, properties, position, workflow):
        """Helper to create a page"""
        return Page.objects.create(
            workflow=workflow,
            name=properties.get('name', ''),
            name_ara=properties.get('name_ara', ''),
            description=properties.get('description', ''),
            description_ara=properties.get('description_ara', ''),
            service_id=properties.get('service'),
            sequence_number_id=properties.get('sequence_number'),
            applicant_type_id=properties.get('applicant_type'),
            position_x=position.get('x', 0),
            position_y=position.get('y', 0),
            is_expanded=properties.get('isExpanded', False)
        )

    def _update_page(self, page, properties, position, workflow):
        """Helper to update a page"""
        page.workflow = workflow
        page.name = properties.get('name', page.name)
        page.name_ara = properties.get('name_ara', page.name_ara)
        page.description = properties.get('description', page.description)
        page.description_ara = properties.get('description_ara', page.description_ara)
        if 'service' in properties:
            page.service_id = properties['service']
        if 'sequence_number' in properties:
            page.sequence_number_id = properties['sequence_number']
        if 'applicant_type' in properties:
            page.applicant_type_id = properties['applicant_type']
        page.position_x = position.get('x', page.position_x)
        page.position_y = position.get('y', page.position_y)
        page.is_expanded = properties.get('isExpanded', page.is_expanded)
        page.save()

    # Similar helper methods for category, field, condition...

    def _handle_deletions(self, deleted_elements, workflow):
        """Handle deletion of removed elements"""
        # Delete conditions
        if 'conditions' in deleted_elements:
            Condition.objects.filter(
                id__in=deleted_elements['conditions'],
                workflow=workflow
            ).delete()

        # Delete fields
        if 'fields' in deleted_elements:
            Field.objects.filter(
                id__in=deleted_elements['fields'],
                workflow=workflow
            ).delete()

        # Delete categories
        if 'categories' in deleted_elements:
            Category.objects.filter(
                id__in=deleted_elements['categories'],
                workflow=workflow
            ).delete()

        # Delete pages
        if 'pages' in deleted_elements:
            Page.objects.filter(
                id__in=deleted_elements['pages'],
                workflow=workflow
            ).delete()

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone workflow as a new version or separate workflow"""
        workflow = self.get_object()

        with transaction.atomic():
            # Create new workflow
            new_workflow = Workflow.objects.create(
                name=request.data.get('name', f"{workflow.name} (Copy)"),
                description=workflow.description,
                service=workflow.service,
                service_code=workflow.service_code,
                is_draft=True,
                version=request.data.get('as_new_version', False) and workflow.version + 1 or 1,
                metadata=workflow.metadata,
                canvas_state=workflow.canvas_state,
                created_by=request.user,
                updated_by=request.user
            )

            # Clone all elements
            element_mapping = {}

            # Clone pages
            for page in workflow.pages.all():
                new_page = Page.objects.create(
                    workflow=new_workflow,
                    name=page.name,
                    name_ara=page.name_ara,
                    description=page.description,
                    description_ara=page.description_ara,
                    service=page.service,
                    sequence_number=page.sequence_number,
                    applicant_type=page.applicant_type,
                    position_x=page.position_x,
                    position_y=page.position_y,
                    is_expanded=page.is_expanded
                )
                element_mapping[('page', page.id)] = new_page.id

            # Similar cloning for categories, fields, conditions...

            # Clone connections
            for connection in workflow.connections.all():
                source_key = (connection.source_type, connection.source_id)
                target_key = (connection.target_type, connection.target_id)

                if source_key in element_mapping and target_key in element_mapping:
                    WorkflowConnection.objects.create(
                        workflow=new_workflow,
                        source_type=connection.source_type,
                        source_id=element_mapping[source_key],
                        target_type=connection.target_type,
                        target_id=element_mapping[target_key],
                        connection_metadata=connection.connection_metadata
                    )

        return Response(WorkflowSerializer(new_workflow).data)

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export workflow as service flow format"""
        workflow = self.get_object()

        # Convert to service flow format
        service_flow = {
            "service_code": workflow.service_code,
            "pages": []
        }

        for page in workflow.pages.all().order_by('sequence_number__code'):
            page_data = {
                "sequence_number": page.sequence_number.code if page.sequence_number else None,
                "name": page.name,
                "name_ara": page.name_ara,
                "description": page.description,
                "description_ara": page.description_ara,
                "is_hidden_page": not page.active_ind,
                "page_id": page.id,
                "categories": []
            }

            for category in page.category_set.filter(workflow=workflow):
                category_data = {
                    "id": category.id,
                    "name": category.name,
                    "name_ara": category.name_ara,
                    "repeatable": category.is_repeatable,
                    "fields": []
                }

                for field in category.field_set.filter(workflow=workflow):
                    field_data = {
                        "name": field._field_name,
                        "field_id": field.id,
                        "display_name": field._field_display_name,
                        "display_name_ara": field._field_display_name_ara,
                        "field_type": field._field_type.name if field._field_type else None,
                        "mandatory": field._mandatory,
                        "is_hidden": field._is_hidden,
                        "is_disabled": field._is_disabled,
                        "visibility_conditions": []
                    }

                    # Add conditions
                    for condition in field.conditions.filter(workflow=workflow):
                        field_data["visibility_conditions"].append({
                            "condition_logic": condition.condition_logic
                        })

                    category_data["fields"].append(field_data)

                page_data["categories"].append(category_data)

            service_flow["pages"].append(page_data)

        return Response({"service_flow": [service_flow]})