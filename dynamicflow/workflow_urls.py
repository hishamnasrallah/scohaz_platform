# Update dynamicflow/workflow_urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from dynamicflow.apis.workflow_container_serializers import WorkflowViewSet
from dynamicflow.apis.workflow_views import (
    WorkflowFieldTypeViewSet, WorkflowPageViewSet,
    WorkflowCategoryViewSet, WorkflowFieldViewSet,
    WorkflowConditionViewSet
)
from dynamicflow.apis.workflow_service_flow_view import WorkflowServiceFlowAPIView

# Router for workflow-specific endpoints
workflow_router = DefaultRouter()
workflow_router.register(r'field-types', WorkflowFieldTypeViewSet, basename='workflow-fieldtype')
workflow_router.register(r'pages', WorkflowPageViewSet, basename='workflow-page')
workflow_router.register(r'categories', WorkflowCategoryViewSet, basename='workflow-category')
workflow_router.register(r'fields', WorkflowFieldViewSet, basename='workflow-field')
workflow_router.register(r'conditions', WorkflowConditionViewSet, basename='workflow-condition')

# Main router for dynamic endpoints
main_router = DefaultRouter()
main_router.register(r'workflows', WorkflowViewSet, basename='workflow')

urlpatterns = [
    # Workflow builder specific service flow endpoint
    path('service_flow/', WorkflowServiceFlowAPIView.as_view(), name='workflow_service_flow'),

    # Workflow builder CRUD APIs
    path('api/v1/', include(workflow_router.urls)),

    # Workflow container management (outside /workflow/ prefix)
    # This makes URLs like /dynamic/workflows/ instead of /dynamic/workflow/workflows/
]