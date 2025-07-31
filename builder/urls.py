from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WidgetMappingViewSet, GenerationConfigViewSet,
    CodePreviewAPIView, GenerateProjectAPIView,
    TranslationKeysAPIView
)

app_name = 'builder'

router = DefaultRouter()
router.register(r'widget-mappings', WidgetMappingViewSet, basename='widgetmapping')
router.register(r'generation-configs', GenerationConfigViewSet, basename='generationconfig')

urlpatterns = [
    path('', include(router.urls)),
    path('generate-preview/', CodePreviewAPIView.as_view(), name='generate-preview'),
    path('generate-project/', GenerateProjectAPIView.as_view(), name='generate-project'),
    path('translation-keys/', TranslationKeysAPIView.as_view(), name='translation-keys'),
]