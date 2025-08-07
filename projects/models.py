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


class CanvasState(models.Model):
    """Stores canvas state for each screen including history"""

    screen = models.OneToOneField(
        Screen,
        on_delete=models.CASCADE,
        related_name='canvas_state'
    )

    # Selection and UI state
    selected_widget_ids = models.JSONField(default=list)
    expanded_tree_nodes = models.JSONField(default=list)

    # Undo/Redo history
    history_stack = models.JSONField(
        default=list,
        help_text="Stack of previous UI structures for undo"
    )
    history_index = models.IntegerField(default=-1)
    max_history_size = models.IntegerField(default=50)

    # Drag state (for recovery)
    last_drag_state = models.JSONField(
        default=dict,
        help_text="Last drag operation for recovery"
    )

    # View settings
    zoom_level = models.IntegerField(default=100)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['screen']),
        ]

    def push_history(self, ui_structure):
        """Add current state to history for undo"""
        # Remove any history after current index
        self.history_stack = self.history_stack[:self.history_index + 1]

        # Add new state
        self.history_stack.append(ui_structure)

        # Limit history size
        if len(self.history_stack) > self.max_history_size:
            self.history_stack.pop(0)
        else:
            self.history_index += 1

        self.save()

    def undo(self):
        """Get previous state from history"""
        if self.history_index > 0:
            self.history_index -= 1
            self.save()
            return self.history_stack[self.history_index]
        return None

    def redo(self):
        """Get next state from history"""
        if self.history_index < len(self.history_stack) - 1:
            self.history_index += 1
            self.save()
            return self.history_stack[self.history_index]
        return None


class ProjectAsset(models.Model):
    """Assets (images, fonts, etc.) for a project"""

    ASSET_TYPES = [
        ('image', 'Image'),
        ('font', 'Font'),
        ('icon', 'Icon'),
        ('other', 'Other')
    ]

    project = models.ForeignKey(
        FlutterProject,
        on_delete=models.CASCADE,
        related_name='assets'
    )
    name = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    file = models.FileField(upload_to='project_assets/')
    url = models.URLField(blank=True)  # For CDN/external assets
    metadata = models.JSONField(default=dict)  # Size, format, etc.

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['project', 'name']
        indexes = [
            models.Index(fields=['project', 'asset_type']),
        ]

    def __str__(self):
        return f"{self.project.name} - {self.name}"


class WidgetTemplate(models.Model):
    """Reusable widget templates/presets"""

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='widget_templates'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50)

    # The widget structure
    structure = models.JSONField()

    # Thumbnail for visual preview
    thumbnail = models.ImageField(
        upload_to='template_thumbnails/',
        blank=True,
        null=True
    )

    is_public = models.BooleanField(default=False)
    tags = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'category']),
            models.Index(fields=['is_public']),
        ]


class StylePreset(models.Model):
    """Reusable style presets"""

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='style_presets'
    )
    name = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=50)
    properties = models.JSONField()

    is_public = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'name', 'widget_type']