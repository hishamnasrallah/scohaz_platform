# reporting_templates/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class PDFTemplate(models.Model):
    """Simple PDF template model"""
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True)

    # Page setup
    page_size = models.CharField(
        max_length=20,
        choices=[('A4', 'A4'), ('letter', 'Letter')],
        default='A4'
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


class PDFElement(models.Model):
    """Simple PDF element - just text"""
    template = models.ForeignKey(
        PDFTemplate,
        on_delete=models.CASCADE,
        related_name='elements'
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

    # Basic styling
    font_size = models.IntegerField(default=12)

    class Meta:
        ordering = ['y_position', 'x_position']

    def __str__(self):
        return f"{self.template.name} - Element at ({self.x_position}, {self.y_position})"