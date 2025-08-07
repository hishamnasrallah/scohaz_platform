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

# Available endpoints with the enhanced CodeGeneratorViewSet:
#
# EXISTING ENDPOINTS:
# POST /api/builder/code-generator/generate_code/           - Generate complete project code
# POST /api/builder/code-generator/download_project/        - Download project as ZIP
#
# NEW ENHANCED ENDPOINTS:
# POST /api/builder/code-generator/generate-widget/         - Generate single widget code with options
# POST /api/builder/code-generator/generate-screen/         - Generate screen code with options
# POST /api/builder/code-generator/validate-code/           - Validate widget structure
# POST /api/builder/code-generator/download-widget/         - Download widget as .dart file
# POST /api/builder/code-generator/copy-code/               - Prepare code for copying
# GET  /api/builder/code-generator/code-templates/          - Get widget templates
# POST /api/builder/code-generator/optimize-code/           - Optimize code for const constructors
#
# WIDGET MAPPING ENDPOINTS:
# GET  /api/builder/widget-mappings/                        - List all widget mappings
# GET  /api/builder/widget-mappings/{id}/                   - Get specific widget mapping
# POST /api/builder/widget-mappings/                        - Create widget mapping
# PUT  /api/builder/widget-mappings/{id}/                   - Update widget mapping
# DELETE /api/builder/widget-mappings/{id}/                 - Delete widget mapping