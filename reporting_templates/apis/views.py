# reporting_templates/apis/views.py
from typing import Dict, Any

from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.db.models import Q, Prefetch
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django_filters import rest_framework as filters
import json
from datetime import datetime

from authentication.crud.managers import user_can
from reporting_templates.models import (
    PDFTemplate, PDFTemplateElement, PDFTemplateVariable,
    PDFTemplateParameter, PDFTemplateDataSource, PDFGenerationLog
)
from reporting_templates.services.data_service import DataFetchingService
from reporting_templates.services.pdf_generator import PDFGenerator, PDFTemplateService
from .serializers import (
    PDFTemplateSerializer, PDFTemplateCreateSerializer,
    PDFTemplateElementSerializer, PDFTemplateVariableSerializer,
    PDFTemplateParameterSerializer, PDFTemplateDataSourceSerializer,
    PDFGenerationLogSerializer, PDFGenerateSerializer,
    TemplatePreviewSerializer, ContentTypeSerializer,
    ParameterSchemaSerializer
)
from .permissions import PDFTemplatePermission

User = get_user_model()


class PDFTemplateFilter(filters.FilterSet):
    """Filter for PDF templates"""
    name = filters.CharFilter(lookup_expr='icontains')
    code = filters.CharFilter(lookup_expr='icontains')
    language = filters.ChoiceFilter(
        field_name='primary_language',
        choices=[('en', 'English'), ('ar', 'Arabic')]
    )
    content_type = filters.NumberFilter(field_name='content_type__id')
    created_by = filters.NumberFilter(field_name='created_by__id')
    active = filters.BooleanFilter(field_name='active_ind')
    requires_parameters = filters.BooleanFilter()
    allow_self = filters.BooleanFilter(field_name='allow_self_generation')
    allow_others = filters.BooleanFilter(field_name='allow_other_generation')

    class Meta:
        model = PDFTemplate
        fields = [
            'name', 'code', 'language', 'content_type', 'created_by',
            'active', 'requires_parameters', 'allow_self', 'allow_others'
        ]


class PDFTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PDF Template CRUD operations
    """
    queryset = PDFTemplate.objects.all()
    serializer_class = PDFTemplateSerializer
    permission_classes = [IsAuthenticated, PDFTemplatePermission]
    filterset_class = PDFTemplateFilter
    search_fields = ['name', 'name_ara', 'code', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PDFTemplateCreateSerializer
        return PDFTemplateSerializer

    def get_queryset(self):
        """Filter templates based on user permissions"""
        queryset = super().get_queryset()
        user = self.request.user

        # Prefetch related data
        queryset = queryset.prefetch_related(
            'elements',
            'variables',
            'parameters',
            'data_sources',
            'groups',
            Prefetch('generation_logs', queryset=PDFGenerationLog.objects.order_by('-created_at')[:5])
        )

        if not user.is_superuser:
            # Filter by user's groups or created by user
            user_groups = user.groups.all()
            queryset = queryset.filter(
                Q(created_by=user) |
                Q(groups__in=user_groups) |
                Q(groups__isnull=True)
            ).distinct()

        return queryset

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a template"""
        template = self.get_object()
        new_name = request.data.get('name', f"{template.name} (Copy)")

        try:
            new_template = PDFTemplateService.duplicate_template(
                template, new_name
            )
            serializer = PDFTemplateSerializer(
                new_template,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def parameter_schema(self, request, pk=None):
        """Get parameter schema for template"""
        template = self.get_object()

        schema = {
            'template': {
                'id': template.id,
                'name': template.name,
                'requires_parameters': template.requires_parameters,
                'allow_self_generation': template.allow_self_generation,
                'allow_other_generation': template.allow_other_generation,
            },
            'parameters': PDFTemplateParameterSerializer(
                template.parameters.filter(active_ind=True),
                many=True,
                context={'request': request}
            ).data,
            'sample_values': {}
        }

        # Add sample values if requested
        if request.query_params.get('include_samples', 'false').lower() == 'true':
            for param in template.parameters.filter(active_ind=True):
                if param.default_value:
                    schema['sample_values'][param.parameter_key] = param.default_value
                elif param.parameter_type == 'integer':
                    schema['sample_values'][param.parameter_key] = 123
                elif param.parameter_type == 'string':
                    schema['sample_values'][param.parameter_key] = f"Sample {param.display_name}"
                elif param.parameter_type == 'date':
                    schema['sample_values'][param.parameter_key] = datetime.now().strftime('%Y-%m-%d')
                elif param.parameter_type == 'boolean':
                    schema['sample_values'][param.parameter_key] = True

        return Response(schema)

    @action(detail=True, methods=['get'])
    def available_data(self, request, pk=None):
        """Get available data structure for template"""
        template = self.get_object()

        # Simulate data fetching to show structure
        try:
            service = DataFetchingService(
                template=template,
                user=request.user,
                parameters={}
            )

            # Get structure without actually fetching data
            available_data = {
                'main_data_source': {
                    'type': template.data_source_type,
                    'model': template.content_type.model if template.content_type else None,
                    'fields': []
                },
                'additional_sources': {},
                'variables': {}
            }

            # Add model fields if model-based
            if template.content_type:
                model_class = template.content_type.model_class()
                if model_class:
                    fields = []
                    for field in model_class._meta.fields:
                        fields.append({
                            'name': field.name,
                            'type': field.__class__.__name__,
                            'verbose_name': str(field.verbose_name)
                        })
                    available_data['main_data_source']['fields'] = fields

            # Add additional data sources
            for source in template.data_sources.filter(active_ind=True):
                available_data['additional_sources'][source.source_key] = {
                    'display_name': source.display_name,
                    'fetch_method': source.fetch_method,
                    'model': source.content_type.model if source.content_type else None
                }

            # Add variables
            for var in template.variables.all():
                available_data['variables'][var.variable_key] = {
                    'display_name': var.display_name,
                    'data_type': var.data_type,
                    'data_source': var.data_source,
                    'default_value': var.default_value
                }

            return Response(available_data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def validate_parameters(self, request, pk=None):
        """Validate parameters without generating PDF"""
        template = self.get_object()
        parameters = request.data.get('parameters', {})

        try:
            service = DataFetchingService(
                template=template,
                user=request.user,
                parameters=parameters
            )

            # This will validate parameters
            service._validate_parameters()

            return Response({
                'valid': True,
                'message': 'All parameters are valid'
            })

        except ValueError as e:
            return Response({
                'valid': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def preview_data(self, request, pk=None):
        """Preview data that will be used in template"""
        template = self.get_object()
        parameters = request.data.get('parameters', {})

        try:
            service = DataFetchingService(
                template=template,
                user=request.user,
                parameters=parameters
            )

            # Fetch all data
            context_data = service.fetch_all_data()

            # Convert model instances to dictionaries for JSON serialization
            preview_data = self._serialize_context_data(context_data)

            return Response({
                'template': PDFTemplateSerializer(
                    template,
                    context={'request': request}
                ).data,
                'data': preview_data,
                'parameters_used': parameters
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def test_generate(self, request, pk=None):
        """Test generate PDF with provided or sample data"""
        template = self.get_object()

        # Get parameters
        parameters = request.data.get('parameters', {})
        use_sample_data = request.data.get('use_sample_data', False)

        try:
            # Fetch data
            service = DataFetchingService(
                template=template,
                user=request.user,
                parameters=parameters
            )
            context_data = service.fetch_all_data()

            # Generate PDF
            generator = PDFGenerator(
                template,
                language=request.data.get('language', template.primary_language)
            )
            pdf_buffer = generator.generate_pdf(context_data)

            # Return PDF
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'inline; filename="{template.code}_test.pdf"'
            return response

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _serialize_context_data(self, context_data):
        """Convert context data to JSON-serializable format"""
        serialized = {}

        for key, value in context_data.items():
            if hasattr(value, '_meta'):  # Django model instance
                serialized[key] = {
                    'model': value._meta.label,
                    'pk': value.pk,
                    'str': str(value),
                    # Add more fields as needed
                }
            elif hasattr(value, 'all'):  # QuerySet
                serialized[key] = [
                    {'pk': obj.pk, 'str': str(obj)}
                    for obj in value[:10]  # Limit to 10 for preview
                ]
            elif isinstance(value, (dict, list, str, int, float, bool, type(None))):
                serialized[key] = value
            else:
                serialized[key] = str(value)

        return serialized


class PDFTemplateParameterViewSet(viewsets.ModelViewSet):
    """ViewSet for template parameters"""
    queryset = PDFTemplateParameter.objects.all()
    serializer_class = PDFTemplateParameterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by template if provided"""
        queryset = super().get_queryset()
        template_id = self.request.query_params.get('template')

        if template_id:
            queryset = queryset.filter(template_id=template_id)

        return queryset.order_by('order', 'parameter_key')


class PDFTemplateDataSourceViewSet(viewsets.ModelViewSet):
    """ViewSet for template data sources"""
    queryset = PDFTemplateDataSource.objects.all()
    serializer_class = PDFTemplateDataSourceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by template if provided"""
        queryset = super().get_queryset()
        template_id = self.request.query_params.get('template')

        if template_id:
            queryset = queryset.filter(template_id=template_id)

        return queryset.order_by('order', 'source_key')


class PDFTemplateElementViewSet(viewsets.ModelViewSet):
    """ViewSet for template elements"""
    queryset = PDFTemplateElement.objects.all()
    serializer_class = PDFTemplateElementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by template if provided"""
        queryset = super().get_queryset()
        template_id = self.request.query_params.get('template')

        if template_id:
            queryset = queryset.filter(template_id=template_id)

        # Include child elements
        queryset = queryset.prefetch_related('child_elements')

        return queryset.order_by('page_number', 'z_index', 'y_position')


class PDFTemplateVariableViewSet(viewsets.ModelViewSet):
    """ViewSet for template variables"""
    queryset = PDFTemplateVariable.objects.all()
    serializer_class = PDFTemplateVariableSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by template if provided"""
        queryset = super().get_queryset()
        template_id = self.request.query_params.get('template')

        if template_id:
            queryset = queryset.filter(template_id=template_id)

        return queryset


class PDFGenerationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for generation logs"""
    queryset = PDFGenerationLog.objects.all()
    serializer_class = PDFGenerationLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['template', 'status', 'generated_by', 'generated_for']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter logs based on user permissions"""
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_superuser:
            # Only show user's own logs or logs they generated
            queryset = queryset.filter(
                Q(generated_by=user) | Q(generated_for=user)
            )

        return queryset


class GeneratePDFView(APIView):
    """API view for generating PDFs"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate PDF from template"""
        serializer = PDFGenerateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Get validated data
        template = serializer.template
        parameters = serializer.validated_data.get('parameters', {})
        language = serializer.validated_data.get('language', template.primary_language)
        filename = serializer.validated_data.get('filename')
        generate_for_user_id = serializer.validated_data.get('generate_for_user_id')

        # Determine target user
        if generate_for_user_id:
            target_user = get_object_or_404(User, id=generate_for_user_id)
        else:
            target_user = request.user

        # Create log entry
        log_entry = PDFGenerationLog.objects.create(
            template=template,
            generated_by=request.user,
            generated_for=target_user if target_user != request.user else None,
            parameters=parameters,
            status='processing'
        )

        try:
            # Fetch data
            service = DataFetchingService(
                template=template,
                user=target_user,
                parameters=parameters
            )
            context_data = service.fetch_all_data()

            # Store context data in log
            log_entry.context_data = self._sanitize_context_data(context_data)
            log_entry.save()

            # Generate PDF
            generator = PDFGenerator(template, language=language)
            pdf_buffer = generator.generate_pdf(context_data)

            # Update log
            log_entry.status = 'completed'
            log_entry.completed_at = datetime.now()
            log_entry.file_size = pdf_buffer.tell()
            log_entry.save()

            # Prepare filename
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{template.code}_{timestamp}.pdf"

            # Return PDF
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            # Update log with error
            log_entry.status = 'failed'
            log_entry.error_message = str(e)
            log_entry.completed_at = datetime.now()
            log_entry.save()

            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _sanitize_context_data(self, context_data):
        """Remove sensitive data from context before storing"""
        from datetime import date, datetime
        from decimal import Decimal

        sanitized = {}

        for key, value in context_data.items():
            if key == 'user':
                # Store only basic user info
                sanitized[key] = {
                    'id': value.id,
                    'username': value.username,
                    'email': value.email
                }
            elif hasattr(value, '_meta'):
                # Model instance - store only ID
                sanitized[key] = {
                    'model': value._meta.label,
                    'pk': value.pk
                }
            elif hasattr(value, 'count'):
                # QuerySet - store count only
                sanitized[key] = {
                    'type': 'queryset',
                    'count': value.count()
                }
            # Add these new conditions
            elif isinstance(value, datetime):
                sanitized[key] = value.isoformat()
            elif isinstance(value, date):
                sanitized[key] = value.isoformat()
            elif isinstance(value, Decimal):
                sanitized[key] = float(value)
            elif isinstance(value, (list, tuple)):
                # Recursively sanitize lists
                sanitized[key] = [
                    self._sanitize_single_value(item) for item in value
                ]
            elif isinstance(value, dict):
                # Recursively sanitize dictionaries
                sanitized[key] = {
                    k: self._sanitize_single_value(v)
                    for k, v in value.items()
                }
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_single_value(self, value):
        """Helper method to sanitize individual values"""
        from datetime import date, datetime
        from decimal import Decimal

        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return float(value)
        elif hasattr(value, '_meta'):
            return {
                'model': value._meta.label,
                'pk': value.pk
            }
        return value

class MyTemplatesView(APIView):
    """Get templates available to current user"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get categorized templates"""
        user = request.user
        user_groups = user.groups.all()

        # Base queryset
        templates = PDFTemplate.objects.filter(active_ind=True)

        # Categorize templates
        response_data = {
            'self_service': [],
            'my_templates': [],
            'shared_templates': [],
            'system_templates': []
        }

        # Self-service templates (user can generate for themselves)
        self_service = templates.filter(
            allow_self_generation=True
        ).filter(
            Q(groups__in=user_groups) | Q(groups__isnull=True)
        ).distinct()

        response_data['self_service'] = PDFTemplateSerializer(
            self_service,
            many=True,
            context={'request': request}
        ).data

        # Templates created by user
        my_templates = templates.filter(created_by=user)
        response_data['my_templates'] = PDFTemplateSerializer(
            my_templates,
            many=True,
            context={'request': request}
        ).data

        # Shared templates (via groups)
        if not user.is_superuser:
            shared = templates.filter(
                groups__in=user_groups
            ).exclude(
                created_by=user
            ).distinct()
        else:
            shared = templates.exclude(created_by=user)

        response_data['shared_templates'] = PDFTemplateSerializer(
            shared,
            many=True,
            context={'request': request}
        ).data

        # System templates
        system = templates.filter(is_system_template=True)
        response_data['system_templates'] = PDFTemplateSerializer(
            system,
            many=True,
            context={'request': request}
        ).data

        # Add summary
        response_data['summary'] = {
            'total': sum(len(v) for v in response_data.values() if isinstance(v, list)),
            'can_create': user.has_perm('reporting_templates.can_design_template'),
            'can_generate_others': user.has_perm('reporting_templates.can_generate_others_pdf')
        }

        return Response(response_data)


class ContentTypeListView(APIView):
    """List available content types for templates"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get content types from user's apps"""
        # Get apps from settings
        from django.conf import settings

        # Filter to only show models from custom apps
        custom_apps = ['authentication', 'case', 'lookup']  # Add your apps

        # You can also read from settings
        if hasattr(settings, 'REPORTING_ENABLED_APPS'):
            custom_apps = settings.REPORTING_ENABLED_APPS

        content_types = ContentType.objects.filter(
            app_label__in=custom_apps
        ).exclude(
            model__in=['logentry', 'permission', 'contenttype', 'session']
        )

        serializer = ContentTypeSerializer(content_types, many=True)
        return Response(serializer.data)


class TemplateDesignerDataView(APIView):
    """Provide data needed for template designer"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get fonts, colors, and other design options"""
        data = {
            'fonts': [
                {'value': 'Helvetica', 'label': 'Helvetica'},
                {'value': 'Times-Roman', 'label': 'Times Roman'},
                {'value': 'Courier', 'label': 'Courier'},
                {'value': 'Arabic', 'label': 'Arabic Font'},
                {'value': 'Arabic-Bold', 'label': 'Arabic Bold'},
            ],
            'element_types': [
                {'value': 'text', 'label': 'Text', 'icon': 'text'},
                {'value': 'dynamic_text', 'label': 'Dynamic Text', 'icon': 'variable'},
                {'value': 'image', 'label': 'Image', 'icon': 'image'},
                {'value': 'dynamic_image', 'label': 'Dynamic Image', 'icon': 'image-plus'},
                {'value': 'line', 'label': 'Line', 'icon': 'minus'},
                {'value': 'rectangle', 'label': 'Rectangle', 'icon': 'square'},
                {'value': 'circle', 'label': 'Circle', 'icon': 'circle'},
                {'value': 'table', 'label': 'Table', 'icon': 'table'},
                {'value': 'chart', 'label': 'Chart', 'icon': 'chart-bar'},
                {'value': 'barcode', 'label': 'Barcode', 'icon': 'barcode'},
                {'value': 'qrcode', 'label': 'QR Code', 'icon': 'qrcode'},
                {'value': 'signature', 'label': 'Signature Field', 'icon': 'signature'},
                {'value': 'loop', 'label': 'Loop Container', 'icon': 'repeat'},
                {'value': 'conditional', 'label': 'Conditional Container', 'icon': 'filter'},
            ],
            'page_sizes': [
                {'value': 'A4', 'label': 'A4 (210 × 297 mm)'},
                {'value': 'A3', 'label': 'A3 (297 × 420 mm)'},
                {'value': 'letter', 'label': 'Letter (8.5 × 11 in)'},
                {'value': 'legal', 'label': 'Legal (8.5 × 14 in)'},
            ],
            'orientations': [
                {'value': 'portrait', 'label': 'Portrait'},
                {'value': 'landscape', 'label': 'Landscape'},
            ],
            'text_aligns': [
                {'value': 'left', 'label': 'Left'},
                {'value': 'center', 'label': 'Center'},
                {'value': 'right', 'label': 'Right'},
                {'value': 'justify', 'label': 'Justify'},
            ],
            'data_types': [
                {'value': 'text', 'label': 'Text'},
                {'value': 'number', 'label': 'Number'},
                {'value': 'date', 'label': 'Date'},
                {'value': 'datetime', 'label': 'Date & Time'},
                {'value': 'boolean', 'label': 'Yes/No'},
                {'value': 'image', 'label': 'Image'},
                {'value': 'list', 'label': 'List'},
                {'value': 'model', 'label': 'Model Instance'},
            ],
            'parameter_types': [
                {'value': 'integer', 'label': 'Integer'},
                {'value': 'string', 'label': 'Text'},
                {'value': 'date', 'label': 'Date'},
                {'value': 'datetime', 'label': 'Date & Time'},
                {'value': 'boolean', 'label': 'Yes/No'},
                {'value': 'float', 'label': 'Decimal'},
                {'value': 'uuid', 'label': 'UUID'},
                {'value': 'model_id', 'label': 'Model Reference'},
                {'value': 'user_id', 'label': 'User Reference'},
            ],
            'widget_types': [
                {'value': 'text', 'label': 'Text Input'},
                {'value': 'number', 'label': 'Number Input'},
                {'value': 'date', 'label': 'Date Picker'},
                {'value': 'datetime', 'label': 'DateTime Picker'},
                {'value': 'select', 'label': 'Dropdown'},
                {'value': 'radio', 'label': 'Radio Buttons'},
                {'value': 'checkbox', 'label': 'Checkbox'},
                {'value': 'user_search', 'label': 'User Search'},
                {'value': 'model_search', 'label': 'Model Search'},
            ],
            'query_operators': [
                {'value': 'exact', 'label': 'Equals'},
                {'value': 'iexact', 'label': 'Equals (case-insensitive)'},
                {'value': 'contains', 'label': 'Contains'},
                {'value': 'icontains', 'label': 'Contains (case-insensitive)'},
                {'value': 'gt', 'label': 'Greater than'},
                {'value': 'gte', 'label': 'Greater than or equal'},
                {'value': 'lt', 'label': 'Less than'},
                {'value': 'lte', 'label': 'Less than or equal'},
                {'value': 'in', 'label': 'In list'},
                {'value': 'range', 'label': 'In range'},
            ],
            'fetch_methods': [
                {'value': 'model_query', 'label': 'Model Query'},
                {'value': 'raw_sql', 'label': 'Raw SQL'},
                {'value': 'custom_function', 'label': 'Custom Function'},
                {'value': 'related_field', 'label': 'Related Field'},
                {'value': 'prefetch', 'label': 'Prefetch Related'},
            ],
            'default_colors': [
                '#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF',
                '#FFFF00', '#FF00FF', '#00FFFF', '#808080', '#C0C0C0'
            ]
        }

        return Response(data)