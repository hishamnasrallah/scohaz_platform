# Generated by Django 5.1.4 on 2024-12-18 12:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('license_subscription_manager', '0002_subscription_active_project_count_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='project_id',
            field=models.CharField(default=1, max_length=255),
            preserve_default=False,
        ),
    ]
