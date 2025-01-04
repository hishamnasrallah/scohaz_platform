from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from dynamic_models.models import DynamicModel, DynamicField
from dynamic_models.utils.utils import (
    apply_schema_changes_for_model,
    delete_table_for_model,
    reload_database_schema,
)
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DynamicModel)
def handle_dynamic_model_save(sender, instance, created, **kwargs):
    """
    Signal to handle the creation or update of a DynamicModel.
    """
    try:
        reload_database_schema()
        apply_schema_changes_for_model(instance)
        if created:
            logger.info(f"DynamicModel '{instance.name}' created and schema applied.")
        else:
            logger.info(f"DynamicModel '{instance.name}' updated and schema applied.")
    except Exception as e:
        logger.error(f"Error handling DynamicModel save for '{instance.name}': {e}")


@receiver(post_delete, sender=DynamicModel)
def handle_dynamic_model_delete(sender, instance, **kwargs):
    """
    Signal to handle the deletion of a DynamicModel.
    """
    try:
        delete_table_for_model(instance.get_dynamic_model_class())
        logger.info(f"DynamicModel '{instance.name}' deleted along with its table.")
    except Exception as e:
        logger.error(f"Error handling DynamicModel deletion for '{instance.name}': {e}")


@receiver(post_save, sender=DynamicField)
def handle_dynamic_field_save(sender, instance, created, **kwargs):
    """
    Signal to handle the addition or update of a DynamicField.
    """
    try:
        reload_database_schema()
        apply_schema_changes_for_model(instance.model)
        if created:
            logger.info(
                f"DynamicField '{instance.name}' added to model '{instance.model.name}'."
            )
        else:
            logger.info(
                f"DynamicField '{instance.name}' updated for model '{instance.model.name}'."
            )
    except Exception as e:
        logger.error(
            f"Error handling DynamicField save for '{instance.name}' in model '{instance.model.name}': {e}"
        )


@receiver(post_delete, sender=DynamicField)
def handle_dynamic_field_delete(sender, instance, **kwargs):
    """
    Signal to handle the deletion of a DynamicField.
    """
    try:
        reload_database_schema()
        apply_schema_changes_for_model(instance.model)
        logger.info(
            f"DynamicField '{instance.name}' deleted from model '{instance.model.name}'."
        )
    except Exception as e:
        logger.error(
            f"Error handling DynamicField deletion for '{instance.name}' in model '{instance.model.name}': {e}"
        )
