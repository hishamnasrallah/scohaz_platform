# dynamicflow/apis/workflow_container_views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Prefetch
import json
from datetime import datetime

from dynamicflow.models import (
    Workflow, WorkflowConnection, Page, Category, Field, Condition, FieldType
)
from dynamicflow.apis.workflow_container_serializers import (
    WorkflowSerializer, WorkflowListSerializer, WorkflowConnectionSerializer
)
from lookup.models import Lookup


class WorkflowViewSet(viewsets.ModelViewSet):
    """Main workflow management API"""
    queryset = Workflow.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['service', 'is_active', 'is_draft']
    search_fields = ['name', 'description']
    ordering = ['-updated_at']

    def get_queryset(self):
        """Override to add prefetch related for better performance"""
        queryset = super().get_queryset()

        if self.action == 'retrieve':
            # Prefetch all related data for detail view
            queryset = queryset.prefetch_related(
                Prefetch('pages', queryset=Page.objects.select_related('service', 'sequence_number', 'applicant_type')),
                Prefetch('categories', queryset=Category.objects.prefetch_related('page')),
                Prefetch('fields', queryset=Field.objects.select_related('_field_type', '_lookup', '_parent_field')),
                Prefetch('conditions', queryset=Condition.objects.select_related('target_field')),
                'connections'
            )

        return queryset

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

        try:
            with transaction.atomic():
                # Update workflow metadata
                workflow.name = data.get('name', workflow.name)
                workflow.description = data.get('description', workflow.description)
                workflow.metadata = data.get('metadata', workflow.metadata)
                workflow.canvas_state = data.get('canvas_state', workflow.canvas_state)
                workflow.is_active = data.get('is_active', workflow.is_active)
                workflow.is_draft = data.get('is_draft', workflow.is_draft)
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
                        # Merge root-level fields with properties for backward compatibility
                        merged_properties = properties.copy()

                        # Check if fields are at root level and merge them
                        root_fields = ['name', 'name_ara', 'description', 'description_ara',
                                       'service', 'service_id', 'sequence_number', 'sequence_number_id',
                                       'applicant_type', 'applicant_type_id', 'active_ind', 'is_hidden_page']

                        for field in root_fields:
                            if field in element_data and field not in merged_properties:
                                merged_properties[field] = element_data[field]

                        page_id = merged_properties.get('page_id') or element_data.get('page_id')
                        if page_id:
                            # Update existing page
                            page = Page.objects.get(id=page_id)
                            self._update_page(page, merged_properties, position, workflow)
                        else:
                            # Create new page
                            page = self._create_page(merged_properties, position, workflow)
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

        except Exception as e:
            return Response(
                {'error': f'Failed to save workflow: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _create_page(self, properties, position, workflow):
        """Helper to create a page"""
        # Handle service field
        service_value = properties.get('service')
        if isinstance(service_value, list):
            service_id = service_value[0] if service_value else None
        else:
            service_id = service_value

        # Handle sequence_number field
        seq_value = properties.get('sequence_number')
        if isinstance(seq_value, list):
            sequence_number_id = seq_value[0] if seq_value else None
        else:
            sequence_number_id = seq_value

        # Handle applicant_type field
        app_value = properties.get('applicant_type')
        if isinstance(app_value, list):
            applicant_type_id = app_value[0] if app_value else None
        else:
            applicant_type_id = app_value

        return Page.objects.create(
            workflow=workflow,
            name=properties.get('name', ''),
            name_ara=properties.get('name_ara', ''),
            description=properties.get('description', ''),
            description_ara=properties.get('description_ara', ''),
            service_id=service_id,
            sequence_number_id=sequence_number_id,
            applicant_type_id=applicant_type_id,
            position_x=position.get('x', 0),
            position_y=position.get('y', 0),
            is_expanded=properties.get('isExpanded', False),
            active_ind=properties.get('active_ind', True)
        )
    def _update_page(self, page, properties, position, workflow):
        """Helper to update a page"""
        page.workflow = workflow
        page.name = properties.get('name', page.name)
        page.name_ara = properties.get('name_ara', page.name_ara)
        page.description = properties.get('description', page.description)
        page.description_ara = properties.get('description_ara', page.description_ara)
        if 'service' in properties:
            service_value = properties['service']
            if isinstance(service_value, list):
                page.service_id = service_value[0] if service_value else None
            else:
                page.service_id = service_value
        if 'sequence_number' in properties:
            seq_value = properties['sequence_number']
            if isinstance(seq_value, list):
                page.sequence_number_id = seq_value[0] if seq_value else None
            else:
                page.sequence_number_id = seq_value
        if 'applicant_type' in properties:
            app_value = properties['applicant_type']
            if isinstance(app_value, list):
                page.applicant_type_id = app_value[0] if app_value else None
            else:
                page.applicant_type_id = app_value
        page.position_x = position.get('x', page.position_x)
        page.position_y = position.get('y', page.position_y)
        page.is_expanded = properties.get('isExpanded', page.is_expanded)
        page.active_ind = properties.get('active_ind', page.active_ind)
        page.save()

    def _create_category(self, properties, position, workflow):
        """Helper to create a category"""
        category = Category.objects.create(
            workflow=workflow,
            name=properties.get('name', ''),
            name_ara=properties.get('name_ara', ''),
            code=properties.get('code', ''),
            description=properties.get('description', ''),
            is_repeatable=properties.get('is_repeatable', False),
            relative_position_x=position.get('x', 0),
            relative_position_y=position.get('y', 0),
            active_ind=properties.get('active_ind', True)
        )
        return category

    def _update_category(self, category, properties, position, workflow):
        """Helper to update a category"""
        category.workflow = workflow
        category.name = properties.get('name', category.name)
        category.name_ara = properties.get('name_ara', category.name_ara)
        category.code = properties.get('code', category.code)
        category.description = properties.get('description', category.description)
        category.is_repeatable = properties.get('is_repeatable', category.is_repeatable)
        category.relative_position_x = position.get('x', category.relative_position_x)
        category.relative_position_y = position.get('y', category.relative_position_y)
        category.active_ind = properties.get('active_ind', category.active_ind)
        category.save()

    def _create_field(self, properties, position, workflow):
        """Helper to create a field"""
        field = Field.objects.create(
            workflow=workflow,
            _field_name=properties.get('_field_name', ''),
            _field_display_name=properties.get('_field_display_name', ''),
            _field_display_name_ara=properties.get('_field_display_name_ara', ''),
            _field_type_id=properties.get('_field_type'),
            _sequence=properties.get('_sequence'),
            _mandatory=properties.get('_mandatory', False),
            _is_hidden=properties.get('_is_hidden', False),
            _is_disabled=properties.get('_is_disabled', False),
            _lookup_id=properties.get('_lookup'),
            relative_position_x=position.get('x', 0),
            relative_position_y=position.get('y', 0),
            # Validation fields
            _max_length=properties.get('_max_length'),
            _min_length=properties.get('_min_length'),
            _regex_pattern=properties.get('_regex_pattern'),
            _allowed_characters=properties.get('_allowed_characters'),
            _forbidden_words=properties.get('_forbidden_words'),
            _value_greater_than=properties.get('_value_greater_than'),
            _value_less_than=properties.get('_value_less_than'),
            _integer_only=properties.get('_integer_only', False),
            _positive_only=properties.get('_positive_only', False),
            _date_greater_than=properties.get('_date_greater_than'),
            _date_less_than=properties.get('_date_less_than'),
            _future_only=properties.get('_future_only', False),
            _past_only=properties.get('_past_only', False),
            _file_types=properties.get('_file_types'),
            _max_file_size=properties.get('_max_file_size'),
            _image_max_width=properties.get('_image_max_width'),
            _image_max_height=properties.get('_image_max_height'),
            _max_selections=properties.get('_max_selections'),
            _min_selections=properties.get('_min_selections'),
            _precision=properties.get('_precision'),
            _unique=properties.get('_unique', False),
            _default_value=properties.get('_default_value'),
            _default_boolean=properties.get('_default_boolean', False),
            _coordinates_format=properties.get('_coordinates_format', False),
            _uuid_format=properties.get('_uuid_format', False),
            active_ind=properties.get('active_ind', True)
        )

        # Handle many-to-many relationships
        if 'service' in properties and properties['service']:
            services = properties['service'] if isinstance(properties['service'], list) else [properties['service']]
            field.service.set(services)

        if 'allowed_lookups' in properties and properties['allowed_lookups']:
            field.allowed_lookups.set(properties['allowed_lookups'])

        return field

    def _update_field(self, field, properties, position, workflow):
        """Helper to update a field"""
        field.workflow = workflow
        field._field_name = properties.get('_field_name', field._field_name)
        field._field_display_name = properties.get('_field_display_name', field._field_display_name)
        field._field_display_name_ara = properties.get('_field_display_name_ara', field._field_display_name_ara)
        if '_field_type' in properties:
            field._field_type_id = properties['_field_type']
        field._sequence = properties.get('_sequence', field._sequence)
        field._mandatory = properties.get('_mandatory', field._mandatory)
        field._is_hidden = properties.get('_is_hidden', field._is_hidden)
        field._is_disabled = properties.get('_is_disabled', field._is_disabled)
        if '_lookup' in properties:
            field._lookup_id = properties['_lookup']
        field.relative_position_x = position.get('x', field.relative_position_x)
        field.relative_position_y = position.get('y', field.relative_position_y)
        field.active_ind = properties.get('active_ind', field.active_ind)

        # Update validation fields
        validation_fields = [
            '_max_length', '_min_length', '_regex_pattern', '_allowed_characters',
            '_forbidden_words', '_value_greater_than', '_value_less_than',
            '_integer_only', '_positive_only', '_date_greater_than', '_date_less_than',
            '_future_only', '_past_only', '_file_types', '_max_file_size',
            '_image_max_width', '_image_max_height', '_max_selections', '_min_selections',
            '_precision', '_unique', '_default_value', '_default_boolean',
            '_coordinates_format', '_uuid_format'
        ]

        for vfield in validation_fields:
            if vfield in properties:
                setattr(field, vfield, properties[vfield])

        field.save()

        # Update many-to-many relationships
        if 'service' in properties and properties['service'] is not None:
            services = properties['service'] if isinstance(properties['service'], list) else [properties['service']]
            field.service.set(services)

        if 'allowed_lookups' in properties and properties['allowed_lookups'] is not None:
            field.allowed_lookups.set(properties['allowed_lookups'])

    def _create_condition(self, properties, position, workflow):
        """Helper to create a condition"""
        return Condition.objects.create(
            workflow=workflow,
            target_field_id=properties.get('target_field_id') or properties.get('target_field'),
            condition_logic=properties.get('condition_logic', []),
            position_x=position.get('x', 0),
            position_y=position.get('y', 0),
            active_ind=properties.get('active_ind', True)
        )

    def _update_condition(self, condition, properties, position, workflow):
        """Helper to update a condition"""
        condition.workflow = workflow
        if 'target_field_id' in properties or 'target_field' in properties:
            condition.target_field_id = properties.get('target_field_id') or properties.get('target_field')
        condition.condition_logic = properties.get('condition_logic', condition.condition_logic)
        condition.position_x = position.get('x', condition.position_x)
        condition.position_y = position.get('y', condition.position_y)
        condition.active_ind = properties.get('active_ind', condition.active_ind)
        condition.save()

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

        try:
            with transaction.atomic():
                # Create new workflow
                new_workflow = Workflow.objects.create(
                    name=request.data.get('name', f"{workflow.name} (Copy)"),
                    description=request.data.get('description', workflow.description),
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
                        is_expanded=page.is_expanded,
                        active_ind=page.active_ind
                    )
                    element_mapping[('page', page.id)] = new_page.id

                # Clone categories
                for category in workflow.categories.all():
                    new_category = Category.objects.create(
                        workflow=new_workflow,
                        name=category.name,
                        name_ara=category.name_ara,
                        code=category.code,
                        description=category.description,
                        is_repeatable=category.is_repeatable,
                        relative_position_x=category.relative_position_x,
                        relative_position_y=category.relative_position_y,
                        active_ind=category.active_ind
                    )
                    # Clone many-to-many relationships
                    for page in category.page.all():
                        if ('page', page.id) in element_mapping:
                            new_page_id = element_mapping[('page', page.id)]
                            new_category.page.add(new_page_id)

                    element_mapping[('category', category.id)] = new_category.id

                # Clone fields
                for field in workflow.fields.all():
                    new_field = Field.objects.create(
                        workflow=new_workflow,
                        _field_name=field._field_name,
                        _field_display_name=field._field_display_name,
                        _field_display_name_ara=field._field_display_name_ara,
                        _field_type=field._field_type,
                        _sequence=field._sequence,
                        _mandatory=field._mandatory,
                        _is_hidden=field._is_hidden,
                        _is_disabled=field._is_disabled,
                        _lookup=field._lookup,
                        relative_position_x=field.relative_position_x,
                        relative_position_y=field.relative_position_y,
                        # Clone all validation fields
                        _max_length=field._max_length,
                        _min_length=field._min_length,
                        _regex_pattern=field._regex_pattern,
                        _allowed_characters=field._allowed_characters,
                        _forbidden_words=field._forbidden_words,
                        _value_greater_than=field._value_greater_than,
                        _value_less_than=field._value_less_than,
                        _integer_only=field._integer_only,
                        _positive_only=field._positive_only,
                        _date_greater_than=field._date_greater_than,
                        _date_less_than=field._date_less_than,
                        _future_only=field._future_only,
                        _past_only=field._past_only,
                        _file_types=field._file_types,
                        _max_file_size=field._max_file_size,
                        _image_max_width=field._image_max_width,
                        _image_max_height=field._image_max_height,
                        _max_selections=field._max_selections,
                        _min_selections=field._min_selections,
                        _precision=field._precision,
                        _unique=field._unique,
                        _default_value=field._default_value,
                        _default_boolean=field._default_boolean,
                        _coordinates_format=field._coordinates_format,
                        _uuid_format=field._uuid_format,
                        active_ind=field.active_ind
                    )

                    # Clone many-to-many relationships
                    new_field.service.set(field.service.all())
                    new_field.allowed_lookups.set(field.allowed_lookups.all())

                    # Clone category relationships
                    for category in field._category.all():
                        if ('category', category.id) in element_mapping:
                            new_category_id = element_mapping[('category', category.id)]
                            new_field._category.add(new_category_id)

                    element_mapping[('field', field.id)] = new_field.id

                # Handle parent-child field relationships
                for field in workflow.fields.filter(_parent_field__isnull=False):
                    if ('field', field.id) in element_mapping and ('field', field._parent_field.id) in element_mapping:
                        new_field_id = element_mapping[('field', field.id)]
                        new_parent_id = element_mapping[('field', field._parent_field.id)]
                        Field.objects.filter(id=new_field_id).update(_parent_field_id=new_parent_id)

                # Clone conditions
                for condition in workflow.conditions.all():
                    new_target_field_id = None
                    if condition.target_field_id and ('field', condition.target_field_id) in element_mapping:
                        new_target_field_id = element_mapping[('field', condition.target_field_id)]

                    new_condition = Condition.objects.create(
                        workflow=new_workflow,
                        target_field_id=new_target_field_id,
                        condition_logic=condition.condition_logic,
                        position_x=condition.position_x,
                        position_y=condition.position_y,
                        active_ind=condition.active_ind
                    )
                    element_mapping[('condition', condition.id)] = new_condition.id

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

        except Exception as e:
            return Response(
                {'error': f'Failed to clone workflow: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export workflow as service flow format"""
        workflow = self.get_object()

        # Convert to service flow format
        service_flow = {
            "service_code": workflow.service_code,
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "workflow_version": workflow.version,
            "metadata": workflow.metadata,
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
                "applicant_type": {
                    "id": page.applicant_type.id if page.applicant_type else None,
                    "name": page.applicant_type.name if page.applicant_type else None,
                    "code": page.applicant_type.code if page.applicant_type else None
                },
                "position": {"x": page.position_x, "y": page.position_y},
                "categories": []
            }

            for category in page.category_set.filter(workflow=workflow):
                category_data = {
                    "id": category.id,
                    "name": category.name,
                    "name_ara": category.name_ara,
                    "code": category.code,
                    "description": category.description,
                    "repeatable": category.is_repeatable,
                    "position": {"x": category.relative_position_x, "y": category.relative_position_y},
                    "fields": []
                }

                for field in category.field_set.filter(workflow=workflow):
                    field_data = {
                        "name": field._field_name,
                        "field_id": field.id,
                        "display_name": field._field_display_name,
                        "display_name_ara": field._field_display_name_ara,
                        "field_type": field._field_type.name if field._field_type else None,
                        "field_type_code": field._field_type.code if field._field_type else None,
                        "mandatory": field._mandatory,
                        "is_hidden": field._is_hidden,
                        "is_disabled": field._is_disabled,
                        "sequence": field._sequence,
                        "position": {"x": field.relative_position_x, "y": field.relative_position_y},
                        "visibility_conditions": []
                    }

                    # Add validation properties
                    if field._max_length:
                        field_data["max_length"] = field._max_length
                    if field._min_length:
                        field_data["min_length"] = field._min_length
                    if field._regex_pattern:
                        field_data["regex_pattern"] = field._regex_pattern
                    if field._allowed_characters:
                        field_data["allowed_characters"] = field._allowed_characters
                    if field._forbidden_words:
                        field_data["forbidden_words"] = field._forbidden_words
                    if field._value_greater_than is not None:
                        field_data["value_greater_than"] = field._value_greater_than
                    if field._value_less_than is not None:
                        field_data["value_less_than"] = field._value_less_than
                    if field._integer_only:
                        field_data["integer_only"] = field._integer_only
                    if field._positive_only:
                        field_data["positive_only"] = field._positive_only
                    if field._date_greater_than:
                        field_data["date_greater_than"] = str(field._date_greater_than)
                    if field._date_less_than:
                        field_data["date_less_than"] = str(field._date_less_than)
                    if field._future_only:
                        field_data["future_only"] = field._future_only
                    if field._past_only:
                        field_data["past_only"] = field._past_only
                    if field._default_boolean is not None:
                        field_data["default_boolean"] = field._default_boolean
                    if field._file_types:
                        field_data["file_types"] = field._file_types
                    if field._max_file_size:
                        field_data["max_file_size"] = field._max_file_size
                    if field._image_max_width:
                        field_data["image_max_width"] = field._image_max_width
                    if field._image_max_height:
                        field_data["image_max_height"] = field._image_max_height
                    if field._max_selections:
                        field_data["max_selections"] = field._max_selections
                    if field._min_selections:
                        field_data["min_selections"] = field._min_selections
                    if field._precision:
                        field_data["precision"] = field._precision
                    if field._unique:
                        field_data["unique"] = field._unique
                    if field._default_value:
                        field_data["default_value"] = field._default_value
                    if field._coordinates_format:
                        field_data["coordinates_format"] = field._coordinates_format
                    if field._uuid_format:
                        field_data["uuid_format"] = field._uuid_format

                    # Add lookup info
                    if field._lookup:
                        field_data["lookup"] = {
                            "id": field._lookup.id,
                            "name": field._lookup.name,
                            "code": field._lookup.code
                        }

                    # Add conditions
                    for condition in field.conditions.filter(workflow=workflow):
                        field_data["visibility_conditions"].append({
                            "id": condition.id,
                            "condition_logic": condition.condition_logic,
                            "position": {"x": condition.position_x, "y": condition.position_y}
                        })

                    # Add sub-fields
                    sub_fields = field.sub_fields.filter(workflow=workflow)
                    if sub_fields.exists():
                        field_data["sub_fields"] = []
                        for sub_field in sub_fields:
                            sub_field_data = {
                                "name": sub_field._field_name,
                                "field_id": sub_field.id,
                                "display_name": sub_field._field_display_name,
                                "field_type": sub_field._field_type.name if sub_field._field_type else None
                            }
                            field_data["sub_fields"].append(sub_field_data)

                    category_data["fields"].append(field_data)

                page_data["categories"].append(category_data)

            service_flow["pages"].append(page_data)

        # Add connections
        connections = []
        for connection in workflow.connections.all():
            connections.append({
                "source_type": connection.source_type,
                "source_id": connection.source_id,
                "target_type": connection.target_type,
                "target_id": connection.target_id,
                "metadata": connection.connection_metadata
            })
        service_flow["connections"] = connections

        return Response({"service_flow": service_flow})

    @action(detail=False, methods=['post'])
    def import_service_flow(self, request):
        """Import service flow to create a new workflow"""
        service_flow_data = request.data.get('service_flow')
        workflow_name = request.data.get('workflow_name', 'Imported Workflow')

        if not service_flow_data:
            return Response(
                {'error': 'service_flow data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Handle both single service flow and array format
                if isinstance(service_flow_data, list):
                    service_flow = service_flow_data[0] if service_flow_data else {}
                else:
                    service_flow = service_flow_data

                # Create workflow
                workflow = Workflow.objects.create(
                    name=workflow_name,
                    description=request.data.get('description', ''),
                    service_code=service_flow.get('service_code'),
                    is_draft=True,
                    created_by=request.user,
                    updated_by=request.user,
                    metadata={'imported_from': 'service_flow', 'import_date': str(datetime.now())}
                )

                # Try to find and set the service
                if service_flow.get('service_code'):
                    try:
                        service = Lookup.objects.get(
                            code=service_flow['service_code'],
                            parent_lookup__name='Service'
                        )
                        workflow.service = service
                        workflow.save()
                    except Lookup.DoesNotExist:
                        pass

                # Import pages and their children
                element_mapping = {}  # Map old IDs to new IDs

                for page_data in service_flow.get('pages', []):
                    # Create page
                    page = Page.objects.create(
                        workflow=workflow,
                        name=page_data.get('name', ''),
                        name_ara=page_data.get('name_ara', ''),
                        description=page_data.get('description', ''),
                        description_ara=page_data.get('description_ara', ''),
                        position_x=page_data.get('position', {}).get('x', 0),
                        position_y=page_data.get('position', {}).get('y', 0),
                        active_ind=not page_data.get('is_hidden_page', False)
                    )

                    # Map sequence number
                    if page_data.get('sequence_number'):
                        try:
                            seq = Lookup.objects.get(
                                code=page_data['sequence_number'],
                                parent_lookup__name='Flow Step'
                            )
                            page.sequence_number = seq
                        except Lookup.DoesNotExist:
                            pass

                    # Map applicant type
                    applicant_type_data = page_data.get('applicant_type', {})
                    if applicant_type_data and applicant_type_data.get('code'):
                        try:
                            app_type = Lookup.objects.get(
                                code=applicant_type_data['code'],
                                parent_lookup__name='Service Applicant Type'
                            )
                            page.applicant_type = app_type
                        except Lookup.DoesNotExist:
                            pass

                    # Set service from workflow
                    page.service = workflow.service
                    page.save()

                    if page_data.get('page_id'):
                        element_mapping[('page', page_data['page_id'])] = page.id

                    # Import categories
                    for category_data in page_data.get('categories', []):
                        category = Category.objects.create(
                            workflow=workflow,
                            name=category_data.get('name', ''),
                            name_ara=category_data.get('name_ara', ''),
                            code=category_data.get('code', ''),
                            description=category_data.get('description', ''),
                            is_repeatable=category_data.get('repeatable', False),
                            relative_position_x=category_data.get('position', {}).get('x', 0),
                            relative_position_y=category_data.get('position', {}).get('y', 0),
                            active_ind=True
                        )
                        category.page.add(page)

                        if category_data.get('id'):
                            element_mapping[('category', category_data['id'])] = category.id

                        # Import fields
                        for field_data in category_data.get('fields', []):
                            field = Field.objects.create(
                                workflow=workflow,
                                _field_name=field_data.get('name', ''),
                                _field_display_name=field_data.get('display_name', ''),
                                _field_display_name_ara=field_data.get('display_name_ara', ''),
                                _sequence=field_data.get('sequence'),
                                _mandatory=field_data.get('mandatory', False),
                                _is_hidden=field_data.get('is_hidden', False),
                                _is_disabled=field_data.get('is_disabled', False),
                                relative_position_x=field_data.get('position', {}).get('x', 0),
                                relative_position_y=field_data.get('position', {}).get('y', 0),
                                active_ind=True,
                                # Import validation fields
                                _max_length=field_data.get('max_length'),
                                _min_length=field_data.get('min_length'),
                                _regex_pattern=field_data.get('regex_pattern'),
                                _allowed_characters=field_data.get('allowed_characters'),
                                _forbidden_words=field_data.get('forbidden_words'),
                                _value_greater_than=field_data.get('value_greater_than'),
                                _value_less_than=field_data.get('value_less_than'),
                                _integer_only=field_data.get('integer_only', False),
                                _positive_only=field_data.get('positive_only', False),
                                _date_greater_than=field_data.get('date_greater_than'),
                                _date_less_than=field_data.get('date_less_than'),
                                _future_only=field_data.get('future_only', False),
                                _past_only=field_data.get('past_only', False),
                                _file_types=field_data.get('file_types'),
                                _max_file_size=field_data.get('max_file_size'),
                                _image_max_width=field_data.get('image_max_width'),
                                _image_max_height=field_data.get('image_max_height'),
                                _max_selections=field_data.get('max_selections'),
                                _min_selections=field_data.get('min_selections'),
                                _precision=field_data.get('precision'),
                                _unique=field_data.get('unique', False),
                                _default_value=field_data.get('default_value'),
                                _default_boolean=field_data.get('default_boolean', False),
                                _coordinates_format=field_data.get('coordinates_format', False),
                                _uuid_format=field_data.get('uuid_format', False)
                            )

                            # Map field type
                            if field_data.get('field_type') or field_data.get('field_type_code'):
                                try:
                                    if field_data.get('field_type_code'):
                                        field_type = FieldType.objects.get(code=field_data['field_type_code'])
                                    else:
                                        field_type = FieldType.objects.get(name__iexact=field_data['field_type'])
                                    field._field_type = field_type
                                except FieldType.DoesNotExist:
                                    pass

                            # Map lookup
                            lookup_data = field_data.get('lookup', {})
                            if lookup_data and lookup_data.get('code'):
                                try:
                                    lookup = Lookup.objects.get(code=lookup_data['code'])
                                    field._lookup = lookup
                                except Lookup.DoesNotExist:
                                    pass

                            field.save()
                            field._category.add(category)

                            # Add service reference
                            if workflow.service:
                                field.service.add(workflow.service)

                            if field_data.get('field_id'):
                                element_mapping[('field', field_data['field_id'])] = field.id

                            # Import conditions
                            for condition_data in field_data.get('visibility_conditions', []):
                                condition = Condition.objects.create(
                                    workflow=workflow,
                                    target_field=field,
                                    condition_logic=condition_data.get('condition_logic', []),
                                    position_x=condition_data.get('position', {}).get('x', 0),
                                    position_y=condition_data.get('position', {}).get('y', 0),
                                    active_ind=True
                                )
                                if condition_data.get('id'):
                                    element_mapping[('condition', condition_data['id'])] = condition.id

                # Import connections if provided
                for connection_data in service_flow.get('connections', []):
                    source_key = (connection_data['source_type'], connection_data['source_id'])
                    target_key = (connection_data['target_type'], connection_data['target_id'])

                    if source_key in element_mapping and target_key in element_mapping:
                        WorkflowConnection.objects.create(
                            workflow=workflow,
                            source_type=connection_data['source_type'],
                            source_id=element_mapping[source_key],
                            target_type=connection_data['target_type'],
                            target_id=element_mapping[target_key],
                            connection_metadata=connection_data.get('metadata', {})
                        )

            return Response(WorkflowSerializer(workflow).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Failed to import workflow: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a workflow and optionally deactivate others for the same service"""
        workflow = self.get_object()

        deactivate_others = request.data.get('deactivate_others', False)

        try:
            with transaction.atomic():
                if deactivate_others and workflow.service:
                    # Deactivate all other workflows for the same service
                    Workflow.objects.filter(
                        service=workflow.service,
                        is_active=True
                    ).exclude(id=workflow.id).update(is_active=False)

                workflow.is_active = True
                workflow.is_draft = False
                workflow.updated_by = request.user
                workflow.save()

            return Response({
                'message': 'Workflow activated successfully',
                'workflow': WorkflowSerializer(workflow).data
            })

        except Exception as e:
            return Response(
                {'error': f'Failed to activate workflow: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a workflow"""
        workflow = self.get_object()

        workflow.is_active = False
        workflow.updated_by = request.user
        workflow.save()

        return Response({
            'message': 'Workflow deactivated successfully',
            'workflow': WorkflowSerializer(workflow).data
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get workflow statistics"""
        stats = {
            'total_workflows': Workflow.objects.count(),
            'active_workflows': Workflow.objects.filter(is_active=True).count(),
            'draft_workflows': Workflow.objects.filter(is_draft=True).count(),
            'by_service': {},
            'recent_updates': []
        }

        # Group by service
        service_stats = Workflow.objects.values('service__name').annotate(
            count=Count('id')
        ).order_by('-count')

        for stat in service_stats:
            if stat['service__name']:
                stats['by_service'][stat['service__name']] = stat['count']

        # Recent updates
        recent = Workflow.objects.order_by('-updated_at')[:5]
        stats['recent_updates'] = WorkflowListSerializer(recent, many=True).data

        return Response(stats)

    @action(detail=True, methods=['get'])
    def validate(self, request, pk=None):
        """Validate workflow structure and return any issues"""
        workflow = self.get_object()
        issues = []
        warnings = []

        # Check if workflow has at least one page
        if not workflow.pages.exists():
            issues.append("Workflow must have at least one page")

        # Check each page
        for page in workflow.pages.all():
            if not page.name:
                issues.append(f"Page {page.id} is missing a name")

            if not page.category_set.exists():
                warnings.append(f"Page '{page.name}' has no categories")

            # Check each category
            for category in page.category_set.filter(workflow=workflow):
                if not category.name:
                    issues.append(f"Category {category.id} is missing a name")

                if not category.field_set.exists():
                    warnings.append(f"Category '{category.name}' has no fields")

                # Check each field
                for field in category.field_set.filter(workflow=workflow):
                    if not field._field_name:
                        issues.append(f"Field {field.id} is missing a name")

                    if not field._field_type:
                        issues.append(f"Field '{field._field_name}' is missing a field type")

                    # Check field validations consistency
                    if field._min_length and field._max_length:
                        if field._min_length > field._max_length:
                            issues.append(f"Field '{field._field_name}': min_length cannot be greater than max_length")

                    if field._value_greater_than is not None and field._value_less_than is not None:
                        if field._value_greater_than >= field._value_less_than:
                            issues.append(f"Field '{field._field_name}': value_greater_than must be less than value_less_than")

        # Check conditions reference valid fields
        for condition in workflow.conditions.all():
            if not condition.target_field:
                issues.append(f"Condition {condition.id} has no target field")
            elif condition.target_field.workflow != workflow:
                issues.append(f"Condition {condition.id} references a field from another workflow")

        return Response({
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        })

    @action(detail=True, methods=['post'])
    def duplicate_check(self, request, pk=None):
        """Check if there are duplicate field names in the workflow"""
        workflow = self.get_object()

        field_names = {}
        duplicates = []

        for field in workflow.fields.all():
            if field._field_name in field_names:
                duplicates.append({
                    'field_name': field._field_name,
                    'field_ids': [field_names[field._field_name], field.id]
                })
            else:
                field_names[field._field_name] = field.id

        return Response({
            'has_duplicates': len(duplicates) > 0,
            'duplicates': duplicates
        })

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Get a preview of the workflow structure"""
        workflow = self.get_object()

        structure = {
            'workflow': {
                'id': workflow.id,
                'name': workflow.name,
                'version': workflow.version,
                'is_active': workflow.is_active,
                'is_draft': workflow.is_draft
            },
            'pages': []
        }

        for page in workflow.pages.all().order_by('sequence_number__code'):
            page_info = {
                'name': page.name,
                'sequence': page.sequence_number.code if page.sequence_number else None,
                'categories': []
            }

            for category in page.category_set.filter(workflow=workflow):
                category_info = {
                    'name': category.name,
                    'fields': []
                }

                for field in category.field_set.filter(workflow=workflow).order_by('_sequence'):
                    field_info = {
                        'name': field._field_name,
                        'type': field._field_type.name if field._field_type else None,
                        'mandatory': field._mandatory
                    }
                    category_info['fields'].append(field_info)

                page_info['categories'].append(category_info)

            structure['pages'].append(page_info)

        return Response(structure)