from rest_framework import generics
from app_builder.models import Application, ModelDefinition
from app_builder.serializers.application_serializer import ApplicationSerializer, ModelDefinitionSerializer

class ApplicationListView(generics.ListCreateAPIView):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer

class ApplicationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
