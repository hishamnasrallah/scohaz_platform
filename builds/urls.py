# File: builds/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
# Router registrations will be added in Phase 4

urlpatterns = [
    path('', include(router.urls)),
]