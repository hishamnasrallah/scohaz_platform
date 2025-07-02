from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType

from dynamicflow.models import FieldType
from reporting.models import (
    Report, ReportDataSource, ReportField, ReportFilter,
    ReportJoin, ReportParameter, ReportExecution, ReportSchedule,
    SavedReportResult
)
from reporting.utils.model_inspector import DynamicModelInspector

User = get_user_model()


class ContentTypeSerializer(serializers.ModelSerializer):
    """Serializer for ContentType with additional display info"""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model', 'display_name']

    def get_display_name(self, obj):
        model_class = obj.model_class()
        if model_class:
            return f"{obj.app_label} | {model_class._meta.verbose_name}"
        return f"{obj.app_label} | {obj.model}"


class ReportDataSourceSerializer(serializers.ModelSerializer):
    """Serializer for report data sources with ContentType support"""

    # For reading - backward compatibility
    app_name = serializers.CharField(source='content_type.app_label', read_only=True)
    model_name = serializers.CharField(source='content_type.model', read_only=True)

    # For writing - use content_type_id
    content_type_id = serializers.PrimaryKeyRelatedField(
        queryset=ContentType.objects.all(),
        source='content_type',
        write_only=True
    )

    # Additional info
    content_type = ContentTypeSerializer(read_only=True)
    model_info = serializers.SerializerMethodField()
    available_fields = serializers.SerializerMethodField()

    class Meta:
        model = ReportDataSource
        fields = [
            'id', 'report', 'content_type_id', 'content_type',
            'app_name', 'model_name', 'alias', 'is_primary',
            'select_related', 'prefetch_related', 'model_info',
            'available_fields'
        ]
        read_only_fields = ['id']

    def get_model_info(self, obj):
        """Get model metadata"""
        model_class = obj.get_model_class()
        if model_class:
            return {
                'verbose_name': str(model_class._meta.verbose_name),
                'verbose_name_plural': str(model_class._meta.verbose_name_plural),
                'db_table': model_class._meta.db_table,
                'field_count': len(model_class._meta.get_fields()),
            }
        return None

    def get_available_fields(self, obj):
        """Get available fields for the selected model"""
        if not obj.content_type:
            return []

        inspector = DynamicModelInspector()
        model_class = obj.get_model_class()
        if model_class:
            fields = []

            # Get direct fields
            for field in model_class._meta.get_fields():
                if not field.auto_created or field.concrete:
                    field_info = {
                        'name': field.name,
                        'verbose_name': str(field.verbose_name),
                        'type': field.get_internal_type(),
                        'is_relation': field.is_relation,
                        'path': field.name,
                    }
                    fields.append(field_info)

                    # Add related fields (one level deep)
                    if field.is_relation and not field.many_to_many:
                        related_model = field.related_model
                        for rel_field in related_model._meta.get_fields():
                            if not rel_field.auto_created or rel_field.concrete:
                                fields.append({
                                    'name': f"{field.name}__{rel_field.name}",
                                    'verbose_name': f"{field.verbose_name} → {rel_field.verbose_name}",
                                    'type': rel_field.get_internal_type(),
                                    'is_relation': False,
                                    'path': f"{field.name}__{rel_field.name}",
                                })

            return fields
        return []


class ReportFieldSerializer(serializers.ModelSerializer):
    """Serializer for report fields with dynamic field validation"""

    # Show available choices
    field_choices = serializers.SerializerMethodField()

    class Meta:
        model = ReportField
        fields = [
            'id', 'report', 'data_source', 'field_name', 'field_path',
            'display_name', 'field_type', 'aggregation', 'order',
            'is_visible', 'width', 'formatting', 'field_choices'
        ]
        read_only_fields = ['id']

    def get_field_choices(self, obj):
        """Get available field choices based on data source"""
        if hasattr(obj, 'data_source') and obj.data_source:
            # Use the available_fields from data source serializer
            ds_serializer = ReportDataSourceSerializer(obj.data_source)
            return ds_serializer.data['available_fields']
        return []

    def validate(self, attrs):
        """Validate field selection and auto-detect field type"""
        data_source = attrs.get('data_source') or (self.instance.data_source if self.instance else None)
        field_path = attrs.get('field_path') or (self.instance.field_path if self.instance else None)

        if data_source and field_path:
            model_class = data_source.get_model_class()
            if model_class:
                inspector = DynamicModelInspector()
                is_valid, result = inspector.validate_field_path(model_class, field_path)

                if is_valid:
                    # Auto-set field_type if not provided
                    if 'field_type' not in attrs or not attrs['field_type']:
                        attrs['field_type'] = result

                    # Auto-set field_name from last part of path
                    if 'field_name' not in attrs:
                        attrs['field_name'] = field_path.split('__')[-1]

                    # Auto-set display_name if not provided
                    if 'display_name' not in attrs:
                        # Try to get verbose name
                        parts = field_path.split('__')
                        current_model = model_class
                        display_parts = []

                        for part in parts:
                            try:
                                field = current_model._meta.get_field(part)
                                display_parts.append(str(field.verbose_name))
                                if field.is_relation:
                                    current_model = field.related_model
                            except:
                                display_parts.append(part.replace('_', ' ').title())

                        attrs['display_name'] = ' → '.join(display_parts)
                else:
                    raise serializers.ValidationError({
                        'field_path': f"Invalid field path: {result}"
                    })

        return attrs


