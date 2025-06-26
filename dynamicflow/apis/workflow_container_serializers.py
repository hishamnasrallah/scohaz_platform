# dynamicflow/apis/workflow_container_serializers.py

from rest_framework import serializers
from dynamicflow.models import Workflow, WorkflowConnection
from dynamicflow.apis.workflow_serializers import (
    WorkflowPageSerializer, WorkflowCategorySerializer,
    WorkflowFieldSerializer, WorkflowConditionSerializer
)


class WorkflowConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowConnection
        fields = ['id', 'workflow', 'source_type', 'source_id', 'target_type', 'target_id', 'connection_metadata']


class WorkflowSerializer(serializers.ModelSerializer):
    """Main workflow serializer"""
    pages = WorkflowPageSerializer(many=True, read_only=True)
    categories = WorkflowCategorySerializer(many=True, read_only=True)
    fields = WorkflowFieldSerializer(many=True, read_only=True)
    conditions = WorkflowConditionSerializer(many=True, read_only=True)
    connections = WorkflowConnectionSerializer(many=True, read_only=True)

    service_name = serializers.CharField(source='service.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'service', 'service_code', 'service_name',
            'is_active', 'is_draft', 'version', 'metadata', 'canvas_state',
            'pages', 'categories', 'fields', 'conditions', 'connections',
            'created_by', 'created_by_name', 'updated_by', 'updated_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']


class WorkflowListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing workflows"""
    service_name = serializers.CharField(source='service.name', read_only=True)
    element_count = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'service', 'service_code', 'service_name',
            'is_active', 'is_draft', 'version', 'element_count',
            'created_at', 'updated_at'
        ]

    def get_element_count(self, obj):
        return {
            'pages': obj.pages.count(),
            'categories': obj.categories.count(),
            'fields': obj.fields.count(),
            'conditions': obj.conditions.count()
        }