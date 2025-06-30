from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.apps import apps
import json

User = get_user_model()


class Report(models.Model):
    """Main report definition"""
    REPORT_TYPE_CHOICES = [
        ('ad_hoc', 'Ad Hoc Report'),
        ('template', 'Report Template'),
        ('dashboard', 'Dashboard Widget'),
        ('scheduled', 'Scheduled Report')
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPE_CHOICES, default='ad_hoc')
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False)

    # Metadata
    tags = models.JSONField(default=list, blank=True)
    category = models.CharField(max_length=100, blank=True)

    # Permissions
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_reports')
    shared_with_users = models.ManyToManyField(User, blank=True, related_name='shared_reports')
    shared_with_groups = models.ManyToManyField('auth.Group', blank=True, related_name='shared_reports')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Configuration
    config = models.JSONField(default=dict, blank=True)  # Additional configuration

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("execute_report", "Can execute report"),
            ("export_report", "Can export report"),
            ("share_report", "Can share report"),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        # Validate that at least one data source exists
        if self.pk and not self.data_sources.filter(is_primary=True).exists():
            raise ValidationError("Report must have at least one primary data source")


class ReportDataSource(models.Model):
    """Links reports to specific models/apps"""
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='data_sources')
    app_name = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    alias = models.CharField(max_length=50)  # For JOIN references (e.g., 'customer', 'order')
    is_primary = models.BooleanField(default=False)

    # Additional options
    select_related = models.JSONField(default=list, blank=True)  # Fields to select_related
    prefetch_related = models.JSONField(default=list, blank=True)  # Fields to prefetch_related

    class Meta:
        unique_together = [['report', 'alias']]
        ordering = ['-is_primary', 'alias']

    def __str__(self):
        return f"{self.app_name}.{self.model_name} as {self.alias}"

    def get_model_class(self):
        """Get the actual Django model class"""
        try:
            return apps.get_model(self.app_name, self.model_name)
        except LookupError:
            return None

    def clean(self):
        # Validate model exists
        if not self.get_model_class():
            raise ValidationError(f"Model {self.app_name}.{self.model_name} does not exist")

        # Ensure only one primary source per report
        if self.is_primary:
            existing_primary = ReportDataSource.objects.filter(
                report=self.report, is_primary=True
            ).exclude(pk=self.pk)
            if existing_primary.exists():
                raise ValidationError("Report can only have one primary data source")


class ReportField(models.Model):
    """Selected fields for the report"""
    AGGREGATION_CHOICES = [
        ('', 'None'),
        ('count', 'Count'),
        ('count_distinct', 'Count Distinct'),
        ('sum', 'Sum'),
        ('avg', 'Average'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
        ('group_by', 'Group By'),
    ]

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='fields')
    data_source = models.ForeignKey(ReportDataSource, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=100)
    field_path = models.CharField(max_length=255)  # For nested fields (e.g., 'customer__name')
    display_name = models.CharField(max_length=255)
    field_type = models.CharField(max_length=50)  # Store Django field type

    # Display options
    aggregation = models.CharField(max_length=20, blank=True, choices=AGGREGATION_CHOICES)
    order = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    width = models.IntegerField(null=True, blank=True)  # Column width in pixels

    # Formatting
    formatting = models.JSONField(default=dict, blank=True)
    # Example: {"type": "currency", "prefix": "$", "decimals": 2}
    # or: {"type": "date", "format": "YYYY-MM-DD"}

    class Meta:
        ordering = ['order', 'id']
        unique_together = [['report', 'data_source', 'field_path']]

    def __str__(self):
        return f"{self.display_name} ({self.field_path})"


