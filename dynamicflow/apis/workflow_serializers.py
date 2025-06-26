from rest_framework import serializers
from dynamicflow.models import FieldType, Page, Category, Field, Condition


class WorkflowFieldTypeSerializer(serializers.ModelSerializer):
    """Field type serializer with consistent structure for workflow builder"""
    class Meta:
        model = FieldType
        fields = ['id', 'name', 'name_ara', 'code', 'active_ind']


class WorkflowPageSerializer(serializers.ModelSerializer):
    """Page serializer with explicit foreign key fields for workflow builder"""
    # Service fields
    service_id = serializers.IntegerField(source='service.id', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_code = serializers.CharField(source='service.code', read_only=True)

    # Sequence number fields
    sequence_number_id = serializers.IntegerField(source='sequence_number.id', read_only=True)
    sequence_number_name = serializers.CharField(source='sequence_number.name', read_only=True)
    sequence_number_code = serializers.CharField(source='sequence_number.code', read_only=True)

    # Applicant type fields
    applicant_type_id = serializers.IntegerField(source='applicant_type.id', read_only=True)
    applicant_type_name = serializers.CharField(source='applicant_type.name', read_only=True)
    applicant_type_code = serializers.CharField(source='applicant_type.code', read_only=True)

    class Meta:
        model = Page
        fields = [
            'id', 'name', 'name_ara', 'description', 'description_ara',
            'service', 'service_id', 'service_name', 'service_code',
            'sequence_number', 'sequence_number_id', 'sequence_number_name', 'sequence_number_code',
            'applicant_type', 'applicant_type_id', 'applicant_type_name', 'applicant_type_code',
            'active_ind'
        ]

    def to_representation(self, instance):
        """Ensure consistent null handling"""
        data = super().to_representation(instance)

        # Ensure foreign key fields are None instead of missing
        fk_fields = [
            'service_id', 'service_name', 'service_code',
            'sequence_number_id', 'sequence_number_name', 'sequence_number_code',
            'applicant_type_id', 'applicant_type_name', 'applicant_type_code'
        ]

        for field in fk_fields:
            if field not in data:
                data[field] = None

        return data


class WorkflowCategorySerializer(serializers.ModelSerializer):
    """Category serializer with pages info for workflow builder"""
    pages = serializers.SerializerMethodField()
    page_ids = serializers.PrimaryKeyRelatedField(
        source='page', many=True, queryset=Page.objects.all(), write_only=True
    )

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'name_ara', 'code', 'description',
            'is_repeatable', 'pages', 'page_ids', 'active_ind'
        ]

    def get_pages(self, obj):
        """Return page info with consistent structure"""
        return [{
            'id': page.id,
            'name': page.name,
            'code': page.sequence_number.code if page.sequence_number else None
        } for page in obj.page.all()]


class WorkflowFieldSerializer(serializers.ModelSerializer):
    """Field serializer with explicit foreign key fields for workflow builder"""
    # Field type fields
    field_type_id = serializers.IntegerField(source='_field_type.id', read_only=True)
    field_type_name = serializers.CharField(source='_field_type.name', read_only=True)
    field_type_code = serializers.CharField(source='_field_type.code', read_only=True)

    # Parent field fields
    parent_field_id = serializers.IntegerField(source='_parent_field.id', read_only=True)
    parent_field_name = serializers.CharField(source='_parent_field._field_name', read_only=True)

    # Lookup fields
    lookup_id = serializers.IntegerField(source='_lookup.id', read_only=True)
    lookup_name = serializers.CharField(source='_lookup.name', read_only=True)
    lookup_code = serializers.CharField(source='_lookup.code', read_only=True)

    # Related fields
    services = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    sub_fields = serializers.SerializerMethodField()

    class Meta:
        model = Field
        fields = [
            'id', '_field_name', '_field_display_name', '_field_display_name_ara',
            '_field_type', 'field_type_id', 'field_type_name', 'field_type_code',
            '_parent_field', 'parent_field_id', 'parent_field_name',
            '_lookup', 'lookup_id', 'lookup_name', 'lookup_code',
            '_sequence', '_mandatory', '_is_hidden', '_is_disabled',
            'services', 'categories', 'sub_fields',
            '_max_length', '_min_length', '_regex_pattern', '_allowed_characters',
            '_forbidden_words', '_value_greater_than', '_value_less_than',
            '_integer_only', '_positive_only', '_date_greater_than', '_date_less_than',
            '_future_only', '_past_only', '_default_boolean', '_file_types',
            '_max_file_size', '_image_max_width', '_image_max_height',
            '_max_selections', '_min_selections', '_precision', '_unique',
            '_default_value', '_coordinates_format', '_uuid_format',
            'active_ind'
        ]

    def get_services(self, obj):
        return [{
            'id': service.id,
            'name': service.name,
            'code': service.code
        } for service in obj.service.all()]

    def get_categories(self, obj):
        return [{
            'id': category.id,
            'name': category.name,
            'code': category.code
        } for category in obj._category.all()]

    def get_sub_fields(self, obj):
        # Return basic info to avoid deep nesting
        return [{
            'id': field.id,
            'name': field._field_name,
            'display_name': field._field_display_name,
            'field_type': field._field_type.name if field._field_type else None
        } for field in obj.sub_fields.filter(active_ind=True)]

    def to_representation(self, instance):
        """Ensure consistent null handling"""
        data = super().to_representation(instance)

        # Ensure foreign key fields are None instead of missing
        fk_fields = [
            'field_type_id', 'field_type_name', 'field_type_code',
            'parent_field_id', 'parent_field_name',
            'lookup_id', 'lookup_name', 'lookup_code'
        ]

        for field in fk_fields:
            if field not in data:
                data[field] = None

        return data


class WorkflowConditionSerializer(serializers.ModelSerializer):
    """Condition serializer with target field info for workflow builder"""
    target_field_id = serializers.IntegerField(source='target_field.id', read_only=True)
    target_field_name = serializers.CharField(source='target_field._field_name', read_only=True)
    target_field_display_name = serializers.CharField(source='target_field._field_display_name', read_only=True)

    class Meta:
        model = Condition
        fields = [
            'id', 'target_field', 'target_field_id', 'target_field_name',
            'target_field_display_name', 'condition_logic', 'active_ind'
        ]