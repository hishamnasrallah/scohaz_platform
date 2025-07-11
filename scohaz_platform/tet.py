# from __future__ import absolute_import, unicode_literals
# import os
# from celery import Celery
#
# # Set the default Django settings module for the 'celery' program.
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scohaz_platform.settings')
#
# app = Celery('scohaz_platform')
#
# # Using a string here means the worker doesn't have to serialize
# # the configuration object to child processes.
# # - namespace='CELERY' means all celery-related config keys should have a `CELERY_` prefix.
# app.config_from_object('django.conf:settings', namespace='CELERY')
#
# # Load task modules from all registered Django app configs.
# app.autodiscover_tasks()
#
# # Configure Redis as the Celery broker
# app.conf.broker_url = 'redis://localhost:6379/0'  # Using Redis as broker
# app.conf.result_backend = 'redis://localhost:6379/0'  # Using Redis as backend for task results
