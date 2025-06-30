from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
import json

from reporting.models import (
    Report, ReportDataSource, ReportField, ReportFilter,
    ReportJoin, ReportParameter, ReportExecution, ReportSchedule,
    SavedReportResult
)
from reporting.apis.serializers import (
    ReportSerializer, ReportListSerializer, ReportDataSourceSerializer,
    ReportFieldSerializer, ReportFilterSerializer, ReportJoinSerializer,
    ReportParameterSerializer, ReportExecutionSerializer,
    ReportScheduleSerializer, SavedReportResultSerializer,
    ReportBuilderSerializer, ReportExecutionRequestSerializer,
    ReportPreviewSerializer
)
from reporting.utils.model_inspector import DynamicModelInspector
from reporting.utils.query_builder import ReportQueryBuilder
from reporting.utils.exporters import ReportExporter
from reporting.apis.permissions import ReportPermission


class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reports.

    Provides CRUD operations plus additional actions for:
    - Executing reports
    - Previewing reports
    - Duplicating reports
    - Getting available models
    """
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated, ReportPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['report_type', 'is_active', 'is_public', 'category', 'created_by']
    search_fields = ['name', 'description', 'tags']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get reports accessible to the current user."""
        user = self.request.user

        if user.is_superuser:
            return Report.objects.all()

        # Get reports that are:
        # 1. Created by the user
        # 2. Shared with the user
        # 3. Shared with user's groups
        # 4. Public reports
        return Report.objects.filter(
            Q(created_by=user) |
            Q(shared_with_users=user) |
            Q(shared_with_groups__in=user.groups.all()) |
            Q(is_public=True)
        ).distinct()

    def get_serializer_class(self):
        """Use lightweight serializer for list action."""
        if self.action == 'list':
            return ReportListSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        Execute a report with the given parameters.

        Request body:
        {
            "parameters": {"param1": "value1"},
            "limit": 100,
            "offset": 0,
            "export_format": "json",
            "save_result": false,
            "result_name": "My Report Result"
        }
        """
        report = self.get_object()
        serializer = ReportExecutionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # Build and execute query
        builder = ReportQueryBuilder(report, user=request.user)
        result = builder.execute(
            parameters=data['parameters'],
            limit=data.get('limit'),
            offset=data.get('offset'),
            export_format=data.get('export_format', 'json')
        )

        if not result['success']:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        # Handle export formats
        export_format = data.get('export_format', 'json')
        if export_format != 'json':
            exporter = ReportExporter()

            if export_format == 'csv':
                return exporter.export_csv(report, result['data'])
            elif export_format == 'excel':
                return exporter.export_excel(report, result['data'])
            elif export_format == 'pdf':
                return exporter.export_pdf(report, result['data'])

        # Save result if requested
        if data.get('save_result'):
            saved_result = SavedReportResult.objects.create(
                report=report,
                name=data.get('result_name', f"{report.name} - Result"),
                description=data.get('result_description', ''),
                execution_id=result.get('execution_id'),
                parameters_used=data['parameters'],
                result_data=result['data'],
                row_count=result['row_count'],
                saved_by=request.user
            )
            result['saved_result_id'] = saved_result.id

        return Response(result)

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """
        Preview a report with limited results.

        Returns the first 10 rows and query information.
        """
        report = self.get_object()

        # Get parameters from request
        parameters = request.data.get('parameters', {})

        # Build query
        builder = ReportQueryBuilder(report, user=request.user)

        try:
            # Get SQL for preview
            query = builder.build_query(parameters)
            sql = builder.get_sql()

            # Execute with limit
            result = builder.execute(parameters=parameters, limit=10)

            if result['success']:
                preview_data = {
                    'query_sql': sql,
                    'estimated_rows': query.count() if hasattr(query, 'count') else 'Unknown',
                    'preview_data': result['data'],
                    'columns': result['columns'],
                    'warnings': []
                }

                serializer = ReportPreviewSerializer(preview_data)
                return Response(serializer.data)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplicate a report.

        Creates a copy of the report with all its components.
        """
        original_report = self.get_object()

        # Create new report
        new_report = Report.objects.create(
            name=f"{original_report.name} (Copy)",
            description=original_report.description,
            report_type=original_report.report_type,
            is_active=True,
            is_public=False,
            tags=original_report.tags,
            category=original_report.category,
            created_by=request.user,
            config=original_report.config
        )

        # Copy data sources
        source_mapping = {}
        for source in original_report.data_sources.all():
            new_source = ReportDataSource.objects.create(
                report=new_report,
                app_name=source.app_name,
                model_name=source.model_name,
                alias=source.alias,
                is_primary=source.is_primary,
                select_related=source.select_related,
                prefetch_related=source.prefetch_related
            )
            source_mapping[source.id] = new_source

        # Copy fields
        for field in original_report.fields.all():
            ReportField.objects.create(
                report=new_report,
                data_source=source_mapping[field.data_source_id],
                field_name=field.field_name,
                field_path=field.field_path,
                display_name=field.display_name,
                field_type=field.field_type,
                aggregation=field.aggregation,
                order=field.order,
                is_visible=field.is_visible,
                width=field.width,
                formatting=field.formatting
            )

        # Copy filters
        for filter_obj in original_report.filters.all():
            ReportFilter.objects.create(
                report=new_report,
                data_source=source_mapping[filter_obj.data_source_id],
                field_name=filter_obj.field_name,
                field_path=filter_obj.field_path,
                operator=filter_obj.operator,
                value=filter_obj.value,
                value_type=filter_obj.value_type,
                logic_group=filter_obj.logic_group,
                group_order=filter_obj.group_order,
                is_active=filter_obj.is_active,
                is_required=filter_obj.is_required
            )

        # Copy joins
        for join in original_report.joins.all():
            ReportJoin.objects.create(
                report=new_report,
                left_source=source_mapping[join.left_source_id],
                right_source=source_mapping[join.right_source_id],
                left_field=join.left_field,
                right_field=join.right_field,
                join_type=join.join_type,
                additional_conditions=join.additional_conditions
            )

        # Copy parameters
        for param in original_report.parameters.all():
            ReportParameter.objects.create(
                report=new_report,
                name=param.name,
                display_name=param.display_name,
                parameter_type=param.parameter_type,
                is_required=param.is_required,
                default_value=param.default_value,
                choices_static=param.choices_static,
                choices_query=param.choices_query,
                validation_rules=param.validation_rules,
                help_text=param.help_text,
                placeholder=param.placeholder,
                order=param.order
            )

        serializer = self.get_serializer(new_report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def available_models(self, request):
        """
        Get all available models for report building.

        Returns structured information about apps and their models.
        """
        include_system = request.query_params.get('include_system', 'false').lower() == 'true'

        inspector = DynamicModelInspector()
        models = inspector.get_all_apps_and_models(include_system_apps=include_system)

        return Response(models)

    @action(detail=False, methods=['get'])
    def builder_data(self, request):
        """
        Get all data needed for the report builder UI.

        Includes available models, field types, operators, etc.
        """
        report_id = request.query_params.get('report_id')

        inspector = DynamicModelInspector()
        builder_data = {
            'available_apps': inspector.get_all_apps_and_models(),
            'available_aggregations': ['count', 'count_distinct', 'sum', 'avg', 'min', 'max', 'group_by'],
            'available_operators': [
                {'value': 'eq', 'label': 'Equals'},
                {'value': 'ne', 'label': 'Not Equals'},
                {'value': 'gt', 'label': 'Greater Than'},
                {'value': 'gte', 'label': 'Greater Than or Equal'},
                {'value': 'lt', 'label': 'Less Than'},
                {'value': 'lte', 'label': 'Less Than or Equal'},
                {'value': 'in', 'label': 'In List'},
                {'value': 'not_in', 'label': 'Not In List'},
                {'value': 'contains', 'label': 'Contains'},
                {'value': 'icontains', 'label': 'Contains (Case Insensitive)'},
                {'value': 'startswith', 'label': 'Starts With'},
                {'value': 'endswith', 'label': 'Ends With'},
                {'value': 'regex', 'label': 'Regex Match'},
                {'value': 'isnull', 'label': 'Is Null'},
                {'value': 'isnotnull', 'label': 'Is Not Null'},
                {'value': 'between', 'label': 'Between'},
                {'value': 'date_range', 'label': 'Date Range'},
            ],
        }

        if report_id:
            try:
                report = Report.objects.get(id=report_id)
                builder_data['report'] = ReportSerializer(report, context={'request': request}).data
            except Report.DoesNotExist:
                pass

        serializer = ReportBuilderSerializer(builder_data)
        return Response(serializer.data)


class ReportDataSourceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing report data sources."""
    queryset = ReportDataSource.objects.all()
    serializer_class = ReportDataSourceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by report if specified."""
        queryset = super().get_queryset()
        report_id = self.request.query_params.get('report')
        if report_id:
            queryset = queryset.filter(report_id=report_id)
        return queryset


class ReportFieldViewSet(viewsets.ModelViewSet):
    """ViewSet for managing report fields."""
    queryset = ReportField.objects.all()
    serializer_class = ReportFieldSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by report if specified."""
        queryset = super().get_queryset()
        report_id = self.request.query_params.get('report')
        if report_id:
            queryset = queryset.filter(report_id=report_id)
        return queryset.order_by('order')


class ReportFilterViewSet(viewsets.ModelViewSet):
    """ViewSet for managing report filters."""
    queryset = ReportFilter.objects.all()
    serializer_class = ReportFilterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by report if specified."""
        queryset = super().get_queryset()
        report_id = self.request.query_params.get('report')
        if report_id:
            queryset = queryset.filter(report_id=report_id)
        return queryset.order_by('group_order', 'id')


class ReportJoinViewSet(viewsets.ModelViewSet):
    """ViewSet for managing report joins."""
    queryset = ReportJoin.objects.all()
    serializer_class = ReportJoinSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by report if specified."""
        queryset = super().get_queryset()
        report_id = self.request.query_params.get('report')
        if report_id:
            queryset = queryset.filter(report_id=report_id)
        return queryset


class ReportParameterViewSet(viewsets.ModelViewSet):
    """ViewSet for managing report parameters."""
    queryset = ReportParameter.objects.all()
    serializer_class = ReportParameterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by report if specified."""
        queryset = super().get_queryset()
        report_id = self.request.query_params.get('report')
        if report_id:
            queryset = queryset.filter(report_id=report_id)
        return queryset.order_by('order')


class ReportExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing report executions (read-only)."""
    queryset = ReportExecution.objects.all()
    serializer_class = ReportExecutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['report', 'executed_by', 'status']
    ordering_fields = ['executed_at', 'execution_time', 'row_count']
    ordering = ['-executed_at']

    def get_queryset(self):
        """Filter based on user permissions."""
        user = self.request.user
        if user.is_superuser:
            return super().get_queryset()

        # Only show executions for reports user can access
        accessible_reports = Report.objects.filter(
            Q(created_by=user) |
            Q(shared_with_users=user) |
            Q(shared_with_groups__in=user.groups.all()) |
            Q(is_public=True)
        ).distinct()

        return super().get_queryset().filter(report__in=accessible_reports)


class ReportScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet for managing report schedules."""
    queryset = ReportSchedule.objects.all()
    serializer_class = ReportScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['report', 'schedule_type', 'is_active']
    ordering_fields = ['name', 'created_at', 'next_run']
    ordering = ['name']

    def get_queryset(self):
        """Filter based on user permissions."""
        user = self.request.user
        if user.is_superuser:
            return super().get_queryset()

        # Only show schedules created by user or for reports they can access
        return super().get_queryset().filter(
            Q(created_by=user) |
            Q(report__created_by=user) |
            Q(report__shared_with_users=user) |
            Q(report__shared_with_groups__in=user.groups.all())
        ).distinct()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a schedule."""
        schedule = self.get_object()
        schedule.is_active = True
        schedule.save()
        return Response({'status': 'activated'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a schedule."""
        schedule = self.get_object()
        schedule.is_active = False
        schedule.save()
        return Response({'status': 'deactivated'})


class SavedReportResultViewSet(viewsets.ModelViewSet):
    """ViewSet for managing saved report results."""
    queryset = SavedReportResult.objects.all()
    serializer_class = SavedReportResultSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['report', 'saved_by', 'is_public']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'saved_at', 'row_count']
    ordering = ['-saved_at']

    def get_queryset(self):
        """Filter based on user permissions."""
        user = self.request.user
        if user.is_superuser:
            return super().get_queryset()

        return super().get_queryset().filter(
            Q(saved_by=user) |
            Q(shared_with_users=user) |
            Q(shared_with_groups__in=user.groups.all()) |
            Q(is_public=True)
        ).distinct()

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download saved result data."""
        saved_result = self.get_object()

        # Return as JSON download
        response = HttpResponse(
            json.dumps(saved_result.result_data, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="{saved_result.name}.json"'
        return response


# Utility views

class FieldLookupView(APIView):
    """
    API view to get available lookups for a field type.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        field_type = request.query_params.get('field_type')
        if not field_type:
            return Response(
                {'error': 'field_type parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        inspector = DynamicModelInspector()
        lookups = inspector.get_field_lookups(field_type)

        return Response({'lookups': lookups})


class ModelFieldsView(APIView):
    """
    API view to get fields for a specific model.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app_name = request.query_params.get('app')
        model_name = request.query_params.get('model')

        if not app_name or not model_name:
            return Response(
                {'error': 'app and model parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        inspector = DynamicModelInspector()
        model_class = inspector.get_model_by_name(app_name, model_name)

        if not model_class:
            return Response(
                {'error': f'Model {app_name}.{model_name} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        fields = inspector.get_model_fields(model_class)
        relationships = inspector.get_model_relationships(model_class)

        return Response({
            'fields': fields,
            'relationships': relationships
        })