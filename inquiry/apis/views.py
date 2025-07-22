import time
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.http import HttpResponse
import csv
import json
from openpyxl import Workbook

from inquiry.models import InquiryConfiguration, InquiryExecution, InquiryTemplate
from inquiry.services.query_builder import DynamicQueryBuilder
from inquiry.apis.serializers.dynamic import DynamicModelSerializer
from inquiry.apis.serializers.inquiry import (
    InquiryConfigurationSerializer,
    InquiryExecutionSerializer,
    InquiryTemplateSerializer
)

class DynamicPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 1000

    def get_page_size(self, request):
        if self.page_size_query_param:
            try:
                inquiry_code = request.parser_context['kwargs'].get('code')
                if inquiry_code:
                    inquiry = InquiryConfiguration.objects.filter(
                        code=inquiry_code
                    ).first()
                    if inquiry:
                        self.page_size = inquiry.default_page_size
                        self.max_page_size = inquiry.max_page_size
            except:
                pass
        return super().get_page_size(request)


class InquiryConfigurationViewSet(viewsets.ModelViewSet):
    """CRUD for inquiry configurations"""
    queryset = InquiryConfiguration.objects.all()
    serializer_class = InquiryConfigurationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'code'

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            # Filter by user's groups
            user_groups = self.request.user.groups.all()
            queryset = queryset.filter(
                allowed_groups__in=user_groups
            ).distinct() | queryset.filter(is_public=True)
        return queryset

    @action(detail=True, methods=['get'])
    def preview(self, request, code=None):
        """Preview inquiry structure without executing"""
        inquiry = self.get_object()

        # Get model info
        model = inquiry.content_type.model_class()

        # Build structure
        structure = {
            'model': {
                'app_label': model._meta.app_label,
                'model_name': model._meta.model_name,
                'verbose_name': model._meta.verbose_name,
                'verbose_name_plural': model._meta.verbose_name_plural,
            },
            'fields': [],
            'relations': [],
            'filters': [],
            'sorts': []
        }

        # Add fields
        for field in inquiry.fields.all():
            field_info = {
                'field_path': field.field_path,
                'display_name': field.display_name,
                'field_type': field.field_type,
                'is_sortable': field.is_sortable,
                'is_searchable': field.is_searchable,
                'is_filterable': field.is_filterable,
            }
            structure['fields'].append(field_info)

        # Add relations
        for relation in inquiry.relations.all():
            relation_info = {
                'relation_path': relation.relation_path,
                'display_name': relation.display_name,
                'relation_type': relation.relation_type,
                'include_fields': relation.include_fields,
            }
            structure['relations'].append(relation_info)

        # Add filters
        for filter_obj in inquiry.filters.all():
            filter_info = {
                'code': filter_obj.code,
                'name': filter_obj.name,
                'field_path': filter_obj.field_path,
                'operator': filter_obj.operator,
                'filter_type': filter_obj.filter_type,
            }
            structure['filters'].append(filter_info)

        return Response(structure)

    @action(detail=False, methods=['get'])
    def available_models(self, request):
        """List all available models for inquiry"""
        models = []
        for ct in ContentType.objects.all():
            model_class = ct.model_class()
            if model_class and issubclass(model_class, Model):
                models.append({
                    'id': ct.id,
                    'app_label': ct.app_label,
                    'model': ct.model,
                    'name': model_class._meta.verbose_name,
                    'fields': [
                        {
                            'name': f.name,
                            'type': f.get_internal_type(),
                            'verbose_name': f.verbose_name,
                            'is_relation': f.is_relation
                        }
                        for f in model_class._meta.get_fields()
                    ]
                })
        return Response(models)


