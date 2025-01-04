from django.apps import AppConfig
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class DynamicModelsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dynamic_models'

    def ready(self):
        """
        Load signal handlers and set SQLite PRAGMA settings for better performance and reliability.
        """
        from dynamic_models.signals import (
            handle_dynamic_model_save,
            handle_dynamic_model_delete,
            handle_dynamic_field_save,
        )
        set_sqlite_pragmas()

        logger.info("DynamicModelsConfig initialized. Ready to manage dynamic models and fields.")


def set_sqlite_pragmas():
    """
    Set SQLite-specific PRAGMA options for better concurrency and durability.
    """
    if connection.vendor == 'sqlite':
        with connection.cursor() as cursor:
            # Enable Write-Ahead Logging (WAL) mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL;")
            # Set synchronous mode for balancing speed and safety
            cursor.execute("PRAGMA synchronous=NORMAL;")