class ReportFilter(models.Model):
    """Filter conditions for reports"""
    OPERATOR_CHOICES = [
        ('eq', 'Equals'),
        ('ne', 'Not Equals'),
        ('gt', 'Greater Than'),
        ('gte', 'Greater Than or Equal'),
        ('lt', 'Less Than'),
        ('lte', 'Less Than or Equal'),
        ('in', 'In List'),
        ('not_in', 'Not In List'),
        ('contains', 'Contains'),
        ('icontains', 'Contains (Case Insensitive)'),
        ('startswith', 'Starts With'),
        ('endswith', 'Ends With'),
        ('regex', 'Regex Match'),
        ('isnull', 'Is Null'),
        ('isnotnull', 'Is Not Null'),
        ('between', 'Between'),
        ('date_range', 'Date Range'),
    ]

    VALUE_TYPE_CHOICES = [
        ('static', 'Static Value'),
        ('parameter', 'Parameter'),
        ('dynamic', 'Dynamic (Computed)'),
        ('user_attribute', 'User Attribute'),
    ]

    LOGIC_CHOICES = [
        ('AND', 'AND'),
        ('OR', 'OR'),
    ]

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='filters')
    data_source = models.ForeignKey(ReportDataSource, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=100)
    field_path = models.CharField(max_length=255)
    operator = models.CharField(max_length=20, choices=OPERATOR_CHOICES)
    value = models.JSONField(null=True, blank=True)  # Flexible value storage
    value_type = models.CharField(max_length=20, choices=VALUE_TYPE_CHOICES, default='static')

    # Grouping
    logic_group = models.CharField(max_length=10, choices=LOGIC_CHOICES, default='AND')
    group_order = models.IntegerField(default=0)  # For complex grouping
    parent_group = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)

    # Options
    is_active = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False)  # For parameter-based filters

    class Meta:
        ordering = ['group_order', 'id']

    def __str__(self):
        return f"{self.field_path} {self.operator} {self.value}"


class ReportJoin(models.Model):
    """Define relationships between data sources"""
    JOIN_TYPE_CHOICES = [
        ('inner', 'Inner Join'),
        ('left', 'Left Join'),
        ('right', 'Right Join'),
        ('outer', 'Full Outer Join'),
    ]

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='joins')
    left_source = models.ForeignKey(ReportDataSource, on_delete=models.CASCADE, related_name='left_joins')
    right_source = models.ForeignKey(ReportDataSource, on_delete=models.CASCADE, related_name='right_joins')
    left_field = models.CharField(max_length=100)
    right_field = models.CharField(max_length=100)
    join_type = models.CharField(max_length=20, choices=JOIN_TYPE_CHOICES, default='inner')

    # Additional join conditions
    additional_conditions = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = [['report', 'left_source', 'right_source']]

    def __str__(self):
        return f"{self.left_source.alias}.{self.left_field} {self.join_type} {self.right_source.alias}.{self.right_field}"


class ReportParameter(models.Model):
    """Dynamic parameters for reports"""
    PARAMETER_TYPE_CHOICES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('datetime', 'DateTime'),
        ('date_range', 'Date Range'),
        ('select', 'Select List'),
        ('multiselect', 'Multi Select'),
        ('boolean', 'Yes/No'),
        ('user', 'User Selection'),
    ]

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='parameters')
    name = models.CharField(max_length=50)  # Internal name (e.g., 'start_date')
    display_name = models.CharField(max_length=100)  # Display name (e.g., 'Start Date')
    parameter_type = models.CharField(max_length=20, choices=PARAMETER_TYPE_CHOICES)
    is_required = models.BooleanField(default=False)
    default_value = models.JSONField(null=True, blank=True)

    # For select/multiselect
    choices_static = models.JSONField(null=True, blank=True)  # Static list of choices
    choices_query = models.JSONField(null=True, blank=True)  # Dynamic query for choices
    # Example: {"app": "crm", "model": "Customer", "value_field": "id", "label_field": "name"}

    # Validation
    validation_rules = models.JSONField(default=dict, blank=True)
    # Example: {"min": 0, "max": 100} for numbers
    # or: {"min_date": "2020-01-01"} for dates

    # UI hints
    help_text = models.TextField(blank=True)
    placeholder = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        unique_together = [['report', 'name']]

    def __str__(self):
        return f"{self.display_name} ({self.name})"