class InquiryExecutionViewSet(viewsets.ViewSet):
    """Execute configured inquiries"""
    permission_classes = [IsAuthenticated]
    pagination_class = DynamicPagination

    @action(detail=False, methods=['post'], url_path='execute/(?P<code>[^/.]+)')
    def execute(self, request, code=None):
        """Execute an inquiry by code"""
        start_time = time.time()

        try:
            # Get inquiry configuration
            inquiry = InquiryConfiguration.objects.get(code=code, active=True)

            # Check permissions
            if not self.has_permission(request.user, inquiry):
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get request parameters
            filters = request.data.get('filters', {})
            search = request.data.get('search', '')
            sort = request.data.get('sort', [])
            export_format = request.data.get('export')

            # Build queryset
            builder = DynamicQueryBuilder(inquiry)
            queryset = builder.build_queryset(
                filters=filters,
                search=search,
                sort=sort,
                user=request.user
            )

            # Get aggregations if requested
            include_aggregations = request.data.get('include_aggregations', False)
            aggregations = {}
            if include_aggregations:
                aggregations = builder.get_aggregations(queryset)

            # Handle export
            if export_format and inquiry.allow_export:
                return self.export_data(
                    queryset,
                    inquiry,
                    export_format,
                    request.user
                )

            # Paginate results
            paginator = DynamicPagination()
            page = paginator.paginate_queryset(queryset, request, view=self)

            # Serialize data
            serializer_context = {
                'inquiry': inquiry,
                'request': request
            }

            if page is not None:
                serializer = DynamicModelSerializer(
                    page,
                    many=True,
                    context=serializer_context
                )

                # Log execution
                execution_time = int((time.time() - start_time) * 1000)
                self.log_execution(
                    inquiry=inquiry,
                    user=request.user,
                    filters=filters,
                    search=search,
                    sort=sort,
                    result_count=paginator.page.paginator.count,
                    page_size=len(page),
                    page_number=request.GET.get('page', 1),
                    execution_time=execution_time,
                    query_count=builder.query_count,
                    request=request
                )

                response_data = paginator.get_paginated_response(serializer.data).data
                response_data['aggregations'] = aggregations
                response_data['execution_time_ms'] = execution_time
                response_data['inquiry'] = {
                    'name': inquiry.name,
                    'display_name': inquiry.display_name,
                    'code': inquiry.code
                }

                return Response(response_data)

            # No pagination
            serializer = DynamicModelSerializer(
                queryset,
                many=True,
                context=serializer_context
            )

            execution_time = int((time.time() - start_time) * 1000)
            self.log_execution(
                inquiry=inquiry,
                user=request.user,
                filters=filters,
                search=search,
                sort=sort,
                result_count=queryset.count(),
                execution_time=execution_time,
                query_count=builder.query_count,
                request=request
            )

            return Response({
                'results': serializer.data,
                'count': queryset.count(),
                'aggregations': aggregations,
                'execution_time_ms': execution_time,
                'inquiry': {
                    'name': inquiry.name,
                    'display_name': inquiry.display_name,
                    'code': inquiry.code
                }
            })

        except InquiryConfiguration.DoesNotExist:
            return Response(
                {'error': 'Inquiry not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # Log failed execution
            if 'inquiry' in locals():
                self.log_execution(
                    inquiry=inquiry,
                    user=request.user,
                    filters=filters if 'filters' in locals() else {},
                    success=False,
                    error_message=str(e),
                    request=request
                )
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='schema/(?P<code>[^/.]+)')
    def schema(self, request, code=None):
        """Get inquiry schema for frontend rendering"""
        try:
            inquiry = InquiryConfiguration.objects.get(code=code)

            if not self.has_permission(request.user, inquiry):
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

            schema = {
                'inquiry': InquiryConfigurationSerializer(inquiry).data,
                'fields': [],
                'filters': [],
                'sorts': [],
                'relations': [],
                'permissions': self.get_user_permissions(request.user, inquiry)
            }

            # Add field schemas
            for field in inquiry.fields.filter(is_visible=True).order_by('order'):
                field_schema = {
                    'field_path': field.field_path,
                    'display_name': field.display_name,
                    'field_type': field.field_type,
                    'is_sortable': field.is_sortable,
                    'is_searchable': field.is_searchable,
                    'is_filterable': field.is_filterable,
                    'is_primary': field.is_primary,
                    'width': field.width,
                    'alignment': field.alignment,
                    'format_template': field.format_template,
                }
                schema['fields'].append(field_schema)

            # Add filter schemas
            for filter_config in inquiry.filters.filter(is_visible=True).order_by('order'):
                filter_schema = {
                    'code': filter_config.code,
                    'name': filter_config.name,
                    'field_path': filter_config.field_path,
                    'operator': filter_config.operator,
                    'filter_type': filter_config.filter_type,
                    'default_value': filter_config.default_value,
                    'is_required': filter_config.is_required,
                    'is_advanced': filter_config.is_advanced,
                    'placeholder': filter_config.placeholder,
                    'help_text': filter_config.help_text,
                    'validation_rules': filter_config.validation_rules,
                }

                # Add choices for select filters
                if filter_config.filter_type in ['select', 'multiselect', 'radio']:
                    if filter_config.choices_json:
                        filter_schema['choices'] = filter_config.choices_json
                    elif filter_config.lookup_category:
                        # Get choices from lookup
                        from lookup.models import Lookup
                        choices = Lookup.objects.filter(
                            parent_lookup__name=filter_config.lookup_category,
                            active_ind=True
                        ).values('id', 'name', 'code')
                        filter_schema['choices'] = list(choices)

                schema['filters'].append(filter_schema)

            # Add sort options
            for sort in inquiry.sorts.all():
                schema['sorts'].append({
                    'field_path': sort.field_path,
                    'direction': sort.direction,
                })

            return Response(schema)

        except InquiryConfiguration.DoesNotExist:
            return Response(
                {'error': 'Inquiry not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def has_permission(self, user, inquiry):
        """Check if user has permission to execute inquiry"""
        if inquiry.is_public:
            return True

        if user.is_superuser:
            return True

        user_groups = user.groups.all()
        return inquiry.allowed_groups.filter(id__in=user_groups).exists()

    def get_user_permissions(self, user, inquiry):
        """Get user's permissions for the inquiry"""
        if user.is_superuser:
            return {
                'can_view': True,
                'can_export': True,
                'can_view_all': True,
                'export_formats': ['csv', 'excel', 'json'],
            }

        user_groups = user.groups.all()
        permission = inquiry.permissions.filter(group__in=user_groups).first()

        if permission:
            return {
                'can_view': permission.can_view,
                'can_export': permission.can_export,
                'can_view_all': permission.can_view_all,
                'export_formats': permission.allowed_export_formats or ['csv'],
                'max_export_rows': permission.max_export_rows,
            }

        return {
            'can_view': inquiry.is_public,
            'can_export': False,
            'can_view_all': False,
            'export_formats': [],
        }

    def log_execution(self, inquiry, user, filters=None, search=None,
                      sort=None, result_count=0, page_size=None,
                      page_number=None, execution_time=0, query_count=0,
                      export_format=None, success=True, error_message='',
                      request=None):
        """Log inquiry execution"""
        InquiryExecution.objects.create(
            inquiry=inquiry,
            user=user,
            filters_applied=filters or {},
            search_query=search or '',
            sort_applied=sort or [],
            result_count=result_count,
            page_size=page_size,
            page_number=page_number,
            execution_time_ms=execution_time,
            query_count=query_count,
            export_format=export_format or '',
            success=success,
            error_message=error_message,
            ip_address=self.get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''
        )

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def export_data(self, queryset, inquiry, export_format, user):
        """Export data in requested format"""
        # Check export permission
        user_groups = user.groups.all()
        permission = inquiry.permissions.filter(group__in=user_groups).first()

        if permission:
            if not permission.can_export:
                return Response(
                    {'error': 'Export not allowed'},
                    status=status.HTTP_403_FORBIDDEN
                )
            if export_format not in permission.allowed_export_formats:
                return Response(
                    {'error': f'Export format {export_format} not allowed'},
                    status=status.HTTP_403_FORBIDDEN
                )
            if permission.max_export_rows and queryset.count() > permission.max_export_rows:
                return Response(
                    {'error': f'Export exceeds maximum rows ({permission.max_export_rows})'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Serialize data
        serializer = DynamicModelSerializer(
            queryset,
            many=True,
            context={'inquiry': inquiry, 'request': None}
        )
        data = serializer.data

        # Get visible fields for export
        export_fields = inquiry.fields.filter(is_visible=True).order_by('order')

        if export_format == 'csv':
            return self.export_csv(data, export_fields, inquiry)
        elif export_format == 'excel':
            return self.export_excel(data, export_fields, inquiry)
        elif export_format == 'json':
            return self.export_json(data, inquiry)
        else:
            return Response(
                {'error': 'Invalid export format'},
                status=status.HTTP_400_BAD_REQUEST
            )

    def export_csv(self, data, fields, inquiry):
        """Export as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{inquiry.code}_export.csv"'

        writer = csv.writer(response)

        # Write headers
        headers = [field.display_name for field in fields]
        writer.writerow(headers)

        # Write data
        for row in data:
            row_data = []
            for field in fields:
                value = row.get(field.field_path, '')
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                row_data.append(value)
            writer.writerow(row_data)

        return response

    def export_excel(self, data, fields, inquiry):
        """Export as Excel"""
        wb = Workbook()
        ws = wb.active
        ws.title = inquiry.display_name[:31]  # Excel sheet name limit

        # Write headers
        headers = [field.display_name for field in fields]
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)

        # Write data
        for row_idx, row in enumerate(data, 2):
            for col_idx, field in enumerate(fields, 1):
                value = row.get(field.field_path, '')
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                ws.cell(row=row_idx, column=col_idx, value=value)

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{inquiry.code}_export.xlsx"'
        wb.save(response)

        return response

    def export_json(self, data, inquiry):
        """Export as JSON"""
        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{inquiry.code}_export.json"'

        export_data = {
            'inquiry': {
                'name': inquiry.name,
                'code': inquiry.code,
                'exported_at': time.strftime('%Y-%m-%d %H:%M:%S')
            },
            'data': data,
            'count': len(data)
        }

        json.dump(export_data, response, indent=2)
        return response


class InquiryTemplateViewSet(viewsets.ModelViewSet):
    """CRUD for saved inquiry templates"""
    queryset = InquiryTemplate.objects.all()
    serializer_class = InquiryTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by ownership
        return queryset.filter(
            created_by=self.request.user
        ) | queryset.filter(is_public=True)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)