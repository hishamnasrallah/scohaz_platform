from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from dynamicflow.models import FieldType, Page, Category, Field, Condition
from dynamicflow.apis.workflow_serializers import (
    WorkflowFieldTypeSerializer, WorkflowPageSerializer,
    WorkflowCategorySerializer, WorkflowFieldSerializer,
    WorkflowConditionSerializer
)


class WorkflowFieldTypeViewSet(viewsets.ModelViewSet):
    """Field types API for workflow builder"""
    queryset = FieldType.objects.all()
    serializer_class = WorkflowFieldTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['active_ind']
    ordering = ['name']


class WorkflowPageViewSet(viewsets.ModelViewSet):
    """Pages API for workflow builder with consistent foreign key handling"""
    queryset = Page.objects.select_related(
        'service', 'sequence_number', 'applicant_type'
    ).all()
    serializer_class = WorkflowPageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['service', 'applicant_type', 'active_ind']
    search_fields = ['name', 'name_ara']
    ordering = ['sequence_number__code']

    def create(self, request, *args, **kwargs):
        """Handle creation with proper foreign key resolution"""
        data = request.data.copy()

        # Ensure foreign keys are properly set
        if 'service' in data and isinstance(data['service'], dict):
            data['service'] = data['service'].get('id')
        if 'sequence_number' in data and isinstance(data['sequence_number'], dict):
            data['sequence_number'] = data['sequence_number'].get('id')
        if 'applicant_type' in data and isinstance(data['applicant_type'], dict):
            data['applicant_type'] = data['applicant_type'].get('id')

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Reload with related data
        instance = Page.objects.select_related(
            'service', 'sequence_number', 'applicant_type'
        ).get(pk=serializer.data['id'])

        return Response(
            self.get_serializer(instance).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """Handle update with proper foreign key resolution"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.copy()

        # Ensure foreign keys are properly set
        if 'service' in data and isinstance(data['service'], dict):
            data['service'] = data['service'].get('id')
        if 'sequence_number' in data and isinstance(data['sequence_number'], dict):
            data['sequence_number'] = data['sequence_number'].get('id')
        if 'applicant_type' in data and isinstance(data['applicant_type'], dict):
            data['applicant_type'] = data['applicant_type'].get('id')

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Reload with related data
        instance.refresh_from_db()

        return Response(self.get_serializer(instance).data)


class WorkflowCategoryViewSet(viewsets.ModelViewSet):
    """Categories API for workflow builder"""
    queryset = Category.objects.prefetch_related('page').all()
    serializer_class = WorkflowCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_repeatable', 'active_ind']
    search_fields = ['name', 'name_ara', 'code']
    ordering = ['name']


class WorkflowFieldViewSet(viewsets.ModelViewSet):
    """Fields API for workflow builder with consistent foreign key handling"""
    queryset = Field.objects.select_related(
        '_field_type', '_parent_field', '_lookup'
    ).prefetch_related(
        'service', '_category', 'allowed_lookups'
    ).all()
    serializer_class = WorkflowFieldSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['_field_type', '_mandatory', '_is_hidden', 'active_ind']
    search_fields = ['_field_name', '_field_display_name']
    ordering = ['_sequence', '_field_name']

    def create(self, request, *args, **kwargs):
        """Handle creation with proper foreign key resolution"""
        data = request.data.copy()

        # Ensure foreign keys are properly set
        if '_field_type' in data and isinstance(data['_field_type'], dict):
            data['_field_type'] = data['_field_type'].get('id')
        if '_parent_field' in data and isinstance(data['_parent_field'], dict):
            data['_parent_field'] = data['_parent_field'].get('id')
        if '_lookup' in data and isinstance(data['_lookup'], dict):
            data['_lookup'] = data['_lookup'].get('id')

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Reload with related data
        instance = Field.objects.select_related(
            '_field_type', '_parent_field', '_lookup'
        ).get(pk=serializer.data['id'])

        return Response(
            self.get_serializer(instance).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def with_children(self, request, pk=None):
        """Get field with all its nested children"""
        field = self.get_object()
        serializer = self.get_serializer(field)
        data = serializer.data

        # Add full nested children
        data['children'] = self._get_nested_children(field)

        return Response(data)

    def _get_nested_children(self, parent_field):
        """Recursively get all children"""
        children = []
        for child in parent_field.sub_fields.filter(active_ind=True):
            child_data = WorkflowFieldSerializer(child).data
            child_data['children'] = self._get_nested_children(child)
            children.append(child_data)
        return children


class WorkflowConditionViewSet(viewsets.ModelViewSet):
    """Conditions API for workflow builder"""
    queryset = Condition.objects.select_related('target_field').all()
    serializer_class = WorkflowConditionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['target_field', 'active_ind']
    ordering = ['target_field___field_name']

    def create(self, request, *args, **kwargs):
        """Handle creation with proper foreign key resolution"""
        data = request.data.copy()

        # Ensure foreign keys are properly set
        if 'target_field' in data and isinstance(data['target_field'], dict):
            data['target_field'] = data['target_field'].get('id')

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Reload with related data
        instance = Condition.objects.select_related('target_field').get(pk=serializer.data['id'])

        return Response(
            self.get_serializer(instance).data,
            status=status.HTTP_201_CREATED
        )