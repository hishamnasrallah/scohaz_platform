from django.urls import path, include
from rest_framework.routers import DefaultRouter

from dynamicflow import workflow_urls
from dynamicflow.apis.views import (
    FlowAPIView,
    FieldTypeViewSet, PageViewSet, CategoryViewSet,
    FieldViewSet, ConditionViewSet
)
from dynamicflow.apis.workflow_container_serializers import WorkflowViewSet


# Original router for existing endpoints
router = DefaultRouter()
router.register(r'field-types', FieldTypeViewSet, basename='fieldtype')
router.register(r'pages', PageViewSet, basename='page')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'fields', FieldViewSet, basename='field')
router.register(r'conditions', ConditionViewSet, basename='condition')

# Workflow container router
workflow_container_router = DefaultRouter()
workflow_container_router.register(r'workflows', WorkflowViewSet, basename='workflow')

urlpatterns = [
    # Original endpoints (unchanged for eservice)
    path('service_flow/', FlowAPIView.as_view(), name='services_flow'),
    path('api/v1/', include(router.urls)),

    # Workflow builder specific endpoints
    path('workflow/', include(workflow_urls)),

    # Workflow container management
    path('', include(workflow_container_router.urls)),
]

app_name = 'form_api'