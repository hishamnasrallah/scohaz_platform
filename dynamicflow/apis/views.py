import ast

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from authentication.models import CustomUser
from case.models import Case
from dynamicflow.models import Page
from utils.constant_lists_variables import UserTypes
from rest_framework import viewsets, status, filters
from dynamicflow.utils.dynamicflow_helper import DynamicFlowHelper
from dynamicflow.models import FieldType, Page, Category, Field, Condition
from dynamicflow.apis.serializers import (
    FieldTypeSerializer, PageListSerializer, PageDetailSerializer,
    CategoryListSerializer, CategoryDetailSerializer, FieldListSerializer,
    FieldDetailSerializer, ConditionListSerializer, ConditionDetailSerializer,
    FieldWithSubFieldsSerializer, PageWithFieldsSerializer, BulkFieldUpdateSerializer
)

class FlowAPIView(GenericAPIView):
    permission_classes = [AllowAny]

    queryset = Page.objects.all()
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):

        _query = {}
        if "service" in self.request.GET:
            _query["service__in"] = ast.literal_eval(
                self.request.GET.get("service"))

        if "beneficiary_type" in self.request.GET:
            _query["beneficiary_type"] = self.request.GET.get("beneficiary_type")
        request_by_user = CustomUser.objects.filter(id=self.request.user.id).first()

        _query["user"] = request_by_user
        # is_public_user = False
        # try:
        #     if _query['user'].user_type.code == UserTypes.PUBLIC_USER_CODE:
        #         is_public_user = True
        #         print(is_public_user)
        #     else:
        #         _query["user"] = Case.objects.filter(
        #             national_number=_query["national_number"]).first()
        # except AttributeError:
        #     _query["user"] = Case.objects.filter(applicant=request_by_user).first()
        result = DynamicFlowHelper(_query)
        flow = result.get_flow()
        # if is_public_user:
        #     result.save_services()
        return Response(flow, status=status.HTTP_200_OK)


class FieldTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for FieldType model"""
    queryset = FieldType.objects.all()
    serializer_class = FieldTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['active_ind']
    search_fields = ['name', 'name_ara', 'code']
    ordering_fields = ['name', 'code']
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Add custom filtering
        active_only = self.request.query_params.get('active_only', None)
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(active_ind=True)
        return queryset

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active field types"""
        active_types = self.get_queryset().filter(active_ind=True)
        serializer = self.get_serializer(active_types, many=True)
        return Response(serializer.data)


