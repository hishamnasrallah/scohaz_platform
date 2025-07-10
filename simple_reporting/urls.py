# reporting_templates/urls.py - WITH FULL CRUD

from django.urls import path
from simple_reporting.apis.views import (
    PDFTemplateListCreateView,
    PDFTemplateDetailView,
    PDFElementListCreateView,
    PDFElementDetailView,
    PDFTemplateBulkCreateView,
    PDFTemplateDuplicateView,
    GeneratePDFView, ContentTypeListView
)

urlpatterns = [

    # Template CRUD
    path('templates/', PDFTemplateListCreateView.as_view(), name='pdf-template-list-create'),
    path('templates/<int:pk>/', PDFTemplateDetailView.as_view(), name='pdf-template-detail'),

    # Element CRUD
    path('elements/', PDFElementListCreateView.as_view(), name='pdf-element-list-create'),
    path('elements/<int:pk>/', PDFElementDetailView.as_view(), name='pdf-element-detail'),

    # Bulk/Special operations
    path('templates/bulk-create/', PDFTemplateBulkCreateView.as_view(), name='pdf-template-bulk-create'),
    path('templates/<int:pk>/duplicate/', PDFTemplateDuplicateView.as_view(), name='pdf-template-duplicate'),

    # PDF Generation
    path('generate/', GeneratePDFView.as_view(), name='pdf-generate'),

    # Content Types
    path('content-types/', ContentTypeListView.as_view(), name='pdf-generate'),


]