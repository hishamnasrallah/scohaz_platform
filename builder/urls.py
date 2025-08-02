# File: builder/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WidgetMappingViewSet, CodeGeneratorViewSet

router = DefaultRouter()
router.register(r'widget-mappings', WidgetMappingViewSet, basename='widget-mapping')
router.register(r'code-generator', CodeGeneratorViewSet, basename='code-generator')

urlpatterns = [
    path('', include(router.urls)),
]