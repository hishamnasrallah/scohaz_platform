from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FlutterProjectViewSet, ScreenViewSet

router = DefaultRouter()
router.register(r'flutter-projects', FlutterProjectViewSet, basename='flutter-project')
router.register(r'screens', ScreenViewSet, basename='screen')

urlpatterns = [
    path('', include(router.urls)),
]