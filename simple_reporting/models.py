# reporting_templates/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()



class PDFTemplate(models.Model):
    """Simple PDF template model"""
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True)

    # Page setup
    page_size = models.CharField(
        max_length=20,
        choices=[
            ('A4', 'A4'),
            ('letter', 'Letter'),
            ('A3', 'A3'),
            ('A5', 'A5'),
            ('legal', 'Legal'),
            ('custom', 'Custom Size'),
            ('ratio_16_9', '16:9 Ratio'),
            ('ratio_4_3', '4:3 Ratio'),
            ('ratio_3_2', '3:2 Ratio'),
            ('ratio_1_1', '1:1 Square')
        ],
        default='A4'
    )

    page_orientation = models.CharField(
        max_length=10,
        choices=[
            ('portrait', 'Portrait'),
            ('landscape', 'Landscape')
        ],
        default='portrait'
    )

    # Custom dimensions (in pixels, will be converted to points)
    custom_width = models.IntegerField(
        null=True,
        blank=True,
        help_text='Custom width in pixels (only for custom size)'
    )
    custom_height = models.IntegerField(
        null=True,
        blank=True,
        help_text='Custom height in pixels (only for custom size)'
    )

    # For ratio-based sizes
    ratio_base_width = models.IntegerField(
        default=1920,
        help_text='Base width in pixels for ratio calculations'
    )

    # Data source - only model based
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='reporting_templates_pdfs',
        help_text='Model to get data from'
    )

    # Simple query filter as JSON
    query_filter = models.JSONField(
        default=dict,
        blank=True,
        help_text='Filter conditions like {"status": "active"}'
    )

    # Background settings
    background_type = models.CharField(
        max_length=20,
        choices=[
            ('none', 'No Background'),
            ('color', 'Solid Color'),
            ('image', 'Image'),
            ('pdf', 'PDF Template')
        ],
        default='none'
    )
    background_color = models.CharField(
        max_length=7,  # For hex colors like #FFFFFF
        blank=True,
        null=True,
        help_text='Hex color code (e.g., #FFFFFF)'
    )
    background_image = models.ImageField(
        upload_to='pdf_backgrounds/',
        blank=True,
        null=True,
        help_text='Background image (JPG, PNG)'
    )
    background_pdf = models.FileField(
        upload_to='pdf_templates/',
        blank=True,
        null=True,
        help_text='PDF file to use as background template'
    )
    background_opacity = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text='Background opacity (0.0 to 1.0)'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reporting_template_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_page_dimensions(self):
        """Get actual page dimensions in points based on settings"""
        from reportlab.lib.pagesizes import A4, A3, A5, letter, legal

        # Standard page sizes (in points)
        standard_sizes = {
            'A4': A4,
            'A3': A3,
            'A5': A5,
            'letter': letter,
            'legal': legal
        }

        # Calculate dimensions
        if self.page_size == 'custom':
            # Convert pixels to points (1 pixel = 0.75 points)
            width = (self.custom_width or 794) * 0.75
            height = (self.custom_height or 1123) * 0.75
        elif self.page_size.startswith('ratio_'):
            # Calculate height based on ratio
            ratios = {
                'ratio_16_9': (16, 9),
                'ratio_4_3': (4, 3),
                'ratio_3_2': (3, 2),
                'ratio_1_1': (1, 1)
            }
            ratio_w, ratio_h = ratios.get(self.page_size, (16, 9))
            width = self.ratio_base_width * 0.75
            height = (self.ratio_base_width * ratio_h / ratio_w) * 0.75
        else:
            # Standard sizes
            width, height = standard_sizes.get(self.page_size, A4)

        # Apply orientation
        if self.page_orientation == 'landscape':
            width, height = height, width

        return width, height
class PDFElement(models.Model):
    """PDF element - text or image"""
    ELEMENT_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
    ]

    template = models.ForeignKey(
        PDFTemplate,
        on_delete=models.CASCADE,
        related_name='elements'
    )

    element_type = models.CharField(
        max_length=10,
        choices=ELEMENT_TYPES,
        default='text'
    )

    # Position
    x_position = models.FloatField(help_text='X coordinate in points')
    y_position = models.FloatField(help_text='Y coordinate in points')

    # Content - either static text or field path
    text_content = models.TextField(
        blank=True,
        help_text='Static text or field path like "name" or "user.email"'
    )
    is_dynamic = models.BooleanField(
        default=False,
        help_text='If true, text_content is a field path'
    )

    # Basic styling for text
    font_size = models.IntegerField(default=12)

    # Image-specific fields
    image_field_path = models.CharField(
        max_length=255,
        blank=True,
        help_text='Path to image field, e.g., "case_data[uploaded_files]"'
    )
    image_filter_type = models.CharField(
        max_length=100,
        blank=True,
        help_text='Filter images by type, e.g., "Personal Image"'
    )
    image_selection_method = models.CharField(
        max_length=20,
        choices=[
            ('first', 'First Match'),
            ('last', 'Last Match'),
            ('filename', 'By Filename Contains'),
            ('all', 'All Matching (creates multiple)')
        ],
        default='first',
        help_text='How to select image when multiple match the filter'
    )

    image_filename_contains = models.CharField(
        max_length=100,
        blank=True,
        help_text='Select image whose filename contains this text (for filename method)'
    )

    # Optional: for even more control
    image_additional_filters = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional filters as JSON, e.g., {"size": "large", "format": "png"}'
    )
    image_width = models.FloatField(
        null=True,
        blank=True,
        help_text='Image width in points (leave empty for auto)'
    )
    image_height = models.FloatField(
        null=True,
        blank=True,
        help_text='Image height in points (leave empty for auto)'
    )
    image_maintain_aspect = models.BooleanField(
        default=True,
        help_text='Maintain aspect ratio when resizing'
    )

    class Meta:
        ordering = ['y_position', 'x_position']

    def __str__(self):
        element_info = f"{self.element_type} at ({self.x_position}, {self.y_position})"
        return f"{self.template.name} - {element_info}"