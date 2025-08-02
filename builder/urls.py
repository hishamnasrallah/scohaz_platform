# File: builder/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
# Router registrations will be added in Phase 2 and Phase 3

urlpatterns = [
    path('', include(router.urls)),
]