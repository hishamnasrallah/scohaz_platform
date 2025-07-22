from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .apis.views import (
    InquiryConfigurationViewSet,
    InquiryExecutionViewSet,
    InquiryTemplateViewSet
)

app_name = 'inquiry'

router = DefaultRouter()
router.register(r'configurations', InquiryConfigurationViewSet)
router.register(r'templates', InquiryTemplateViewSet)

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