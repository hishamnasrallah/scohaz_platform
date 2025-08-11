from django.urls import path, include
from rest_framework.routers import DefaultRouter

from builder.views import WidgetMappingViewSet, CodeGeneratorViewSet
from projects.views import ComponentTemplateViewSet

# from .views import WidgetMappingViewSet, ComponentTemplateViewSet, CodeGeneratorViewSet

router = DefaultRouter()
router.register(r'widget-mappings', WidgetMappingViewSet, basename='widget-mapping')
router.register(r'component-templates', ComponentTemplateViewSet, basename='component-template')
router.register(r'code-generator', CodeGeneratorViewSet, basename='code-generator')

urlpatterns = [
    path('', include(router.urls)),
]