from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from reporting.models import (
    Report, ReportDataSource, ReportField, ReportFilter,
    ReportJoin, ReportParameter, ReportExecution, ReportSchedule,
    SavedReportResult
)
from reporting.utils.model_inspector import DynamicModelInspector

User = get_user_model()


class ReportDataSourceSerializer(serializers.ModelSerializer):
    """Serializer for report data sources."""
    model_class_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ReportDataSource
        fields = [
            'id', 'report', 'app_name', 'model_name', 'alias',
            'is_primary', 'select_related', 'prefetch_related',
            'model_class_info'
        ]
        read_only_fields = ['id']

    def get_model_class_info(self, obj):
        """Get model metadata."""
        model_class = obj.get_model_class()
        if model_class:
            return {
                'verbose_name': str(model_class._meta.verbose_name),
                'verbose_name_plural': str(model_class._meta.verbose_name_plural),
                'db_table': model_class._meta.db_table,
            }
        return None

    def validate(self, attrs):
        """Validate that the model exists."""
        app_name = attrs.get('app_name')
        model_name = attrs.get('model_name')

        inspector = DynamicModelInspector()
        if not inspector.get_model_by_name(app_name, model_name):
            raise serializers.ValidationError(
                f"Model {app_name}.{model_name} does not exist"
            )

        return attrs


class ReportFieldSerializer(serializers.ModelSerializer):
    """Serializer for report fields."""
    class Meta:
        model = ReportField
        fields = [
            'id', 'report', 'data_source', 'field_name', 'field_path',
            'display_name', 'field_type', 'aggregation', 'order',
            'is_visible', 'width', 'formatting'
        ]
        read_only_fields = ['id', 'field_type']

    def validate_field_path(self, value):
        """Validate that the field path exists."""
        if self.instance:
            data_source = self.instance.data_source
        else:
            data_source_id = self.initial_data.get('data_source')
            if not data_source_id:
                return value
            try:
                data_source = ReportDataSource.objects.get(id=data_source_id)
            except ReportDataSource.DoesNotExist:
                return value

        model_class = data_source.get_model_class()
        if model_class:
            inspector = DynamicModelInspector()
            is_valid, result = inspector.validate_field_path(model_class, value)
            if not is_valid:
                raise serializers.ValidationError(result)

        return value


class ReportFilterSerializer(serializers.ModelSerializer):
    """Serializer for report filters."""
    class Meta:
        model = ReportFilter
        fields = [
            'id', 'report', 'data_source', 'field_name', 'field_path',
            'operator', 'value', 'value_type', 'logic_group',
            'group_order', 'parent_group', 'is_active', 'is_required'
        ]
        read_only_fields = ['id']


class ReportJoinSerializer(serializers.ModelSerializer):
    """Serializer for report joins."""
    left_source_display = serializers.CharField(source='left_source.alias', read_only=True)
    right_source_display = serializers.CharField(source='right_source.alias', read_only=True)

    class Meta:
        model = ReportJoin
        fields = [
            'id', 'report', 'left_source', 'right_source',
            'left_field', 'right_field', 'join_type',
            'additional_conditions', 'left_source_display', 'right_source_display'
        ]
        read_only_fields = ['id']


class ReportParameterSerializer(serializers.ModelSerializer):
    """Serializer for report parameters."""
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
        """Get dynamic choices if applicable."""
        if obj.parameter_type in ['select', 'multiselect']:
            if obj.choices_static:
                return obj.choices_static
            elif obj.choices_query:
                # Execute dynamic query
                # This is simplified - you'd want proper error handling
                try:
                    query_config = obj.choices_query
                    inspector = DynamicModelInspector()
                    model_class = inspector.get_model_by_name(
                        query_config['app'],
                        query_config['model']
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
                                'label': getattr(item, label_field),
                            })
                        return choices
                except Exception:
                    return []
        return None


class ReportSerializer(serializers.ModelSerializer):
    """Main report serializer."""
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
        """Check if current user can edit the report."""
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
        """Check if current user can execute the report."""
        request = self.context.get('request')
        if not request or not request.user:
            return False

        if obj.is_public:
            return True

        user = request.user
        return self.get_can_edit(obj) or user.has_perm('reporting.execute_report')

    def create(self, validated_data):
        """Create report with current user as creator."""
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
    """Serializer for report executions."""
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
    """Serializer for report schedules."""
    recipient_users = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), required=False
    )
    recipient_groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Group.objects.all(), required=False
    )
    all_recipient_emails = serializers.SerializerMethodField()

    class Meta:
        model = ReportSchedule
        fields = [
            'id', 'report', 'name', 'schedule_type', 'cron_expression',
            'time_of_day', 'day_of_week', 'day_of_month', 'timezone',
            'parameters', 'output_format', 'recipient_emails',
            'recipient_users', 'recipient_groups', 'email_subject',
            'email_body', 'include_in_body', 'is_active', 'last_run',
            'last_status', 'next_run', 'retry_on_failure', 'max_retries',
            'created_by', 'created_at', 'updated_at', 'all_recipient_emails'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at',
                            'last_run', 'last_status', 'next_run']

    def get_all_recipient_emails(self, obj):
        """Get all recipient emails."""
        return obj.get_recipient_emails()

    def create(self, validated_data):
        """Create schedule with current user as creator."""
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
    """Serializer for saved report results."""
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
        """Create saved result with current user."""
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
    """Lightweight serializer for report listings."""
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
        """Get last execution info."""
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
    """Serializer for model information from inspector."""
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
    """Serializer for app information from inspector."""
    label = serializers.CharField()
    verbose_name = serializers.CharField()
    is_custom = serializers.BooleanField()
    models = ModelInfoSerializer(many=True)


class ReportBuilderSerializer(serializers.Serializer):
    """Serializer for report builder data."""
    available_apps = serializers.DictField(child=AppInfoSerializer())
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


class ReportExecutionRequestSerializer(serializers.Serializer):
    """Serializer for report execution requests."""
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
    """Serializer for report preview."""
    query_sql = serializers.CharField()
    estimated_rows = serializers.IntegerField()
    preview_data = serializers.ListField()
    columns = serializers.ListField()
    warnings = serializers.ListField()