class ReportExecution(models.Model):
    """Track report executions for auditing and performance monitoring"""
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('error', 'Error'),
        ('timeout', 'Timeout'),
        ('cancelled', 'Cancelled'),
    ]

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='executions')
    executed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    executed_at = models.DateTimeField(auto_now_add=True)

    # Execution details
    parameters_used = models.JSONField(default=dict)
    execution_time = models.FloatField()  # in seconds
    row_count = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error_message = models.TextField(blank=True)

    # Performance metrics
    query_count = models.IntegerField(default=0)
    peak_memory = models.BigIntegerField(null=True, blank=True)  # in bytes

    # Caching
    result_cache_key = models.CharField(max_length=255, blank=True)
    cached_until = models.DateTimeField(null=True, blank=True)

    # Export info
    export_format = models.CharField(max_length=20, blank=True)
    export_file_size = models.BigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['report', '-executed_at']),
            models.Index(fields=['executed_by', '-executed_at']),
        ]

    def __str__(self):
        return f"{self.report.name} - {self.executed_at}"


class ReportSchedule(models.Model):
    """Schedule reports for automatic execution"""
    SCHEDULE_TYPE_CHOICES = [
        ('once', 'One Time'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('cron', 'Custom Cron'),
    ]

    OUTPUT_FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
        ('json', 'JSON'),
        ('html', 'HTML Email'),
    ]

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='schedules')
    name = models.CharField(max_length=255)
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPE_CHOICES)

    # Schedule configuration
    cron_expression = models.CharField(max_length=100, blank=True)
    time_of_day = models.TimeField(null=True, blank=True)  # For daily schedules
    day_of_week = models.IntegerField(null=True, blank=True)  # 0-6 for weekly
    day_of_month = models.IntegerField(null=True, blank=True)  # 1-31 for monthly
    timezone = models.CharField(max_length=50, default='UTC')

    # Execution settings
    parameters = models.JSONField(default=dict)  # Default parameters for execution
    output_format = models.CharField(max_length=20, choices=OUTPUT_FORMAT_CHOICES, default='excel')

    # Recipients
    recipient_emails = models.JSONField(default=list)  # List of emails
    recipient_users = models.ManyToManyField(User, blank=True)
    recipient_groups = models.ManyToManyField('auth.Group', blank=True)

    # Email settings
    email_subject = models.CharField(max_length=255, blank=True)
    email_body = models.TextField(blank=True)
    include_in_body = models.BooleanField(default=False)  # Include report in email body

    # Status
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=20, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    retry_on_failure = models.BooleanField(default=True)
    max_retries = models.IntegerField(default=3)

    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.get_schedule_type_display()}"

    def get_recipient_emails(self):
        """Get all recipient emails including from users and groups"""
        emails = set(self.recipient_emails)

        # Add user emails
        for user in self.recipient_users.all():
            if user.email:
                emails.add(user.email)

        # Add group member emails
        for group in self.recipient_groups.all():
            for user in group.user_set.all():
                if user.email:
                    emails.add(user.email)

        return list(emails)


class SavedReportResult(models.Model):
    """Store saved report results for quick access"""
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='saved_results')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Execution info
    execution = models.ForeignKey(ReportExecution, on_delete=models.SET_NULL, null=True)
    parameters_used = models.JSONField(default=dict)

    # Result storage
    result_data = models.JSONField()  # Actual data
    row_count = models.IntegerField()

    # Metadata
    saved_by = models.ForeignKey(User, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Sharing
    is_public = models.BooleanField(default=False)
    shared_with_users = models.ManyToManyField(User, blank=True, related_name='shared_saved_reports')
    shared_with_groups = models.ManyToManyField('auth.Group', blank=True, related_name='shared_saved_reports')

    class Meta:
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.name} - {self.report.name}"