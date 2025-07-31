from django.db import models
from django.conf import settings
from authentication.models import CustomUser
from version.models import Version, LocalVersion


class FlutterProject(models.Model):
    """Main project model for Flutter Visual Builder"""
    name = models.CharField(
        max_length=100,
        help_text="Project name shown in the builder"
    )
    package_name = models.CharField(
        max_length=255,
        help_text="Android package name (e.g., com.example.myapp)",
        unique=True
    )
    description = models.TextField(
        blank=True,
        help_text="Project description"
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='flutter_projects'
    )

    # Link to version for the generated app
    app_version = models.ForeignKey(
        Version,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flutter_projects',
        help_text="Version control for the generated Flutter app"
    )

    # Languages supported by this app
    supported_languages = models.ManyToManyField(
        LocalVersion,
        related_name='flutter_projects',
        help_text="Languages available in the generated app"
    )

    # Default language
    default_language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES if hasattr(settings, 'LANGUAGES') else [('en', 'English')],
        default='en',
        help_text="Default language for the app"
    )

    # Project configuration
    app_icon = models.ImageField(
        upload_to='project_icons/',
        null=True,
        blank=True,
        help_text="App icon for the generated Flutter app"
    )
    primary_color = models.CharField(
        max_length=7,
        default='#2196F3',
        help_text="Primary theme color (hex format)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.package_name})"


class Screen(models.Model):
    """Individual screens within a Flutter project"""
    project = models.ForeignKey(
        FlutterProject,
        on_delete=models.CASCADE,
        related_name='screens'
    )
    name = models.CharField(
        max_length=100,
        help_text="Screen name (e.g., HomeScreen, LoginScreen)"
    )
    route = models.CharField(
        max_length=255,
        help_text="Flutter route path (e.g., /home, /login)"
    )
    is_home = models.BooleanField(
        default=False,
        help_text="Set as the default home screen"
    )

    # UI structure storage
    ui_structure = models.JSONField(
        default=dict,
        help_text="JSON representation of the screen's widget tree"
    )

    # Screen settings
    has_app_bar = models.BooleanField(
        default=True,
        help_text="Whether this screen includes an app bar"
    )
    app_bar_title = models.CharField(
        max_length=100,
        blank=True,
        help_text="Title shown in the app bar"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['project', 'name']
        unique_together = [['project', 'route']]
        indexes = [
            models.Index(fields=['project', 'is_home']),
        ]

    def __str__(self):
        return f"{self.project.name} - {self.name}"

    def save(self, *args, **kwargs):
        # Ensure only one home screen per project
        if self.is_home:
            Screen.objects.filter(
                project=self.project,
                is_home=True
            ).exclude(pk=self.pk).update(is_home=False)
        super().save(*args, **kwargs)


class ComponentTemplate(models.Model):
    """Reusable component templates for the visual builder"""
    CATEGORY_CHOICES = [
        ('basic', 'Basic Components'),
        ('layout', 'Layout Components'),
        ('input', 'Input Components'),
        ('navigation', 'Navigation Components'),
        ('custom', 'Custom Components'),
    ]

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Component name shown in the builder palette"
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='basic',
        help_text="Component category for organization"
    )
    flutter_widget = models.CharField(
        max_length=100,
        help_text="Corresponding Flutter widget name (e.g., Container, Text)"
    )

    # Component configuration
    icon = models.CharField(
        max_length=50,
        default='widgets',
        help_text="Material icon name for the component"
    )
    description = models.TextField(
        blank=True,
        help_text="Description shown in the builder"
    )

    # Default properties for this component
    default_properties = models.JSONField(
        default=dict,
        help_text="Default property values for new instances"
    )

    # Allowed properties that can be edited
    editable_properties = models.JSONField(
        default=list,
        help_text="List of properties that can be edited in the builder"
    )

    # Whether this component can have children
    can_have_children = models.BooleanField(
        default=False,
        help_text="Whether this component can contain other components"
    )

    # Component constraints
    max_children = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of children (null for unlimited)"
    )
    allowed_child_types = models.JSONField(
        default=list,
        blank=True,
        help_text="List of component types allowed as children"
    )

    # Active flag
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this component is available in the builder"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
        ]

    def __str__(self):
        return f"{self.get_category_display()} - {self.name}"