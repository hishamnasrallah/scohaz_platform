from django.urls import path, include
from rest_framework.routers import DefaultRouter

from reporting_templates.apis.views import (
    PDFTemplateViewSet, PDFTemplateElementViewSet,
    PDFTemplateVariableViewSet, PDFGenerationLogViewSet,
    GeneratePDFView, PreviewPDFView, ContentTypeListView,
    TemplateDesignerDataView
)

router = DefaultRouter()
router.register(r'templates', PDFTemplateViewSet, basename='pdftemplate')
router.register(r'elements', PDFTemplateElementViewSet, basename='pdfelement')
router.register(r'variables', PDFTemplateVariableViewSet, basename='pdfvariable')
router.register(r'logs', PDFGenerationLogViewSet, basename='pdflog')

urlpatterns = [
    path('', include(router.urls)),
    path('generate/', GeneratePDFView.as_view(), name='pdf-generate'),
    path('preview/', PreviewPDFView.as_view(), name='pdf-preview'),
    path('content-types/', ContentTypeListView.as_view(), name='pdf-content-types'),
    path('designer-data/', TemplateDesignerDataView.as_view(), name='pdf-designer-data'),
]