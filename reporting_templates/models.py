# reporting_templates/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import json

User = get_user_model()


class PDFTemplate(models.Model):
    """
    Main template model that stores PDF template configurations
    """
    ORIENTATION_CHOICES = [
        ('portrait', 'Portrait'),
        ('landscape', 'Landscape'),
    ]

    PAGE_SIZE_CHOICES = [
        ('A4', 'A4'),
        ('A3', 'A3'),
        ('letter', 'Letter'),
        ('legal', 'Legal'),
    ]

    DATA_SOURCE_TYPE_CHOICES = [
        ('model', 'Model Query'),
        ('raw_sql', 'Raw SQL'),
        ('custom_function', 'Custom Function'),
        ('api', 'External API'),
    ]

    # Basic Information
    name = models.CharField(max_length=200, unique=True)
    name_ara = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True)
    description_ara = models.TextField(blank=True, null=True)
    code = models.CharField(max_length=50, unique=True)

    # Language Configuration
    primary_language = models.CharField(
        max_length=2,
        choices=[('en', 'English'), ('ar', 'Arabic')],
        default='en'
    )
    supports_bilingual = models.BooleanField(default=False)

    # Page Configuration
    page_size = models.CharField(
        max_length=20,
        choices=PAGE_SIZE_CHOICES,
        default='A4'
    )
    orientation = models.CharField(
        max_length=20,
        choices=ORIENTATION_CHOICES,
        default='portrait'
    )
    margin_top = models.FloatField(default=72)  # points (1 inch)
    margin_bottom = models.FloatField(default=72)
    margin_left = models.FloatField(default=72)
    margin_right = models.FloatField(default=72)

    # Template Configuration
    header_enabled = models.BooleanField(default=True)
    footer_enabled = models.BooleanField(default=True)
    watermark_enabled = models.BooleanField(default=False)
    watermark_text = models.CharField(max_length=100, blank=True)

    # Data Source Configuration
    data_source_type = models.CharField(
        max_length=20,
        choices=DATA_SOURCE_TYPE_CHOICES,
        default='model'
    )

    # Model-based data source
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Primary model this template queries data from'
    )

    # Query configuration
    query_filter = models.JSONField(
        default=dict,
        blank=True,
        help_text='Default filter conditions for queries'
    )

    # Custom function path
    custom_function_path = models.CharField(
        max_length=255,
        blank=True,
        help_text='Python path to custom data fetching function'
    )

    # Raw SQL query
    raw_sql_query = models.TextField(
        blank=True,
        help_text='Raw SQL query for data fetching'
    )

    # Permissions & Ownership
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_pdf_templates'
    )
    groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        help_text='Groups that can use this template'
    )

    # Access Control
    requires_parameters = models.BooleanField(
        default=False,
        help_text='Whether this template requires parameters to generate'
    )
    allow_self_generation = models.BooleanField(
        default=True,
        help_text='Whether users can generate reports about themselves'
    )
    allow_other_generation = models.BooleanField(
        default=False,
        help_text='Whether users can generate reports about others'
    )

    # Related models configuration
    related_models = models.JSONField(
        default=dict,
        blank=True,
        help_text='Configuration for fetching related model data'
    )

    # Metadata
    is_system_template = models.BooleanField(
        default=False,
        help_text='System templates cannot be deleted by users'
    )
    active_ind = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ('can_design_template', 'Can design PDF templates'),
            ('can_generate_pdf', 'Can generate PDFs from templates'),
            ('can_generate_others_pdf', 'Can generate PDFs for other users'),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_display_name(self, language='en'):
        """Get display name based on language"""
        if language == 'ar' and self.name_ara:
            return self.name_ara
        return self.name


