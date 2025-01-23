from rest_framework import serializers
from app_builder.models import ApplicationDefinition, ModelDefinition, FieldDefinition, RelationshipDefinition


class FieldDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldDefinition
        fields = '__all__'

class RelationshipDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelationshipDefinition
        fields = '__all__'

class ModelDefinitionSerializer(serializers.ModelSerializer):
    fielddefinition_set = FieldDefinitionSerializer(many=True, read_only=True)
    relationshipdefinition_set = RelationshipDefinitionSerializer(many=True, read_only=True)

    class Meta:
        model = ModelDefinition
        fields = '__all__'

class ApplicationSerializer(serializers.ModelSerializer):
    modeldefinition_set = ModelDefinitionSerializer(many=True, read_only=True)

    class Meta:
        model = ApplicationDefinition
        fields = '__all__'
