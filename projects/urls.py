# File: projects/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FlutterProjectViewSet,
    ComponentTemplateViewSet,
    ScreenViewSet,
    CanvasStateViewSet,
    ValidationViewSet,
    ProjectAssetViewSet,
    WidgetTemplateViewSet,
    StylePresetViewSet
)

router = DefaultRouter()
router.register(r'flutter-projects', FlutterProjectViewSet, basename='flutter-project')
router.register(r'component-templates', ComponentTemplateViewSet, basename='component-template')
router.register(r'screens', ScreenViewSet, basename='screen')
router.register(r'canvas-states', CanvasStateViewSet, basename='canvas-state')
router.register(r'validation', ValidationViewSet, basename='validation')
router.register(r'assets', ProjectAssetViewSet, basename='project-asset')
router.register(r'widget-templates', WidgetTemplateViewSet, basename='widget-template')
router.register(r'style-presets', StylePresetViewSet, basename='style-preset')

urlpatterns = [
    path('', include(router.urls)),
]

# The enhanced ComponentTemplateViewSet now provides these endpoints automatically:
#
# EXISTING ENDPOINTS:
# GET  /api/projects/component-templates/                    - List all components
# GET  /api/projects/component-templates/{id}/               - Get specific component
# GET  /api/projects/component-templates/by_category/        - Components grouped by category
#
# NEW BUILDER-SPECIFIC ENDPOINTS:
# GET  /api/projects/component-templates/components/         - Components optimized for builder
# GET  /api/projects/component-templates/organized/          - Components grouped by widget_group
# GET  /api/projects/component-templates/widget-groups/      - List of widget groups
# GET  /api/projects/component-templates/categories/         - List of categories
#
# SCREEN ENDPOINTS:
# GET  /api/projects/screens/                                - List screens
# POST /api/projects/screens/                                - Create screen
# GET  /api/projects/screens/{id}/                           - Get screen
# PUT  /api/projects/screens/{id}/                           - Update screen
# PUT  /api/projects/screens/{id}/update_ui_structure/       - Update only UI structure
# POST /api/projects/screens/{id}/set_as_home/              - Set as home screen
# POST /api/projects/screens/{id}/duplicate/                - Duplicate screen