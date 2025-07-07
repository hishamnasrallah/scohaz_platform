# reporting_templates/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from reporting_templates.apis.views import (
    PDFTemplateViewSet, PDFTemplateElementViewSet,
    PDFTemplateVariableViewSet, PDFTemplateParameterViewSet,
    PDFTemplateDataSourceViewSet, PDFGenerationLogViewSet,
    GeneratePDFView, MyTemplatesView, ContentTypeListView,
    TemplateDesignerDataView
)

router = DefaultRouter()
router.register(r'templates', PDFTemplateViewSet, basename='pdftemplate')
router.register(r'elements', PDFTemplateElementViewSet, basename='pdfelement')
router.register(r'variables', PDFTemplateVariableViewSet, basename='pdfvariable')
router.register(r'parameters', PDFTemplateParameterViewSet, basename='pdfparameter')
router.register(r'data-sources', PDFTemplateDataSourceViewSet, basename='pdfdatasource')
router.register(r'logs', PDFGenerationLogViewSet, basename='pdflog')

urlpatterns = [
    # Main router URLs
    path('', include(router.urls)),

    # Custom views
    path('generate/', GeneratePDFView.as_view(), name='pdf-generate'),
    path('my-templates/', MyTemplatesView.as_view(), name='pdf-my-templates'),
    path('content-types/', ContentTypeListView.as_view(), name='pdf-content-types'),
    path('designer-data/', TemplateDesignerDataView.as_view(), name='pdf-designer-data'),
]