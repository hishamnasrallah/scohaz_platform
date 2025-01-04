from django.core.management.base import BaseCommand
from dynamic_models.models import DynamicModel
from dynamic_models.utils.utils import create_dynamic_model, create_table_for_model, reload_database_schema
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Initialize dynamic models and their tables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model_ids',
            type=str,
            help='Comma-separated IDs of DynamicModel records to process.',
        )

    def handle(self, *args, **options):
        model_ids = options.get('model_ids')
        if model_ids:
            model_ids = list(map(int, model_ids.split(',')))  # Convert comma-separated IDs to integers
            queryset = DynamicModel.objects.filter(id__in=model_ids)
        else:
            queryset = DynamicModel.objects.all()

        reload_database_schema()

        for dynamic_model in queryset:
            try:
                model = create_dynamic_model(dynamic_model)
                create_table_for_model(model)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Dynamic model '{dynamic_model.name}' initialized successfully."
                    )
                )
            except Exception as e:
                logger.error(f"Error initializing model '{dynamic_model.name}': {e}")
                self.stderr.write(
                    self.style.ERROR(
                        f"Error initializing model '{dynamic_model.name}': {e}"
                    )
                )