class ReportFilterSerializer(serializers.ModelSerializer):
    """Serializer for report filters with field validation"""

    # Show available fields for filtering
    field_choices = serializers.SerializerMethodField()

    class Meta:
        model = ReportFilter
        fields = [
            'id', 'report', 'data_source', 'field_name', 'field_path',
            'operator', 'value', 'value_type', 'logic_group',
            'group_order', 'parent_group', 'is_active', 'is_required',
            'field_choices'
        ]
        read_only_fields = ['id']

    def get_field_choices(self, obj):
        """Get available field choices based on data source"""
        if hasattr(obj, 'data_source') and obj.data_source:
            ds_serializer = ReportDataSourceSerializer(obj.data_source)
            return ds_serializer.data['available_fields']
        return []

    def validate(self, attrs):
        """Validate field path exists on the model"""
        data_source = attrs.get('data_source') or (self.instance.data_source if self.instance else None)
        field_path = attrs.get('field_path') or (self.instance.field_path if self.instance else None)

        if data_source and field_path:
            model_class = data_source.get_model_class()
            if model_class:
                inspector = DynamicModelInspector()
                is_valid, result = inspector.validate_field_path(model_class, field_path)

                if is_valid:
                    # Auto-set field_name if not provided
                    if 'field_name' not in attrs:
                        attrs['field_name'] = field_path.split('__')[-1]
                else:
                    raise serializers.ValidationError({
                        'field_path': f"Invalid field path: {result}"
                    })

        return attrs


class ReportJoinSerializer(serializers.ModelSerializer):
    """Serializer for report joins"""
    left_source_display = serializers.CharField(source='left_source.alias', read_only=True)
    right_source_display = serializers.CharField(source='right_source.alias', read_only=True)

    # Available fields for join conditions
    left_fields = serializers.SerializerMethodField()
    right_fields = serializers.SerializerMethodField()

    class Meta:
        model = ReportJoin
        fields = [
            'id', 'report', 'left_source', 'right_source',
            'left_field', 'right_field', 'join_type',
            'additional_conditions', 'left_source_display',
            'right_source_display', 'left_fields', 'right_fields'
        ]
        read_only_fields = ['id']

    def get_left_fields(self, obj):
        """Get available fields from left source"""
        if hasattr(obj, 'left_source') and obj.left_source:
            ds_serializer = ReportDataSourceSerializer(obj.left_source)
            return ds_serializer.data['available_fields']
        return []

    def get_right_fields(self, obj):
        """Get available fields from right source"""
        if hasattr(obj, 'right_source') and obj.right_source:
            ds_serializer = ReportDataSourceSerializer(obj.right_source)
            return ds_serializer.data['available_fields']
        return []


class ReportParameterSerializer(serializers.ModelSerializer):
    """Serializer for report parameters"""
    choices = serializers.SerializerMethodField()

    class Meta:
        model = ReportParameter
        fields = [
            'id', 'report', 'name', 'display_name', 'parameter_type',
            'is_required', 'default_value', 'choices_static',
            'choices_query', 'validation_rules', 'help_text',
            'placeholder', 'order', 'choices'
        ]
        read_only_fields = ['id']

    def get_choices(self, obj):
        """Get dynamic choices if applicable"""
        if obj.parameter_type in ['select', 'multiselect']:
            if obj.choices_static:
                return obj.choices_static
            elif obj.choices_query:
                # Execute dynamic query
                try:
                    query_config = obj.choices_query

                    # Get model using ContentType if specified
                    if 'content_type_id' in query_config:
                        ct = ContentType.objects.get(id=query_config['content_type_id'])
                        model_class = ct.model_class()
                    else:
                        # Fallback to old method for backward compatibility
                        inspector = DynamicModelInspector()
                        model_class = inspector.get_model_by_name(
                            query_config.get('app', ''),
                            query_config.get('model', '')
                        )

                    if model_class:
                        queryset = model_class.objects.all()

                        if 'filter' in query_config:
                            queryset = queryset.filter(**query_config['filter'])
                        if 'order_by' in query_config:
                            queryset = queryset.order_by(query_config['order_by'])

                        value_field = query_config.get('value_field', 'id')
                        label_field = query_config.get('label_field', 'name')

                        choices = []
                        for item in queryset[:100]:  # Limit to 100 items
                            choices.append({
                                'value': getattr(item, value_field),
                                'label': str(getattr(item, label_field, item)),
                            })
                        return choices
                except Exception as e:
                    return [{'error': str(e)}]
        return None


