from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scohaz_platform.settings')

app = Celery('scohaz_platform')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
