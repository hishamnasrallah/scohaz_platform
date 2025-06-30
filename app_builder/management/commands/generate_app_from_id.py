from django.core.management.base import BaseCommand
from app_builder.utils.app_generator import AppGeneratorService


class Command(BaseCommand):
    help = 'Generate and create Django app from ApplicationDefinition ID'

    def add_arguments(self, parser):
        parser.add_argument('app_id', type=int, help='ApplicationDefinition ID')

    def handle(self, *args, **options):
        app_id = options['app_id']
        self.stdout.write(f"Generating app from ID: {app_id}")

        result = AppGeneratorService.generate_and_create_app(app_id)

        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully generated app '{result['app_name']}'"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to generate app: {result.get('error', 'Unknown error')}"
                )
            )