from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from authentication.models import CustomUser
from version.models import LocalVersion, Version
import re


class FlutterProject(models.Model):
    """Simplified Flutter project model"""

    # Basic Information
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
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
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='simple_flutter_projects')
    app_version = models.ForeignKey(Version, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='simple_flutter_projects')
    supported_languages = models.ManyToManyField(LocalVersion, blank=True,
                                                 related_name='simple_flutter_projects')
    default_language = models.CharField(max_length=10, default='en')

    # App Configuration
    app_icon = models.ImageField(upload_to='project_icons/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#2196F3')
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
        if self.package_name:
            self.package_name = self.package_name.lower()
            if not re.match(r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$', self.package_name):
                raise ValidationError('Invalid package name format')


class Screen(models.Model):
    """Simplified screen model"""

    project = models.ForeignKey(FlutterProject, on_delete=models.CASCADE, related_name='screens')
    name = models.CharField(max_length=100)
    route = models.CharField(max_length=100)
    is_home = models.BooleanField(default=False)

    # UI Structure stored as JSON
    ui_structure = models.JSONField(default=dict, help_text="""
    JSON structure: {"type": "container", "properties": {}, "children": []}
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
        if not self.route.startswith('/'):
            self.route = f'/{self.route}'

        if not isinstance(self.ui_structure, dict):
            raise ValidationError('UI structure must be a dictionary')

        if self.ui_structure and 'type' not in self.ui_structure:
            raise ValidationError('UI structure must have a type field')