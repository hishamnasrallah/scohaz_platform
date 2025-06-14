# Generated by Django 5.1.4 on 2024-12-15 11:58

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dynamicflow', '0010_alter_field__lookup'),
        ('lookup', '0003_lookup_is_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='field',
            name='_lookup',
            field=models.ForeignKey(blank=True, limit_choices_to={'is_category': True}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='field_lookups', to='lookup.lookup'),
        ),
    ]
