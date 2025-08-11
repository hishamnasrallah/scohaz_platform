from django.urls import path, include
from rest_framework.routers import DefaultRouter

from builds.views import BuildViewSet

# from .views import BuildViewSet

router = DefaultRouter()
router.register(r'', BuildViewSet, basename='build')

urlpatterns = [
    path('', include(router.urls)),
]