class ReportSerializer(serializers.ModelSerializer):
    """Main report serializer"""
    data_sources = ReportDataSourceSerializer(many=True, read_only=True)
    fields = ReportFieldSerializer(many=True, read_only=True)
    filters = ReportFilterSerializer(many=True, read_only=True)
    joins = ReportJoinSerializer(many=True, read_only=True)
    parameters = ReportParameterSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    shared_with_users = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), required=False
    )
    shared_with_groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Group.objects.all(), required=False
    )
    can_edit = serializers.SerializerMethodField()
    can_execute = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'name', 'description', 'report_type', 'is_active',
            'is_public', 'tags', 'category', 'created_by', 'created_by_username',
            'shared_with_users', 'shared_with_groups', 'created_at',
            'updated_at', 'config', 'data_sources', 'fields', 'filters',
            'joins', 'parameters', 'can_edit', 'can_execute'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_can_edit(self, obj):
        """Check if current user can edit the report"""
        request = self.context.get('request')
        if not request or not request.user:
            return False

        user = request.user
        return (
                user.is_superuser or
                obj.created_by == user or
                user in obj.shared_with_users.all() or
                user.groups.filter(id__in=obj.shared_with_groups.all()).exists()
        )

    def get_can_execute(self, obj):
        """Check if current user can execute the report"""
        request = self.context.get('request')
        if not request or not request.user:
            return False

        if obj.is_public:
            return True

        user = request.user
        return self.get_can_edit(obj) or user.has_perm('reporting.execute_report')

    def create(self, validated_data):
        """Create report with current user as creator"""
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user

        shared_users = validated_data.pop('shared_with_users', [])
        shared_groups = validated_data.pop('shared_with_groups', [])

        report = Report.objects.create(**validated_data)

        if shared_users:
            report.shared_with_users.set(shared_users)
        if shared_groups:
            report.shared_with_groups.set(shared_groups)

        return report


class ReportExecutionSerializer(serializers.ModelSerializer):
    """Serializer for report executions"""
    report_name = serializers.CharField(source='report.name', read_only=True)
    executed_by_username = serializers.CharField(source='executed_by.username', read_only=True)

    class Meta:
        model = ReportExecution
        fields = [
            'id', 'report', 'report_name', 'executed_by', 'executed_by_username',
            'executed_at', 'parameters_used', 'execution_time', 'row_count',
            'status', 'error_message', 'query_count', 'peak_memory',
            'result_cache_key', 'cached_until', 'export_format', 'export_file_size'
        ]
        read_only_fields = fields  # All fields are read-only


class ReportScheduleSerializer(serializers.ModelSerializer):
    """Serializer for report schedules"""
    recipient_users = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), required=False
    )
    recipient_groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Group.objects.all(), required=False
    )
    all_recipient_emails = serializers.SerializerMethodField()

    # Timezone choices for frontend
    timezone_choices = serializers.SerializerMethodField()

    class Meta:
        model = ReportSchedule
        fields = [
            'id', 'report', 'name', 'schedule_type', 'cron_expression',
            'time_of_day', 'day_of_week', 'day_of_month', 'timezone',
            'parameters', 'output_format', 'recipient_emails',
            'recipient_users', 'recipient_groups', 'email_subject',
            'email_body', 'include_in_body', 'is_active', 'last_run',
            'last_status', 'next_run', 'retry_on_failure', 'max_retries',
            'created_by', 'created_at', 'updated_at', 'all_recipient_emails',
            'timezone_choices'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at',
                            'last_run', 'last_status', 'next_run']

    def get_all_recipient_emails(self, obj):
        """Get all recipient emails"""
        return obj.get_recipient_emails()

    def get_timezone_choices(self, obj):
        """Get available timezone choices"""
        # Return a simplified list for frontend
        import pytz
        return [{'value': tz, 'label': tz} for tz in pytz.common_timezones]

    def create(self, validated_data):
        """Create schedule with current user as creator"""
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user

        recipient_users = validated_data.pop('recipient_users', [])
        recipient_groups = validated_data.pop('recipient_groups', [])

        schedule = ReportSchedule.objects.create(**validated_data)

        if recipient_users:
            schedule.recipient_users.set(recipient_users)
        if recipient_groups:
            schedule.recipient_groups.set(recipient_groups)

        return schedule


