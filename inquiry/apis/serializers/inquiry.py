from rest_framework import serializers
from inquiry.models import (
    InquiryConfiguration, InquiryField, InquiryRelation,
    InquiryFilter, InquirySort, InquiryPermission,
    InquiryExecution, InquiryTemplate
)

class InquiryFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = InquiryField
        fields = '__all__'

class InquiryRelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InquiryRelation
        fields = '__all__'

class InquiryFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = InquiryFilter
        fields = '__all__'

class InquirySortSerializer(serializers.ModelSerializer):
    class Meta:
        model = InquirySort
        fields = '__all__'

class InquiryPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InquiryPermission
        fields = '__all__'

class InquiryConfigurationSerializer(serializers.ModelSerializer):
    fields = InquiryFieldSerializer(many=True, read_only=True)
    relations = InquiryRelationSerializer(many=True, read_only=True)
    filters = InquiryFilterSerializer(many=True, read_only=True)
    sorts = InquirySortSerializer(many=True, read_only=True)
    permissions = InquiryPermissionSerializer(many=True, read_only=True)

    class Meta:
        model = InquiryConfiguration
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by']

class InquiryExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InquiryExecution
        fields = '__all__'

class InquiryTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InquiryTemplate
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by']