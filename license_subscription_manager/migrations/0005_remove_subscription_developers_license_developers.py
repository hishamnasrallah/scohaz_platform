# Generated by Django 5.1.4 on 2024-12-18 12:38

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('license_subscription_manager', '0004_remove_license_project_id_subscription_developers'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subscription',
            name='developers',
        ),
        migrations.AddField(
            model_name='license',
            name='developers',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL),
        ),
    ]
