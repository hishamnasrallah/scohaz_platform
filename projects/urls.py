from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FlutterProjectViewSet, ScreenViewSet, ComponentTemplateViewSet

app_name = 'projects'

router = DefaultRouter()
router.register(r'projects', FlutterProjectViewSet, basename='flutterproject')
router.register(r'screens', ScreenViewSet, basename='screen')
router.register(r'components', ComponentTemplateViewSet, basename='componenttemplate')

urlpatterns = [
    path('', include(router.urls)),
]

# API endpoints created by this configuration:
#
# Projects:
# - GET/POST    /api/projects/                    - List/Create projects
# - GET/PUT/DELETE /api/projects/{id}/            - Project detail
# - POST        /api/projects/{id}/set_version/   - Create initial version
# - POST        /api/projects/{id}/update_version/ - Update version number
# - POST        /api/projects/{id}/add_language/  - Add language support
# - POST        /api/projects/{id}/remove_language/ - Remove language
# - GET         /api/projects/{id}/screens/       - List project screens
# - POST        /api/projects/{id}/create_default_screen/ - Create home screen
#
# Screens:
# - GET/POST    /api/screens/                     - List/Create screens
# - GET/PUT/DELETE /api/screens/{id}/             - Screen detail
# - POST        /api/screens/{id}/set_as_home/    - Set as home screen
# - POST        /api/screens/{id}/duplicate/      - Duplicate screen