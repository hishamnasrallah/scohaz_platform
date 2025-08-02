# File: builder/models.py

from django.db import models
from django.core.exceptions import ValidationError


class WidgetMapping(models.Model):
    """Maps visual builder UI types to Flutter widgets"""

    # UI type used in visual builder
    ui_type = models.CharField(max_length=50, unique=True)  # e.g., 'button', 'text'

    # Corresponding Flutter widget
    flutter_widget = models.CharField(max_length=100)  # e.g., 'ElevatedButton', 'Text'

    # Property mappings (UI property -> Flutter property)
    properties_mapping = models.JSONField(default=dict, help_text="""
    Example:
    {
        "text": "child: Text('{{value}}')",
        "color": "color: Color(0xFF{{value.replace('#', '')}})",
        "onPressed": "onPressed: {{value}}"
    }
    """)

    # Required imports for this widget
    import_statements = models.TextField(blank=True, help_text="""
    One import per line, e.g.:
    import 'package:flutter/material.dart';
    """)

    # Code template for complex widgets
    code_template = models.TextField(blank=True, help_text="""
    Use {{property_name}} for property values.
    Example: {{flutter_widget}}({{properties}})
    """)

    # Widget constraints
    can_have_children = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ui_type']

    def __str__(self):
        return f"{self.ui_type} -> {self.flutter_widget}"

    def clean(self):
        # Validate flutter_widget is PascalCase
        if self.flutter_widget and not self.flutter_widget[0].isupper():
            raise ValidationError('Flutter widget must be in PascalCase')