from django.core.management.base import BaseCommand
from dynamic_models.models import DynamicModel
from dynamic_models.utils.utils import create_dynamic_model, sync_model_fields

class Command(BaseCommand):
    help = 'Apply schema changes to dynamic models'

    def handle(self, *args, **kwargs):
        for dynamic_model in DynamicModel.objects.all():
            model = create_dynamic_model(dynamic_model)
            sync_model_fields(model, dynamic_model.fields.all())
        self.stdout.write("Schema changes applied.")
