
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Populate initial data for the app'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating initial data...')
        # Add your custom logic here
        self.stdout.write(self.style.SUCCESS('Data populated successfully!'))
