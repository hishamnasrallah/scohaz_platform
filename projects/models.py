# File: projects/models.py

from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from authentication.models import CustomUser
from version.models import LocalVersion, Version
import re


class FlutterProject(models.Model):
    """Represents a Flutter project created by a user"""

    # Basic Information
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    package_name = models.CharField(
        max_length=255,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$',
                message='Package name must be in format: com.example.app'
            )
        ],
        help_text='e.g., com.yourcompany.appname'
    )

    # Relationships
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='flutter_projects')
    app_version = models.ForeignKey(Version, on_delete=models.SET_NULL, null=True, blank=True)
    supported_languages = models.ManyToManyField(LocalVersion, blank=True)
    default_language = models.CharField(max_length=10, default='en')

    # App Configuration
    app_icon = models.ImageField(upload_to='project_icons/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#2196F3')  # Hex color
    secondary_color = models.CharField(max_length=7, default='#03DAC6')

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.package_name})"

    def clean(self):
        # Ensure package name is lowercase
        if self.package_name:
            self.package_name = self.package_name.lower()

        # Validate package name format
        if self.package_name and not re.match(r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$', self.package_name):
            raise ValidationError('Invalid package name format')


class ComponentTemplate(models.Model):
    """Flutter widget templates available in the visual builder"""

    CATEGORY_CHOICES = [
        ('layout', 'Layout'),
        ('input', 'Input'),
        ('display', 'Display'),
        ('navigation', 'Navigation'),
        ('feedback', 'Feedback'),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    flutter_widget = models.CharField(max_length=100)  # e.g., 'Container', 'Text'
    icon = models.CharField(max_length=50, blank=True)  # Icon name for UI
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


class Screen(models.Model):
    """Represents a screen in a Flutter project"""

    project = models.ForeignKey(FlutterProject, on_delete=models.CASCADE, related_name='screens')
    name = models.CharField(max_length=100)
    route = models.CharField(max_length=100)  # e.g., '/home', '/profile'
    is_home = models.BooleanField(default=False)

    # UI Structure stored as JSON
    ui_structure = models.JSONField(default=dict, help_text="""
    Example structure:
    {
        "type": "container",
        "properties": {"color": "#FFFFFF"},
        "children": [
            {
                "type": "text",
                "properties": {"text": "Hello", "fontSize": 20}
            }
        ]
    }
    """)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['project', 'route']
        ordering = ['created_at']

    def __str__(self):
        return f"{self.project.name} - {self.name}"

    def save(self, *args, **kwargs):
        # Ensure only one home screen per project
        if self.is_home:
            Screen.objects.filter(
                project=self.project,
                is_home=True
            ).exclude(pk=self.pk).update(is_home=False)

        # Ensure at least one screen is home
        if not self.is_home and not Screen.objects.filter(
                project=self.project,
                is_home=True
        ).exclude(pk=self.pk).exists():
            self.is_home = True

        super().save(*args, **kwargs)

    def clean(self):
        # Validate route format
        if not self.route.startswith('/'):
            self.route = f'/{self.route}'

        # Validate ui_structure
        if not isinstance(self.ui_structure, dict):
            raise ValidationError('UI structure must be a dictionary')

        if 'type' not in self.ui_structure:
            raise ValidationError('UI structure must have a type')