class PDFTemplateParameter(models.Model):
    """
    Define parameters that can be passed to templates
    """
    PARAMETER_TYPE_CHOICES = [
        ('integer', 'Integer'),
        ('string', 'String'),
        ('date', 'Date'),
        ('datetime', 'DateTime'),
        ('boolean', 'Boolean'),
        ('float', 'Float'),
        ('uuid', 'UUID'),
        ('model_id', 'Model ID'),
        ('user_id', 'User ID'),
    ]

    WIDGET_TYPE_CHOICES = [
        ('text', 'Text Input'),
        ('number', 'Number Input'),
        ('date', 'Date Picker'),
        ('datetime', 'DateTime Picker'),
        ('select', 'Dropdown'),
        ('radio', 'Radio Buttons'),
        ('checkbox', 'Checkbox'),
        ('user_search', 'User Search'),
        ('model_search', 'Model Search'),
    ]

    template = models.ForeignKey(
        PDFTemplate,
        on_delete=models.CASCADE,
        related_name='parameters'
    )

    # Parameter definition
    parameter_key = models.CharField(
        max_length=50,
        help_text='Key used in queries and templates'
    )
    display_name = models.CharField(max_length=100)
    display_name_ara = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    description_ara = models.TextField(blank=True)

    # Parameter configuration
    parameter_type = models.CharField(
        max_length=20,
        choices=PARAMETER_TYPE_CHOICES
    )
    is_required = models.BooleanField(default=True)
    default_value = models.CharField(max_length=255, blank=True)

    # UI Configuration
    widget_type = models.CharField(
        max_length=20,
        choices=WIDGET_TYPE_CHOICES,
        default='text'
    )
    widget_config = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional widget configuration (choices, min/max, etc.)'
    )

    # Validation
    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text='Validation rules for the parameter'
    )

    # Query usage
    query_field = models.CharField(
        max_length=100,
        help_text='Field name in database query'
    )
    query_operator = models.CharField(
        max_length=20,
        default='exact',
        help_text='Query operator (exact, icontains, gte, etc.)'
    )

    # Security
    allow_user_override = models.BooleanField(
        default=True,
        help_text='Whether users can override this parameter'
    )
    restricted_to_groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        help_text='Only these groups can use this parameter'
    )

    # Order
    order = models.IntegerField(default=0)

    # Metadata
    active_ind = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'parameter_key']
        unique_together = [['template', 'parameter_key']]

    def __str__(self):
        return f"{self.template.name} - {self.parameter_key}"


class PDFTemplateDataSource(models.Model):
    """
    Define additional data sources for templates
    """
    DATA_FETCH_METHOD_CHOICES = [
        ('model_query', 'Model Query'),
        ('raw_sql', 'Raw SQL'),
        ('custom_function', 'Custom Function'),
        ('related_field', 'Related Field'),
        ('prefetch', 'Prefetch Related'),
    ]

    template = models.ForeignKey(
        PDFTemplate,
        on_delete=models.CASCADE,
        related_name='data_sources'
    )

    # Data source identification
    source_key = models.CharField(
        max_length=50,
        help_text='Key to access this data in template'
    )
    display_name = models.CharField(max_length=100)

    # Data fetching configuration
    fetch_method = models.CharField(
        max_length=20,
        choices=DATA_FETCH_METHOD_CHOICES
    )

    # Model-based configuration
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    query_path = models.CharField(
        max_length=255,
        blank=True,
        help_text='Path for related fields (e.g., user__profile__address)'
    )

    # Query configuration
    filter_config = models.JSONField(
        default=dict,
        blank=True,
        help_text='Filter configuration using parameters'
    )

    # Custom function
    custom_function_path = models.CharField(
        max_length=255,
        blank=True
    )

    # Raw SQL
    raw_sql = models.TextField(blank=True)

    # Data processing
    post_process_function = models.CharField(
        max_length=255,
        blank=True,
        help_text='Function to process fetched data'
    )

    # Caching
    cache_timeout = models.IntegerField(
        default=0,
        help_text='Cache timeout in seconds (0 = no cache)'
    )

    # Order
    order = models.IntegerField(default=0)

    # Metadata
    active_ind = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'source_key']
        unique_together = [['template', 'source_key']]

    def __str__(self):
        return f"{self.template.name} - {self.source_key}"


