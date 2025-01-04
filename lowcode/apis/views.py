from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from dynamicflow.models import FieldType, Page, Category, Field
from lowcode.apis.serializers import (FieldTypeSerializer,
                                      PageSerializer,
                                      CategorySerializer,
                                      FieldSerializer)


class FieldTypeViewSet(viewsets.ModelViewSet):
    queryset = FieldType.objects.all()
    serializer_class = FieldTypeSerializer
    # Only superuser or staff can access
    permission_classes = [IsAuthenticated, IsAdminUser]


class PageViewSet(viewsets.ModelViewSet):
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    # Only superuser or staff can access
    permission_classes = [IsAuthenticated, IsAdminUser]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    # Only superuser or staff can access
    permission_classes = [IsAuthenticated, IsAdminUser]


class FieldViewSet(viewsets.ModelViewSet):
    queryset = Field.objects.all()
    serializer_class = FieldSerializer
    # Only superuser or staff can access
    permission_classes = [IsAuthenticated, IsAdminUser]
