# Generated by Django 5.1.4 on 2024-12-16 08:49

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dynamicflow', '0012_field_allowed_lookups'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='field',
            name='_sub_fields',
        ),
        migrations.AddField(
            model_name='field',
            name='_parent_field',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sub_fields', to='dynamicflow.field'),
        ),
    ]
