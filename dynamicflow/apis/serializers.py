from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from dynamicflow.models import FieldType, Page, Category, Field, Condition

class FlowRetrieveIndustriesFlow(serializers.Serializer):

    class Meta:
        fields = ('sequence_number', 'name', 'name_ara',
                  'categories', 'multiple_industries_ind')


class FieldTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldType
        fields = '__all__'


class PageListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing pages"""
    service_name = serializers.CharField(source='service.name', read_only=True)
    sequence_number_name = serializers.CharField(source='sequence_number.name', read_only=True)
    applicant_type_name = serializers.CharField(source='applicant_type.name', read_only=True)

    class Meta:
        model = Page
        fields = [
            'id', 'name', 'name_ara', 'description', 'is_review_page', 'description_ara',
            'service_name', 'sequence_number_name', 'applicant_type_name',
            'active_ind'
        ]


class PageDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for page CRUD operations"""
    service_name = serializers.CharField(source='service.name', read_only=True)
    sequence_number_name = serializers.CharField(source='sequence_number.name', read_only=True)
    applicant_type_name = serializers.CharField(source='applicant_type.name', read_only=True)

    class Meta:
        model = Page
        fields = '__all__'


class CategoryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing categories"""
    page_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'name_ara', 'code', 'is_repeatable',
            'description', 'page_count', 'active_ind'
        ]

    def get_page_count(self, obj):
        return obj.page.count()


class CategoryDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for category CRUD operations"""
    pages = PageListSerializer(source='page', many=True, read_only=True)

    class Meta:
        model = Category
        fields = '__all__'


class FieldListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing fields"""
    field_type_name = serializers.CharField(source='_field_type.name', read_only=True)
    parent_field_name = serializers.CharField(source='_parent_field._field_name', read_only=True)
    service_names = serializers.SerializerMethodField()
    category_names = serializers.SerializerMethodField()
    sub_fields_count = serializers.SerializerMethodField()

    class Meta:
        model = Field
        fields = [
            'id', '_field_name', '_field_display_name', '_field_display_name_ara',
            'field_type_name', 'parent_field_name', '_sequence', '_mandatory',
            '_is_hidden', '_is_disabled', 'service_names', 'category_names',
            'sub_fields_count', 'active_ind'
        ]

    def get_service_names(self, obj):
        return [service.name for service in obj.service.all()]

    def get_category_names(self, obj):
        return [category.name for category in obj._category.all()]

    def get_sub_fields_count(self, obj):
        return obj.sub_fields.count()


class FieldDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for field CRUD operations"""
    field_type_name = serializers.CharField(source='_field_type.name', read_only=True)
    parent_field_name = serializers.CharField(source='_parent_field._field_name', read_only=True)
    lookup_name = serializers.CharField(source='_lookup.name', read_only=True)
    service_names = serializers.SerializerMethodField()
    category_names = serializers.SerializerMethodField()
    sub_fields = serializers.SerializerMethodField()
    allowed_lookup_names = serializers.SerializerMethodField()
    ancestor_ids = serializers.SerializerMethodField()
    descendant_ids = serializers.SerializerMethodField()

    class Meta:
        model = Field
        fields = '__all__'

    def get_service_names(self, obj):
        return [service.name for service in obj.service.all()]

    def get_category_names(self, obj):
        return [category.name for category in obj._category.all()]

    def get_sub_fields(self, obj):
        return obj.serialize_sub_fields()

    def get_allowed_lookup_names(self, obj):
        return [lookup.name for lookup in obj.allowed_lookups.all()]

    def get_ancestor_ids(self, obj):
        if obj.pk:
            return obj.get_ancestor_ids()
        return []

    def get_descendant_ids(self, obj):
        if obj.pk:
            return list(obj.get_descendant_ids())
        return []

    def validate(self, data):
        """Custom validation to handle model's clean method"""
        # Create a temporary instance for validation
        instance = Field(**data)
        if self.instance:
            instance.pk = self.instance.pk
            instance.id = self.instance.id

        try:
            instance.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict)

        return data


class ConditionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing conditions"""
    target_field_name = serializers.CharField(source='target_field._field_name', read_only=True)
    condition_summary = serializers.SerializerMethodField()

    class Meta:
        model = Condition
        fields = [
            'id', 'target_field_name', 'condition_summary', 'active_ind'
        ]

    def get_condition_summary(self, obj):
        """Provide a human-readable summary of the condition logic"""
        if not obj.condition_logic:
            return "No conditions defined"

        try:
            logic = obj.condition_logic
            if isinstance(logic, list) and logic:
                first_condition = logic[0]
                field_name = first_condition.get('field', 'Unknown')
                operation = first_condition.get('operation', 'Unknown')
                value = first_condition.get('value', 'Unknown')

                summary = f"{field_name} {operation} {value}"
                if len(logic) > 1:
                    summary += f" (and {len(logic) - 1} more conditions)"

                return summary
        except (TypeError, KeyError, IndexError):
            pass

        return "Complex condition logic"


class ConditionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for condition CRUD operations"""
    target_field_name = serializers.CharField(source='target_field._field_name', read_only=True)
    target_field_display_name = serializers.CharField(source='target_field._field_display_name', read_only=True)

    class Meta:
        model = Condition
        fields = '__all__'

    def validate_condition_logic(self, value):
        """Validate the condition logic JSON structure"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Condition logic must be a list of conditions")

        required_keys = ['field', 'operation', 'value']
        valid_operations = [
            '+', '-', '*', '/', '**', '=', '!=', '>', '<', '>=', '<=',
            'in', 'not in', 'startswith', 'endswith', 'contains', 'matches',
            'and', 'or', 'not', 'sum'
        ]

        for i, condition in enumerate(value):
            if not isinstance(condition, dict):
                raise serializers.ValidationError(f"Condition {i} must be a dictionary")

            for key in required_keys:
                if key not in condition:
                    raise serializers.ValidationError(f"Condition {i} missing required key: {key}")

            operation = condition.get('operation')
            if operation not in valid_operations:
                raise serializers.ValidationError(
                    f"Invalid operation '{operation}' in condition {i}. "
                    f"Valid operations: {', '.join(valid_operations)}"
                )

        return value


# Nested serializers for complex operations
class FieldWithSubFieldsSerializer(serializers.ModelSerializer):
    """Serializer that includes nested sub-fields"""
    sub_fields = serializers.SerializerMethodField()
    field_type_name = serializers.CharField(source='_field_type.name', read_only=True)

    class Meta:
        model = Field
        fields = [
            'id', '_field_name', '_field_display_name', '_field_display_name_ara',
            '_sequence', '_mandatory', '_is_hidden', '_is_disabled',
            'field_type_name', 'sub_fields'
        ]

    def get_sub_fields(self, obj):
        sub_fields = obj.sub_fields.filter(active_ind=True).order_by('_sequence')
        return FieldWithSubFieldsSerializer(sub_fields, many=True, context=self.context).data


class PageWithFieldsSerializer(serializers.ModelSerializer):
    """Serializer that includes all fields for a page"""
    categories = serializers.SerializerMethodField()
    all_fields = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            'id', 'name', 'name_ara', 'is_review_page', 'description', 'description_ara',
            'categories', 'all_fields'
        ]

    def get_categories(self, obj):
        categories = obj.category_set.filter(active_ind=True)
        return CategoryListSerializer(categories, many=True, context=self.context).data

    def get_all_fields(self, obj):
        # Get all fields associated with this page through categories
        fields = Field.objects.filter(
            _category__page=obj,
            active_ind=True,
            _parent_field__isnull=True  # Only root fields
        ).distinct().order_by('_sequence')

        return FieldWithSubFieldsSerializer(fields, many=True, context=self.context).data


# Bulk operation serializers
class BulkFieldUpdateSerializer(serializers.Serializer):
    """Serializer for bulk field operations"""
    field_ids = serializers.ListField(child=serializers.IntegerField())
    action = serializers.ChoiceField(choices=['activate', 'deactivate', 'hide', 'show'])

    def validate_field_ids(self, value):
        if not value:
            raise serializers.ValidationError("Field IDs list cannot be empty")

        # Check if all field IDs exist
        existing_ids = set(Field.objects.filter(id__in=value).values_list('id', flat=True))
        provided_ids = set(value)

        if existing_ids != provided_ids:
            missing_ids = provided_ids - existing_ids
            raise serializers.ValidationError(f"Fields with IDs {list(missing_ids)} do not exist")

        return value