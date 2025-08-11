from django.db import models
from django.core.exceptions import ValidationError


class ComponentTemplate(models.Model):
    """Simplified component template for visual builder"""

    CATEGORY_CHOICES = [
        ('layout', 'Layout'),
        ('input', 'Input'),
        ('display', 'Display'),
        ('navigation', 'Navigation'),
        ('feedback', 'Feedback'),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    flutter_widget = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True)
    description = models.TextField()

    # Default properties as JSON
    default_properties = models.JSONField(default=dict)

    # Widget constraints
    can_have_children = models.BooleanField(default=False)
    max_children = models.IntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.flutter_widget})"


class WidgetMapping(models.Model):
    """Maps UI types to Flutter widgets"""

    ui_type = models.CharField(max_length=50, unique=True)
    flutter_widget = models.CharField(max_length=100)

    properties_mapping = models.JSONField(default=dict, help_text="""
    Example: {"text": "child: Text('{{value}}')", "color": "color: {{value}}"}
    """)

    import_statements = models.TextField(blank=True, help_text="One import per line")
    code_template = models.TextField(blank=True, help_text="Complex widget code template")

    can_have_children = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ui_type']

    def __str__(self):
        return f"{self.ui_type} -> {self.flutter_widget}"

    def clean(self):
        if self.flutter_widget and not self.flutter_widget[0].isupper():
            raise ValidationError('Flutter widget must be in PascalCase')