class PDFTemplateElement(models.Model):
    """
    Individual elements within a PDF template
    """
    ELEMENT_TYPE_CHOICES = [
        ('text', 'Text'),
        ('dynamic_text', 'Dynamic Text'),
        ('image', 'Image'),
        ('dynamic_image', 'Dynamic Image'),
        ('line', 'Line'),
        ('rectangle', 'Rectangle'),
        ('circle', 'Circle'),
        ('table', 'Table'),
        ('chart', 'Chart'),
        ('barcode', 'Barcode'),
        ('qrcode', 'QR Code'),
        ('signature', 'Signature Field'),
        ('page_break', 'Page Break'),
        ('loop', 'Loop Container'),
        ('conditional', 'Conditional Container'),
    ]

    FONT_FAMILY_CHOICES = [
        ('Helvetica', 'Helvetica'),
        ('Times-Roman', 'Times Roman'),
        ('Courier', 'Courier'),
        ('Arabic', 'Arabic Font'),
        ('Arabic-Bold', 'Arabic Bold'),
    ]

    TEXT_ALIGN_CHOICES = [
        ('left', 'Left'),
        ('center', 'Center'),
        ('right', 'Right'),
        ('justify', 'Justify'),
    ]

    # Basic Information
    template = models.ForeignKey(
        PDFTemplate,
        on_delete=models.CASCADE,
        related_name='elements'
    )
    element_type = models.CharField(
        max_length=20,
        choices=ELEMENT_TYPE_CHOICES
    )
    element_key = models.CharField(
        max_length=100,
        help_text='Unique identifier for this element in the template'
    )

    # Position & Size
    x_position = models.FloatField(help_text='X coordinate in points')
    y_position = models.FloatField(help_text='Y coordinate in points from top')
    width = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    rotation = models.FloatField(default=0, help_text='Rotation in degrees')

    # Text Properties
    text_content = models.TextField(
        blank=True,
        help_text='Static text or template variable like {{user.name}}'
    )
    text_content_ara = models.TextField(
        blank=True,
        help_text='Arabic version of text content'
    )
    font_family = models.CharField(
        max_length=50,
        choices=FONT_FAMILY_CHOICES,
        default='Helvetica'
    )
    font_size = models.IntegerField(default=12)
    font_color = models.CharField(
        max_length=7,
        default='#000000',
        help_text='Hex color code'
    )
    is_bold = models.BooleanField(default=False)
    is_italic = models.BooleanField(default=False)
    is_underline = models.BooleanField(default=False)
    text_align = models.CharField(
        max_length=10,
        choices=TEXT_ALIGN_CHOICES,
        default='left'
    )
    line_height = models.FloatField(default=1.2)

    # Shape Properties
    fill_color = models.CharField(
        max_length=7,
        blank=True,
        help_text='Fill color for shapes'
    )
    stroke_color = models.CharField(
        max_length=7,
        default='#000000',
        help_text='Border color'
    )
    stroke_width = models.FloatField(default=1)

    # Image Properties
    image_source = models.CharField(
        max_length=500,
        blank=True,
        help_text='URL or field reference for images'
    )
    maintain_aspect_ratio = models.BooleanField(default=True)

    # Table Properties
    table_config = models.JSONField(
        default=dict,
        blank=True,
        help_text='Table configuration including columns, headers, etc.'
    )

    # Loop Configuration
    loop_config = models.JSONField(
        default=dict,
        blank=True,
        help_text='Configuration for loop elements'
    )

    # Dynamic Properties
    data_source = models.CharField(
        max_length=200,
        blank=True,
        help_text='Data source key or path to get dynamic data'
    )
    condition = models.CharField(
        max_length=500,
        blank=True,
        help_text='Condition for showing this element'
    )

    # Parent-Child Relationship
    parent_element = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_elements'
    )

    # Metadata
    z_index = models.IntegerField(
        default=0,
        help_text='Layer order (higher values on top)'
    )
    is_repeatable = models.BooleanField(
        default=False,
        help_text='For elements that repeat on every page'
    )
    page_number = models.IntegerField(
        null=True,
        blank=True,
        help_text='Specific page number (null for all pages)'
    )
    active_ind = models.BooleanField(default=True)

    class Meta:
        ordering = ['template', 'page_number', 'z_index', 'y_position']
        unique_together = [['template', 'element_key']]

    def __str__(self):
        return f"{self.template.name} - {self.element_key} ({self.element_type})"


class PDFTemplateVariable(models.Model):
    """
    Define available variables for templates
    """
    DATA_TYPE_CHOICES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('datetime', 'DateTime'),
        ('boolean', 'Boolean'),
        ('image', 'Image'),
        ('list', 'List'),
        ('dict', 'Dictionary'),
        ('model', 'Model Instance'),
    ]

    template = models.ForeignKey(
        PDFTemplate,
        on_delete=models.CASCADE,
        related_name='variables'
    )
    variable_key = models.CharField(
        max_length=100,
        help_text='Variable name used in template like user_name'
    )
    display_name = models.CharField(max_length=200)
    display_name_ara = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    data_type = models.CharField(
        max_length=20,
        choices=DATA_TYPE_CHOICES,
        default='text'
    )
    data_source = models.CharField(
        max_length=200,
        help_text='Source key and path like main.user.profile.full_name'
    )
    default_value = models.CharField(max_length=500, blank=True)
    format_string = models.CharField(
        max_length=100,
        blank=True,
        help_text='Python format string like %Y-%m-%d for dates'
    )

    # Processing
    transform_function = models.CharField(
        max_length=255,
        blank=True,
        help_text='Function to transform the value'
    )

    is_required = models.BooleanField(default=False)

    class Meta:
        unique_together = [['template', 'variable_key']]

    def __str__(self):
        return f"{self.template.name} - {self.variable_key}"


class PDFGenerationLog(models.Model):
    """
    Log of all PDF generation activities
    """
    template = models.ForeignKey(
        PDFTemplate,
        on_delete=models.CASCADE,
        related_name='generation_logs'
    )
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    generated_for = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pdfs_generated_for'
    )

    # Context Information
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Generation Details
    parameters = models.JSONField(
        default=dict,
        help_text='Parameters used for generation'
    )
    context_data = models.JSONField(
        default=dict,
        help_text='Full context data used for generation'
    )
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.IntegerField(null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    error_message = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    generation_time = models.FloatField(
        null=True,
        blank=True,
        help_text='Time taken in seconds'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['generated_by', 'created_at']),
            models.Index(fields=['template', 'status']),
        ]

    def __str__(self):
        return f"{self.template.name} - {self.created_at} - {self.status}"