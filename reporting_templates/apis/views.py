from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django_filters import rest_framework as filters
import json
from datetime import datetime

from authentication.crud.managers import user_can
from reporting_templates.models import (
    PDFTemplate, PDFTemplateElement,
    PDFTemplateVariable, PDFGenerationLog
)
from .serializers import (
    PDFTemplateSerializer, PDFTemplateCreateSerializer,
    PDFTemplateElementSerializer, PDFTemplateVariableSerializer,
    PDFGenerationLogSerializer, PDFGenerateSerializer,
    TemplatePreviewSerializer, ContentTypeSerializer
)
from reporting_templates.services.pdf_generator import PDFGenerator, PDFTemplateService
from .permissions import PDFTemplatePermission


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

    class Meta:
        model = PDFTemplate
        fields = ['name', 'code', 'language', 'content_type', 'created_by', 'active']


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
    def preview_data(self, request, pk=None):
        """Get sample data for template preview"""
        template = self.get_object()

        # Build sample data based on template variables
        sample_data = {
            'user': {
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'full_name': request.user.get_full_name(),
            },
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'current_time': datetime.now().strftime('%H:%M:%S'),
        }

        # Add sample data for template variables
        for variable in template.variables.all():
            if variable.default_value:
                sample_data[variable.variable_key] = variable.default_value
            else:
                # Generate sample based on data type
                if variable.data_type == 'text':
                    sample_data[variable.variable_key] = f"Sample {variable.display_name}"
                elif variable.data_type == 'number':
                    sample_data[variable.variable_key] = 123
                elif variable.data_type == 'date':
                    sample_data[variable.variable_key] = datetime.now().strftime('%Y-%m-%d')
                elif variable.data_type == 'boolean':
                    sample_data[variable.variable_key] = True

        return Response({
            'template': PDFTemplateSerializer(
                template,
                context={'request': request}
            ).data,
            'sample_data': sample_data
        })

    @action(detail=True, methods=['post'])
    def test_generate(self, request, pk=None):
        """Test generate PDF with sample data"""
        template = self.get_object()

        # Get sample data
        context_data = request.data.get('context_data', {})
        if not context_data:
            # Use preview data
            preview_response = self.preview_data(request, pk)
            context_data = preview_response.data['sample_data']

        # Add user to context
        context_data['user'] = request.user

        try:
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
    filterset_fields = ['template', 'status', 'generated_by']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter logs based on user permissions"""
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_superuser:
            # Only show user's own logs
            queryset = queryset.filter(generated_by=user)

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

        # Get template
        template = PDFTemplate.objects.get(
            id=serializer.validated_data['template_id']
        )

        # Get context data
        context_data = serializer.validated_data['context_data']
        context_data['user'] = request.user

        # Get language
        language = serializer.validated_data.get(
            'language',
            template.primary_language
        )

        try:
            # Generate PDF
            generator = PDFGenerator(template, language=language)
            pdf_buffer = generator.generate_pdf(context_data)

            # Prepare filename
            filename = serializer.validated_data.get(
                'filename',
                f"{template.code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )

            # Return PDF
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PreviewPDFView(APIView):
    """API view for previewing PDF design"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Preview PDF without saving template"""
        serializer = TemplatePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create temporary template
        temp_template = PDFTemplate(
            name="Preview Template",
            code="preview",
            page_size=serializer.validated_data['page_size'],
            orientation=serializer.validated_data['orientation'],
            primary_language=serializer.validated_data['language']
        )

        try:
            # Generate PDF with temporary elements
            generator = PDFGenerator(temp_template)

            # Temporarily assign elements
            temp_template._temp_elements = serializer.validated_data['elements']

            # Override the elements property for preview
            original_elements = PDFTemplateElement.objects.none()
            PDFTemplateElement.objects.filter = lambda **kwargs: [
                PDFTemplateElement(**elem) for elem in temp_template._temp_elements
            ]

            # Generate preview
            context_data = serializer.validated_data.get('context_data', {})
            context_data['user'] = request.user

            pdf_buffer = generator.generate_pdf(context_data)

            # Return preview
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = 'inline; filename="preview.pdf"'
            return response

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ContentTypeListView(APIView):
    """List available content types for templates"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get content types from user's apps"""
        # Get apps from settings
        from django.conf import settings

        # Filter to only show models from custom apps
        custom_apps = getattr(settings, 'CUSTOM_APPS', [])
        custom_apps.extend(['authentication', 'case'])  # Add your core apps

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
                {'value': 'line', 'label': 'Line', 'icon': 'minus'},
                {'value': 'rectangle', 'label': 'Rectangle', 'icon': 'square'},
                {'value': 'circle', 'label': 'Circle', 'icon': 'circle'},
                {'value': 'table', 'label': 'Table', 'icon': 'table'},
                {'value': 'barcode', 'label': 'Barcode', 'icon': 'barcode'},
                {'value': 'qrcode', 'label': 'QR Code', 'icon': 'qrcode'},
                {'value': 'signature', 'label': 'Signature Field', 'icon': 'signature'},
            ],
            'page_sizes': [
                {'value': 'A4', 'label': 'A4 (210 × 297 mm)'},
                {'value': 'A3', 'label': 'A3 (297 × 420 mm)'},
                {'value': 'letter', 'label': 'Letter (8.5 × 11 in)'},
                {'value': 'legal', 'label': 'Legal (8.5 × 14 in)'},
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
            ],
            'default_colors': [
                '#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF',
                '#FFFF00', '#FF00FF', '#00FFFF', '#808080', '#C0C0C0'
            ]
        }

        return Response(data)