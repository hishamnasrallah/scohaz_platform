from rest_framework.routers import DefaultRouter
from django.urls import path, include
from lowcode.apis.views import (FieldTypeViewSet,
                                PageViewSet, CategoryViewSet,
                                FieldViewSet)

router = DefaultRouter()
router.register(r'field-types', FieldTypeViewSet)
router.register(r'pages', PageViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'fields', FieldViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
