from django.apps import AppConfig
from django.db import connection
import logging

logger = logging.getLogger(__name__)

class DynamicModelsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dynamic_models'

    def ready(self):
        """
        Set SQLite-specific PRAGMA options and load signal handlers on app startup.
        """
        from dynamic_models.signals import (
            handle_dynamic_model_save,
            handle_dynamic_model_delete,
            handle_dynamic_field_save,
        )
        set_sqlite_pragmas()
        logger.info("DynamicModelsConfig initialized. Signal handlers are ready, and SQLite PRAGMAs set (if applicable).")


def set_sqlite_pragmas():
    """
    Set SQLite-specific PRAGMA options for better concurrency and durability.
    """
    if connection.vendor == 'sqlite':
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys = ON;")
