from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group
from django.conf import settings

class InquiryConfiguration(models.Model):
    """Main configuration for an inquiry"""
    name = models.CharField(max_length=200)
    code = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    # Target model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    # Display configuration
    display_name = models.CharField(max_length=200)
    icon = models.CharField(max_length=50, blank=True)

    # Permissions
    allowed_groups = models.ManyToManyField(Group, blank=True)
    is_public = models.BooleanField(default=False)

    # Query configuration
    default_page_size = models.IntegerField(default=20)
    max_page_size = models.IntegerField(default=100)
    allow_export = models.BooleanField(default=True)
    export_formats = models.JSONField(default=list, blank=True)  # ['csv', 'excel', 'json']

    # Advanced query options
    distinct = models.BooleanField(default=False)
    enable_search = models.BooleanField(default=True)
    search_fields = models.JSONField(default=list, blank=True)  # Global search fields

    # Status
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_inquiries'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Inquiry Configuration'
        verbose_name_plural = 'Inquiry Configurations'

    def __str__(self):
        return f"{self.name} ({self.code})"


class InquiryField(models.Model):
    """Fields to include in inquiry results"""
    inquiry = models.ForeignKey(
        InquiryConfiguration,
        related_name='fields',
        on_delete=models.CASCADE
    )

    # Field configuration
    field_path = models.CharField(max_length=500)  # e.g., "user__profile__name"
    display_name = models.CharField(max_length=200)
    field_type = models.CharField(max_length=50)  # string, number, date, boolean, etc.

    # Display options
    is_visible = models.BooleanField(default=True)
    is_searchable = models.BooleanField(default=False)
    is_sortable = models.BooleanField(default=False)
    is_filterable = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)  # Primary display field

    # Formatting
    format_template = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Python format string, e.g., '{value:%Y-%m-%d}' for dates"
    )
    transform_function = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Dotted path to transform function"
    )

    # Aggregation options
    aggregation = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ('count', 'Count'),
            ('sum', 'Sum'),
            ('avg', 'Average'),
            ('min', 'Minimum'),
            ('max', 'Maximum'),
        ]
    )

    # Order and display
    order = models.IntegerField(default=0)
    width = models.CharField(max_length=20, blank=True, null=True)  # e.g., "150px", "20%"
    alignment = models.CharField(
        max_length=10,
        choices=[('left', 'Left'), ('center', 'Center'), ('right', 'Right')],
        default='left'
    )

    # JSON field specific options
    json_extract_path = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="For JSON fields, path to extract value"
    )

    class Meta:
        ordering = ['order', 'id']
        unique_together = ['inquiry', 'field_path']

    def __str__(self):
        return f"{self.inquiry.code} - {self.display_name}"


class InquiryRelation(models.Model):
    """Related models to include"""
    inquiry = models.ForeignKey(
        InquiryConfiguration,
        related_name='relations',
        on_delete=models.CASCADE
    )

    relation_path = models.CharField(max_length=500)  # e.g., "user__profile"
    display_name = models.CharField(max_length=200)
    relation_type = models.CharField(
        max_length=20,
        choices=[
            ('one_to_one', 'One to One'),
            ('foreign_key', 'Foreign Key'),
            ('one_to_many', 'One to Many'),
            ('many_to_many', 'Many to Many'),
        ]
    )

    # Include options
    include_fields = models.JSONField(default=list)  # List of fields to include
    exclude_fields = models.JSONField(default=list)  # List of fields to exclude

    # Query optimization
    use_select_related = models.BooleanField(default=True)
    use_prefetch_related = models.BooleanField(default=False)

    # Nested configuration
    max_depth = models.IntegerField(default=1)
    include_count = models.BooleanField(default=False)

    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ['inquiry', 'relation_path']

    def __str__(self):
        return f"{self.inquiry.code} -> {self.relation_path}"


