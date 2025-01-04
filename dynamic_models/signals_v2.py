from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from dynamic_models.models import DynamicModel, DynamicField
from dynamic_models.utils.utils import (
    create_table_for_model,
    delete_table_for_model,
    apply_schema_changes_for_model,
)


@receiver(post_save, sender=DynamicModel)
def handle_dynamic_model_save(sender, instance, created, **kwargs):
    """
    Handle the creation or update of a DynamicModel.
    """
    def on_commit():
        if created:
            create_table_for_model(instance.get_dynamic_model_class())
        else:
            apply_schema_changes_for_model(instance)

    transaction.on_commit(on_commit)


@receiver(post_delete, sender=DynamicModel)
def handle_dynamic_model_delete(sender, instance, **kwargs):
    """
    Handle the deletion of a DynamicModel by dropping its database table.
    """
    def on_commit():
        delete_table_for_model(instance.get_dynamic_model_class())

    transaction.on_commit(on_commit)


@receiver(post_save, sender=DynamicField)
def handle_dynamic_field_save(sender, instance, created, **kwargs):
    """
    Handle the creation or update of a DynamicField.
    """
    def on_commit():
        apply_schema_changes_for_model(instance.model)

    transaction.on_commit(on_commit)
