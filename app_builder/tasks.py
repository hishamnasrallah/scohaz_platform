
from celery import shared_task
from django.core.management import call_command

@shared_task
def create_app_task(app_name, models_file, **options):
    call_command("create_app", app_name, models_file=models_file, **options)