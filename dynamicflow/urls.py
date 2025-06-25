# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.documentation import include_docs_urls

from dynamicflow.apis.views import (
    FlowAPIView,
    FieldTypeViewSet, PageViewSet, CategoryViewSet,
    FieldViewSet, ConditionViewSet
)
from dynamicflow.apis.additional_views import (
    FormSchemaAPIView, FormSubmissionAPIView, FormExportAPIView,
    FormImportAPIView, FormStatisticsAPIView, FieldValidationAPIView
)

# Router-based endpoints
router = DefaultRouter()
router.register(r'field-types', FieldTypeViewSet, basename='fieldtype')
router.register(r'pages', PageViewSet, basename='page')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'fields', FieldViewSet, basename='field')
router.register(r'conditions', ConditionViewSet, basename='condition')

# Main URL patterns
urlpatterns = [
    # Static API endpoints
    path('service_flow/', FlowAPIView.as_view(), name='services_flow'),

    # Core API routes
    path('api/v1/', include(router.urls)),

    # Additional form processing endpoints
    # path('api/v1/forms/<int:page_id>/schema/', FormSchemaAPIView.as_view(), name='form-schema'),
    # path('api/v1/forms/<int:page_id>/submit/', FormSubmissionAPIView.as_view(), name='form-submit'),
    # path('api/v1/forms/<int:page_id>/export/', FormExportAPIView.as_view(), name='form-export'),
    # path('api/v1/forms/import/', FormImportAPIView.as_view(), name='form-import'),
    # path('api/v1/forms/statistics/', FormStatisticsAPIView.as_view(), name='form-statistics'),
    #
    # # Field validation endpoint
    # path('api/v1/fields/<int:field_id>/validate/', FieldValidationAPIView.as_view(), name='field-validate'),
    #
    # # Browsable API docs
    # path('api/docs/', include_docs_urls(title='Form Builder API')),
    #
    # # DRF login/logout
    # path('api-auth/', include('rest_framework.urls')),
]

# Optional: namespace if included in project urls
app_name = 'form_api'
