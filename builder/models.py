from django.db import models
from projects.models import ComponentTemplate


class WidgetMapping(models.Model):
    """Maps visual builder components to Flutter widget code templates"""
    component = models.OneToOneField(
        ComponentTemplate,
        on_delete=models.CASCADE,
        related_name='widget_mapping',
        help_text="The component template this mapping is for"
    )

    # Flutter code template using Jinja2 syntax
    code_template = models.TextField(
        help_text="Jinja2 template for generating Flutter widget code"
    )

    # Import statements required for this widget
    required_imports = models.JSONField(
        default=list,
        help_text="List of Flutter import statements needed"
    )

    # Property mappings
    property_mappings = models.JSONField(
        default=dict,
        help_text="Maps builder properties to Flutter widget properties"
    )

    # Code generation hints
    wrap_in_widget = models.CharField(
        max_length=100,
        blank=True,
        help_text="Wrap generated widget in another widget (e.g., 'Expanded')"
    )
    requires_context = models.BooleanField(
        default=False,
        help_text="Whether this widget requires BuildContext"
    )

    # Version compatibility
    min_flutter_version = models.CharField(
        max_length=20,
        default='3.0.0',
        help_text="Minimum Flutter SDK version required"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['component__category', 'component__name']

    def __str__(self):
        return f"Mapping for {self.component.name}"


class GenerationConfig(models.Model):
    """Configuration settings for Flutter code generation"""
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Configuration name"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this configuration"
    )

    # Flutter project settings
    flutter_version = models.CharField(
        max_length=20,
        default='3.0.0',
        help_text="Target Flutter SDK version"
    )
    dart_version = models.CharField(
        max_length=20,
        default='3.0.0',
        help_text="Target Dart SDK version"
    )

    # Build settings
    enable_null_safety = models.BooleanField(
        default=True,
        help_text="Enable Dart null safety"
    )
    enable_material3 = models.BooleanField(
        default=True,
        help_text="Use Material Design 3"
    )

    # Code generation options
    use_const_constructors = models.BooleanField(
        default=True,
        help_text="Use const constructors where possible"
    )
    generate_comments = models.BooleanField(
        default=True,
        help_text="Include explanatory comments in generated code"
    )

    # Localization settings
    generate_localization = models.BooleanField(
        default=True,
        help_text="Generate localization files from translations"
    )
    localization_package = models.CharField(
        max_length=100,
        default='flutter_localizations',
        help_text="Localization package to use"
    )

    # Package dependencies
    default_packages = models.JSONField(
        default=dict,
        help_text="Default packages to include in pubspec.yaml"
    )

    # Template settings
    main_template = models.TextField(
        blank=True,
        help_text="Override template for main.dart file"
    )
    pubspec_template = models.TextField(
        blank=True,
        help_text="Override template for pubspec.yaml file"
    )

    # Active flag
    is_default = models.BooleanField(
        default=False,
        help_text="Use as default configuration"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this configuration is available"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'name']

    def __str__(self):
        return f"{self.name} {'(Default)' if self.is_default else ''}"

    def save(self, *args, **kwargs):
        # Ensure only one default configuration
        if self.is_default:
            GenerationConfig.objects.filter(
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)