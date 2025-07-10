# reporting_templates/views.py - WITH FULL CRUD
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from rest_framework import generics, views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from simple_reporting.models import PDFTemplate, PDFElement
from .serializers import (
    PDFTemplateSerializer,
    GeneratePDFSerializer,
    PDFElementSerializer, ContentTypeSerializer
)
from simple_reporting.services import DataService, PDFGenerator


# ========== TEMPLATE CRUD ==========

class PDFTemplateListCreateView(generics.ListCreateAPIView):
    """List all templates or create a new one"""
    queryset = PDFTemplate.objects.filter(active=True)
    serializer_class = PDFTemplateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Set the user who created the template
        serializer.save(created_by=self.request.user)


class PDFTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update or delete a template"""
    queryset = PDFTemplate.objects.filter(active=True)
    serializer_class = PDFTemplateSerializer
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        # Soft delete - just mark as inactive
        instance.active = False
        instance.save()


# ========== ELEMENT CRUD ==========

class PDFElementListCreateView(generics.ListCreateAPIView):
    """List elements for a template or create new ones"""
    serializer_class = PDFElementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filter by template if provided
        template_id = self.request.query_params.get('template_id')
        if template_id:
            return PDFElement.objects.filter(template_id=template_id)
        return PDFElement.objects.all()


class PDFElementDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update or delete an element"""
    queryset = PDFElement.objects.all()
    serializer_class = PDFElementSerializer
    permission_classes = [IsAuthenticated]


# ========== BULK OPERATIONS ==========

class PDFTemplateBulkCreateView(views.APIView):
    """Create template with elements in one request"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Extract template data
        template_data = {
            'name': request.data.get('name'),
            'code': request.data.get('code'),
            'page_size': request.data.get('page_size', 'A4'),
            'content_type': request.data.get('content_type'),
            'query_filter': request.data.get('query_filter', {}),
            'active': request.data.get('active', True)
        }

        # Create template
        template_serializer = PDFTemplateSerializer(data=template_data)
        if not template_serializer.is_valid():
            return Response(
                template_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        template = template_serializer.save(created_by=request.user)

        # Create elements if provided
        elements_data = request.data.get('elements', [])
        created_elements = []

        for element_data in elements_data:
            element_data['template'] = template.id
            element_serializer = PDFElementSerializer(data=element_data)
            if element_serializer.is_valid():
                element = element_serializer.save()
                created_elements.append(element)
            else:
                # Rollback - delete template and elements
                template.delete()
                return Response(
                    {
                        'error': 'Element creation failed',
                        'details': element_serializer.errors
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Return complete template with elements
        response_data = PDFTemplateSerializer(
            template,
            context={'request': request}
        ).data

        return Response(response_data, status=status.HTTP_201_CREATED)


class PDFTemplateDuplicateView(views.APIView):
    """Duplicate an existing template"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            # Get original template
            original = PDFTemplate.objects.get(pk=pk)

            # Create copy
            new_template = PDFTemplate.objects.create(
                name=f"{original.name} (Copy)",
                code=f"{original.code}_copy_{request.user.id}",
                page_size=original.page_size,
                content_type=original.content_type,
                query_filter=original.query_filter,
                created_by=request.user,
                active=True
            )

            # Copy elements
            for element in original.elements.all():
                PDFElement.objects.create(
                    template=new_template,
                    x_position=element.x_position,
                    y_position=element.y_position,
                    text_content=element.text_content,
                    is_dynamic=element.is_dynamic,
                    font_size=element.font_size
                )

            return Response(
                PDFTemplateSerializer(
                    new_template,
                    context={'request': request}
                ).data,
                status=status.HTTP_201_CREATED
            )

        except PDFTemplate.DoesNotExist:
            return Response(
                {'error': 'Template not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ========== PDF GENERATION (unchanged) ==========

class GeneratePDFView(views.APIView):
    """Generate PDF from template"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GeneratePDFSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get template
        template = PDFTemplate.objects.get(
            id=serializer.validated_data['template_id']
        )

        # Fetch data
        data_service = DataService(
            template=template,
            object_id=serializer.validated_data.get('object_id')
        )
        data = data_service.fetch_data()

        if not data:
            return Response(
                {'error': 'No data found'},
                status=404
            )

        # Generate PDF
        generator = PDFGenerator(template)
        pdf_buffer = generator.generate(data)

        # Return PDF
        response = HttpResponse(
            pdf_buffer.getvalue(),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{template.code}.pdf"'

        return response


class ContentTypeListView(views.APIView):
    """List available content types for template creation"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # You can filter content types to only show specific models
        # For example, exclude Django's built-in models
        excluded_apps = ['admin', 'auth', 'contenttypes', 'sessions']

        content_types = ContentType.objects.exclude(
            app_label__in=excluded_apps
        ).order_by('app_label', 'model')

        serializer = ContentTypeSerializer(content_types, many=True)
        return Response(serializer.data)

# Add this URL pattern to your main urls.py or simple_reporting/urls.py:
# path('api/content-types/', ContentTypeListView.as_view(), name='content-types'),

# Optional: If you want to provide model fields for query building
class ContentTypeFieldsView(views.APIView):
    """Get fields for a specific content type"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            content_type = ContentType.objects.get(pk=pk)
            model_class = content_type.model_class()

            if not model_class:
                return Response({'error': 'Model class not found'}, status=404)

            fields = []
            for field in model_class._meta.get_fields():
                fields.append({
                    'name': field.name,
                    'verbose_name': getattr(field, 'verbose_name', field.name),
                    'type': field.__class__.__name__,
                    'is_relation': field.is_relation,
                    'related_model': field.related_model.__name__ if field.is_relation else None
                })

            return Response({
                'model': content_type.model,
                'app_label': content_type.app_label,
                'fields': fields
            })

        except ContentType.DoesNotExist:
            return Response({'error': 'Content type not found'}, status=404)