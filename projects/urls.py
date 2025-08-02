# File: projects/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FlutterProjectViewSet, ComponentTemplateViewSet, ScreenViewSet

router = DefaultRouter()
router.register(r'flutter-projects', FlutterProjectViewSet, basename='flutter-project')
router.register(r'component-templates', ComponentTemplateViewSet, basename='component-template')
router.register(r'screens', ScreenViewSet, basename='screen')

urlpatterns = [
    path('', include(router.urls)),
]