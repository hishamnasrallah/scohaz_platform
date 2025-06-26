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
            relative_position_y=position.get('y', 0)
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
        )
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

    def _create_condition(self, properties, position, workflow):
        """Helper to create a condition"""
        return Condition.objects.create(
            workflow=workflow,
            target_field_id=properties.get('target_field_id') or properties.get('target_field'),
            condition_logic=properties.get('condition_logic', []),
            position_x=position.get('x', 0),
            position_y=position.get('y', 0)
        )

    def _update_condition(self, condition, properties, position, workflow):
        """Helper to update a condition"""
        condition.workflow = workflow
        if 'target_field_id' in properties or 'target_field' in properties:
            condition.target_field_id = properties.get('target_field_id') or properties.get('target_field')
        condition.condition_logic = properties.get('condition_logic', condition.condition_logic)
        condition.position_x = position.get('x', condition.position_x)
        condition.position_y = position.get('y', condition.position_y)
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
                    is_expanded=page.is_expanded
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
                    relative_position_y=category.relative_position_y
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

            # Clone conditions
            for condition in workflow.conditions.all():
                new_condition = Condition.objects.create(
                    workflow=new_workflow,
                    target_field_id=element_mapping.get(('field', condition.target_field_id), condition.target_field_id),
                    condition_logic=condition.condition_logic,
                    position_x=condition.position_x,
                    position_y=condition.position_y
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

                    # Add validation properties
                    if field._max_length:
                        field_data["max_length"] = field._max_length
                    if field._min_length:
                        field_data["min_length"] = field._min_length
                    if field._regex_pattern:
                        field_data["regex_pattern"] = field._regex_pattern
                    # Add other validation fields as needed...

                    # Add conditions
                    for condition in field.conditions.filter(workflow=workflow):
                        field_data["visibility_conditions"].append({
                            "condition_logic": condition.condition_logic
                        })

                    category_data["fields"].append(field_data)

                page_data["categories"].append(category_data)

            service_flow["pages"].append(page_data)

        return Response({"service_flow": [service_flow]})

    @action(detail=False, methods=['post'])
    def import_service_flow(self, request):
        """Import service flow to create a new workflow"""
        service_flow = request.data.get('service_flow')
        workflow_name = request.data.get('workflow_name', 'Imported Workflow')

        if not service_flow:
            return Response(
                {'error': 'service_flow data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # Create workflow
            workflow = Workflow.objects.create(
                name=workflow_name,
                service_code=service_flow.get('service_code'),
                is_draft=True,
                created_by=request.user,
                updated_by=request.user,
                metadata={'imported_from': 'service_flow'}
            )

            # Import pages and their children
            for page_data in service_flow.get('pages', []):
                page = Page.objects.create(
                    workflow=workflow,
                    name=page_data.get('name', ''),
                    name_ara=page_data.get('name_ara', ''),
                    description=page_data.get('description', ''),
                    description_ara=page_data.get('description_ara', ''),
                    # You'll need to map sequence_number and other lookups
                )

                # Import categories and fields...
                # Similar to export but in reverse

        return Response(WorkflowSerializer(workflow).data, status=status.HTTP_201_CREATED)