class PageViewSet(viewsets.ModelViewSet):
    """ViewSet for Page model"""
    queryset = Page.objects.select_related(
        'service', 'sequence_number', 'applicant_type'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['service', 'applicant_type', 'active_ind']
    search_fields = ['name', 'name_ara', 'description']
    ordering_fields = ['name', 'sequence_number__code']
    ordering = ['sequence_number__code']

    def get_serializer_class(self):
        if self.action == 'list':
            return PageListSerializer
        elif self.action == 'with_fields':
            return PageWithFieldsSerializer
        return PageDetailSerializer

    @action(detail=True, methods=['get'])
    def with_fields(self, request, pk=None):
        """Get page with all its fields and categories"""
        page = self.get_object()
        serializer = PageWithFieldsSerializer(page, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_service(self, request):
        """Get pages grouped by service"""
        service_id = request.query_params.get('service_id')
        if not service_id:
            return Response(
                {'error': 'service_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        pages = self.get_queryset().filter(service_id=service_id)
        serializer = self.get_serializer(pages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a page with optional modifications"""
        original_page = self.get_object()
        new_name = request.data.get('name', f"{original_page.name} (Copy)")

        # Create new page
        new_page = Page.objects.create(
            service=original_page.service,
            sequence_number=original_page.sequence_number,
            applicant_type=original_page.applicant_type,
            name=new_name,
            name_ara=request.data.get('name_ara', f"{original_page.name_ara} (نسخة)"),
            description=original_page.description,
            description_ara=original_page.description_ara,
            active_ind=request.data.get('active_ind', True)
        )

        serializer = self.get_serializer(new_page)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for Category model"""
    queryset = Category.objects.prefetch_related('page').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_repeatable', 'active_ind']
    search_fields = ['name', 'name_ara', 'description', 'code']
    ordering_fields = ['name', 'code']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return CategoryListSerializer
        return CategoryDetailSerializer

    @action(detail=False, methods=['get'])
    def repeatable(self, request):
        """Get only repeatable categories"""
        categories = self.get_queryset().filter(is_repeatable=True, active_ind=True)
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_pages(self, request, pk=None):
        """Add multiple pages to a category"""
        category = self.get_object()
        page_ids = request.data.get('page_ids', [])

        if not page_ids:
            return Response(
                {'error': 'page_ids list is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        pages = Page.objects.filter(id__in=page_ids)
        category.page.add(*pages)

        serializer = self.get_serializer(category)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def remove_pages(self, request, pk=None):
        """Remove multiple pages from a category"""
        category = self.get_object()
        page_ids = request.data.get('page_ids', [])

        if not page_ids:
            return Response(
                {'error': 'page_ids list is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        pages = Page.objects.filter(id__in=page_ids)
        category.page.remove(*pages)

        serializer = self.get_serializer(category)
        return Response(serializer.data)


class FieldViewSet(viewsets.ModelViewSet):
    """ViewSet for Field model"""
    queryset = Field.objects.select_related(
        '_field_type', '_parent_field', '_lookup'
    ).prefetch_related(
        'service', '_category', 'allowed_lookups', 'sub_fields'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        '_field_type', '_parent_field', '_mandatory', '_is_hidden',
        '_is_disabled', 'active_ind'
    ]
    search_fields = ['_field_name', '_field_display_name', '_field_display_name_ara']
    ordering_fields = ['_field_name', '_sequence']
    ordering = ['_sequence', '_field_name']

    def get_serializer_class(self):
        if self.action == 'list':
            return FieldListSerializer
        elif self.action in ['with_sub_fields', 'tree_structure']:
            return FieldWithSubFieldsSerializer
        return FieldDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Custom filtering
        service_id = self.request.query_params.get('service')
        if service_id:
            queryset = queryset.filter(service__id=service_id)

        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(_category__id=category_id)

        field_type = self.request.query_params.get('field_type')
        if field_type:
            queryset = queryset.filter(_field_type__name__icontains=field_type)

        root_only = self.request.query_params.get('root_only')
        if root_only and root_only.lower() == 'true':
            queryset = queryset.filter(_parent_field__isnull=True)

        return queryset

    @action(detail=True, methods=['get'])
    def with_sub_fields(self, request, pk=None):
        """Get field with all its sub-fields in a nested structure"""
        field = self.get_object()
        serializer = FieldWithSubFieldsSerializer(field, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def tree_structure(self, request):
        """Get all root fields with their nested sub-fields"""
        root_fields = self.get_queryset().filter(
            _parent_field__isnull=True,
            active_ind=True
        ).order_by('_sequence')

        serializer = FieldWithSubFieldsSerializer(
            root_fields, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_sub_field(self, request, pk=None):
        """Add a sub-field to this field"""
        parent_field = self.get_object()
        data = request.data.copy()
        data['_parent_field'] = parent_field.id

        serializer = FieldDetailSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def validate_field(self, request, pk=None):
        """Validate a field value against all its validation rules"""
        field = self.get_object()
        value = request.query_params.get('value')

        if value is None:
            return Response(
                {'error': 'value parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # This is a placeholder for field validation logic
        # You would implement the actual validation based on field properties
        validation_result = {
            'field_name': field._field_name,
            'value': value,
            'is_valid': True,
            'errors': []
        }

        # Add validation logic here based on field type and constraints

        return Response(validation_result)

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update multiple fields"""
        serializer = BulkFieldUpdateSerializer(data=request.data)
        if serializer.is_valid():
            field_ids = serializer.validated_data['field_ids']
            action_type = serializer.validated_data['action']

            fields = Field.objects.filter(id__in=field_ids)

            if action_type == 'activate':
                fields.update(active_ind=True)
            elif action_type == 'deactivate':
                fields.update(active_ind=False)
            elif action_type == 'hide':
                fields.update(_is_hidden=True)
            elif action_type == 'show':
                fields.update(_is_hidden=False)

            return Response({
                'message': f'Successfully {action_type}d {len(field_ids)} fields',
                'affected_fields': field_ids
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a field with optional modifications"""
        original_field = self.get_object()
        new_name = request.data.get('_field_name', f"{original_field._field_name}_copy")

        # Create new field with copied attributes
        field_data = {
            '_field_name': new_name,
            '_field_display_name': request.data.get(
                '_field_display_name',
                f"{original_field._field_display_name} (Copy)"
            ),
            '_field_display_name_ara': request.data.get(
                '_field_display_name_ara',
                f"{original_field._field_display_name_ara} (نسخة)"
            ),
            '_field_type': original_field._field_type,
            '_sequence': request.data.get('_sequence', original_field._sequence),
            # Copy all validation fields
            '_max_length': original_field._max_length,
            '_min_length': original_field._min_length,
            '_regex_pattern': original_field._regex_pattern,
            # ... copy other fields as needed
        }

        serializer = FieldDetailSerializer(data=field_data, context={'request': request})
        if serializer.is_valid():
            new_field = serializer.save()

            # Copy many-to-many relationships
            new_field.service.set(original_field.service.all())
            new_field._category.set(original_field._category.all())
            new_field.allowed_lookups.set(original_field.allowed_lookups.all())

            return Response(
                FieldDetailSerializer(new_field, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConditionViewSet(viewsets.ModelViewSet):
    """ViewSet for Condition model"""
    queryset = Condition.objects.select_related('target_field').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['target_field', 'active_ind']
    search_fields = ['target_field___field_name']
    ordering_fields = ['target_field___field_name']
    ordering = ['target_field___field_name']

    def get_serializer_class(self):
        if self.action == 'list':
            return ConditionListSerializer
        return ConditionDetailSerializer

    @action(detail=True, methods=['post'])
    def test_condition(self, request, pk=None):
        """Test a condition with provided field data"""
        condition = self.get_object()
        field_data = request.data.get('field_data', {})

        if not field_data:
            return Response(
                {'error': 'field_data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = condition.evaluate_condition(field_data)
            return Response({
                'condition_id': condition.id,
                'target_field': condition.target_field._field_name,
                'field_data': field_data,
                'result': result,
                'should_show_field': result
            })
        except Exception as e:
            return Response(
                {'error': f'Error evaluating condition: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def evaluate_multiple(self, request):
        """Evaluate multiple conditions with the same field data"""
        condition_ids = request.data.get('condition_ids', [])
        field_data = request.data.get('field_data', {})

        if not condition_ids or not field_data:
            return Response(
                {'error': 'condition_ids and field_data are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        conditions = Condition.objects.filter(
            id__in=condition_ids,
            active_ind=True
        ).select_related('target_field')

        results = []
        for condition in conditions:
            try:
                result = condition.evaluate_condition(field_data)
                results.append({
                    'condition_id': condition.id,
                    'target_field': condition.target_field._field_name,
                    'result': result,
                    'should_show_field': result
                })
            except Exception as e:
                results.append({
                    'condition_id': condition.id,
                    'target_field': condition.target_field._field_name,
                    'error': str(e),
                    'result': False
                })

        return Response({
            'field_data': field_data,
            'results': results,
            'fields_to_show': [
                r['target_field'] for r in results
                if r.get('result', False)
            ]
        })

    @action(detail=False, methods=['get'])
    def by_field(self, request):
        """Get all conditions for a specific field"""
        field_id = request.query_params.get('field_id')
        if not field_id:
            return Response(
                {'error': 'field_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        conditions = self.get_queryset().filter(target_field_id=field_id)
        serializer = self.get_serializer(conditions, many=True)
        return Response(serializer.data)