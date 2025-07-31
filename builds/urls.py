from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BuildViewSet, TriggerBuildAPIView,
    BuildStatsAPIView, BuildStatusWebSocketView
)

app_name = 'builds'

router = DefaultRouter()
router.register(r'builds', BuildViewSet, basename='build')

urlpatterns = [
    path('', include(router.urls)),
    path('build/', TriggerBuildAPIView.as_view(), name='trigger-build'),
    path('stats/', BuildStatsAPIView.as_view(), name='build-stats'),
    path('builds/<int:build_id>/status/', BuildStatusWebSocketView.as_view(), name='build-status'),
]