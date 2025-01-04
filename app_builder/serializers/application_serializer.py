from rest_framework import serializers
from app_builder.models import Application, ModelDefinition

class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = '__all__'

class ModelDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelDefinition
        fields = '__all__'