class InquiryFilter(models.Model):
    """Pre-configured filters"""
    inquiry = models.ForeignKey(
        InquiryConfiguration,
        related_name='filters',
        on_delete=models.CASCADE
    )

    name = models.CharField(max_length=200)
    code = models.SlugField()
    field_path = models.CharField(max_length=500)
    operator = models.CharField(
        max_length=50,
        choices=[
            ('exact', 'Equals'),
            ('iexact', 'Equals (case-insensitive)'),
            ('contains', 'Contains'),
            ('icontains', 'Contains (case-insensitive)'),
            ('gt', 'Greater than'),
            ('gte', 'Greater than or equal'),
            ('lt', 'Less than'),
            ('lte', 'Less than or equal'),
            ('in', 'In list'),
            ('range', 'Between'),
            ('isnull', 'Is null'),
            ('isnotnull', 'Is not null'),
            ('startswith', 'Starts with'),
            ('endswith', 'Ends with'),
            ('regex', 'Regular expression'),
        ]
    )

    # Filter configuration
    filter_type = models.CharField(
        max_length=50,
        choices=[
            ('text', 'Text input'),
            ('number', 'Number input'),
            ('date', 'Date picker'),
            ('datetime', 'DateTime picker'),
            ('select', 'Dropdown'),
            ('multiselect', 'Multi-select'),
            ('checkbox', 'Checkbox'),
            ('radio', 'Radio buttons'),
            ('daterange', 'Date range'),
            ('lookup', 'Lookup reference'),
        ]
    )

    # Default and validation
    default_value = models.JSONField(null=True, blank=True)
    is_required = models.BooleanField(default=False)
    validation_rules = models.JSONField(default=dict, blank=True)

    # For select/multiselect filters
    lookup_category = models.CharField(max_length=100, blank=True)
    choices_json = models.JSONField(default=list, blank=True)
    choices_function = models.CharField(
        max_length=200,
        blank=True,
        help_text="Dotted path to function returning choices"
    )

    # UI options
    placeholder = models.CharField(max_length=200, blank=True)
    help_text = models.TextField(blank=True)
    is_visible = models.BooleanField(default=True)
    is_advanced = models.BooleanField(default=False)

    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ['inquiry', 'code']

    def __str__(self):
        return f"{self.inquiry.code} - {self.name}"


class InquirySort(models.Model):
    """Default sorting configuration"""
    inquiry = models.ForeignKey(
        InquiryConfiguration,
        related_name='sorts',
        on_delete=models.CASCADE
    )

    field_path = models.CharField(max_length=500)
    direction = models.CharField(
        max_length=4,
        choices=[('asc', 'Ascending'), ('desc', 'Descending')]
    )
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.inquiry.code} - {self.field_path} {self.direction}"


class InquiryPermission(models.Model):
    """Fine-grained permissions for inquiries"""
    inquiry = models.ForeignKey(
        InquiryConfiguration,
        related_name='permissions',
        on_delete=models.CASCADE
    )

    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    # Basic permissions
    can_view = models.BooleanField(default=True)
    can_export = models.BooleanField(default=False)
    can_view_all = models.BooleanField(
        default=False,
        help_text="Can view all records, not just owned"
    )

    # Row-level permissions
    row_permission_function = models.CharField(
        max_length=200,
        blank=True,
        help_text="Function to determine row-level access"
    )

    # Field-level permissions
    visible_fields = models.JSONField(default=list, blank=True)
    hidden_fields = models.JSONField(default=list, blank=True)

    # Export limitations
    max_export_rows = models.IntegerField(null=True, blank=True)
    allowed_export_formats = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ['inquiry', 'group']

    def __str__(self):
        return f"{self.inquiry.code} - {self.group.name}"


class InquiryExecution(models.Model):
    """Log inquiry executions"""
    inquiry = models.ForeignKey(InquiryConfiguration, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    executed_at = models.DateTimeField(auto_now_add=True)
    filters_applied = models.JSONField(default=dict)
    sort_applied = models.JSONField(default=list)
    search_query = models.CharField(max_length=500, blank=True)

    # Results
    result_count = models.IntegerField(default=0)
    page_size = models.IntegerField(null=True)
    page_number = models.IntegerField(null=True)

    # Performance
    execution_time_ms = models.IntegerField(default=0)
    query_count = models.IntegerField(default=0)

    # Export info
    export_format = models.CharField(max_length=10, blank=True)
    export_fields = models.JSONField(default=list, blank=True)

    # Status
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    # Request info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['inquiry', 'executed_at']),
            models.Index(fields=['user', 'executed_at']),
        ]

    def __str__(self):
        return f"{self.inquiry.code} - {self.user} - {self.executed_at}"


class InquiryTemplate(models.Model):
    """Saved inquiry templates with pre-configured filters"""
    name = models.CharField(max_length=200)
    code = models.SlugField(unique=True)
    inquiry = models.ForeignKey(InquiryConfiguration, on_delete=models.CASCADE)

    # Saved configuration
    filters = models.JSONField(default=dict)
    sorts = models.JSONField(default=list)
    selected_fields = models.JSONField(default=list)

    # Ownership
    is_public = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inquiry_templates'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.inquiry.code})"