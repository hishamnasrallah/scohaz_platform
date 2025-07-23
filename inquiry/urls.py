from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .apis.views import (
    InquiryConfigurationViewSet,
    InquiryExecutionViewSet,
    InquiryTemplateViewSet,
    InquiryFieldViewSet,
    InquiryFilterViewSet,
    InquiryRelationViewSet,
    InquirySortViewSet,
    InquiryPermissionViewSet
)

app_name = 'inquiry'

router = DefaultRouter()
router.register(r'configurations', InquiryConfigurationViewSet)
router.register(r'templates', InquiryTemplateViewSet)
router.register(r'fields', InquiryFieldViewSet)
router.register(r'filters', InquiryFilterViewSet)
router.register(r'relations', InquiryRelationViewSet)
router.register(r'sorts', InquirySortViewSet)
router.register(r'permissions', InquiryPermissionViewSet)

urlpatterns = [
    path('', include(router.urls)),

    # Execution endpoints
    path('execute/<str:code>/',
         InquiryExecutionViewSet.as_view({'post': 'execute'}),
         name='execute-inquiry'),

    path('schema/<str:code>/',
         InquiryExecutionViewSet.as_view({'get': 'schema'}),
         name='inquiry-schema'),
]