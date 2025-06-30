from django.apps import AppConfig


class ReportingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reporting'
    verbose_name = 'Dynamic Reporting System'

    def ready(self):
        """Initialize the app when Django starts."""
        # Import signal handlers
        # from . import signals  # noqa

        # Register any startup tasks
        self._register_permissions()

    def _register_permissions(self):
        """Register custom permissions."""
        # This ensures our custom permissions are available
        pass