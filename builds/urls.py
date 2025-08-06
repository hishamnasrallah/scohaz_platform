# File: builds/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BuildViewSet

router = DefaultRouter()
router.register(r'', BuildViewSet, basename='build')

urlpatterns = [
    path('', include(router.urls)),
]