class SavedReportResultSerializer(serializers.ModelSerializer):
    """Serializer for saved report results"""
    report_name = serializers.CharField(source='report.name', read_only=True)
    saved_by_username = serializers.CharField(source='saved_by.username', read_only=True)
    shared_with_users = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), required=False
    )
    shared_with_groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Group.objects.all(), required=False
    )

    class Meta:
        model = SavedReportResult
        fields = [
            'id', 'report', 'report_name', 'name', 'description',
            'execution', 'parameters_used', 'result_data', 'row_count',
            'saved_by', 'saved_by_username', 'saved_at', 'expires_at',
            'is_public', 'shared_with_users', 'shared_with_groups'
        ]
        read_only_fields = ['id', 'saved_by', 'saved_at']

    def create(self, validated_data):
        """Create saved result with current user"""
        request = self.context.get('request')
        if request and request.user:
            validated_data['saved_by'] = request.user

        shared_users = validated_data.pop('shared_with_users', [])
        shared_groups = validated_data.pop('shared_with_groups', [])

        saved_result = SavedReportResult.objects.create(**validated_data)

        if shared_users:
            saved_result.shared_with_users.set(shared_users)
        if shared_groups:
            saved_result.shared_with_groups.set(shared_groups)

        return saved_result


# Additional serializers for specific use cases

class ReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for report listings"""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    field_count = serializers.IntegerField(source='fields.count', read_only=True)
    last_execution = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'name', 'description', 'report_type', 'category',
            'is_active', 'is_public', 'created_by_username',
            'created_at', 'updated_at', 'field_count', 'last_execution'
        ]

    def get_last_execution(self, obj):
        """Get last execution info"""
        last_exec = obj.executions.order_by('-executed_at').first()
        if last_exec:
            return {
                'executed_at': last_exec.executed_at,
                'executed_by': last_exec.executed_by.username,
                'status': last_exec.status,
                'row_count': last_exec.row_count,
            }
        return None


class ModelInfoSerializer(serializers.Serializer):
    """Serializer for model information from inspector"""
    name = serializers.CharField()
    db_table = serializers.CharField()
    verbose_name = serializers.CharField()
    verbose_name_plural = serializers.CharField()
    fields = serializers.ListField()
    relationships = serializers.ListField()
    permissions = serializers.ListField()
    is_managed = serializers.BooleanField()
    ordering = serializers.ListField()
    indexes = serializers.ListField()


class AppInfoSerializer(serializers.Serializer):
    """Serializer for app information from inspector"""
    label = serializers.CharField()
    verbose_name = serializers.CharField()
    is_custom = serializers.BooleanField()
    models = ModelInfoSerializer(many=True)


class ReportBuilderSerializer(serializers.Serializer):
    """Serializer for report builder data"""
    available_content_types = ContentTypeSerializer(many=True)
    report = ReportSerializer(required=False)
    available_fields = serializers.ListField(required=False)
    available_filters = serializers.ListField(required=False)
    available_aggregations = serializers.ListField(
        default=['count', 'count_distinct', 'sum', 'avg', 'min', 'max', 'group_by']
    )
    available_operators = serializers.ListField(
        default=[
            'eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'not_in',
            'contains', 'icontains', 'startswith', 'endswith',
            'regex', 'isnull', 'isnotnull', 'between', 'date_range'
        ]
    )
    available_field_types = serializers.ListField()
    available_timezones = serializers.ListField()


class ReportExecutionRequestSerializer(serializers.Serializer):
    """Serializer for report execution requests"""
    parameters = serializers.DictField(required=False, default=dict)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=10000)
    offset = serializers.IntegerField(required=False, min_value=0)
    export_format = serializers.ChoiceField(
        choices=['json', 'csv', 'excel', 'pdf'],
        required=False,
        default='json'
    )
    save_result = serializers.BooleanField(default=False)
    result_name = serializers.CharField(required=False, max_length=255)
    result_description = serializers.CharField(required=False)


class ReportPreviewSerializer(serializers.Serializer):
    """Serializer for report preview"""
    query_sql = serializers.CharField()
    estimated_rows = serializers.IntegerField()
    preview_data = serializers.ListField()
    columns = serializers.ListField()
    warnings = serializers.ListField()



class ReportingFieldTypeSerializer(serializers.ModelSerializer):
    """Field type serializer with consistent structure for reporting builder"""
    class Meta:
        model = FieldType
        fields = ['id', 'name', 'name_ara', 'code', 'active_ind']

