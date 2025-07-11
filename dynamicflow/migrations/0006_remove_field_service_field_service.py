# Generated by Django 5.1.4 on 2024-12-11 19:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dynamicflow', '0005_field_service'),
        ('lookup', '0002_lookupconfig'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='field',
            name='service',
        ),
        migrations.AddField(
            model_name='field',
            name='service',
            field=models.ManyToManyField(blank=True, limit_choices_to={'parent_lookup__name': 'Service'}, related_name='service_field', to='lookup.lookup'),
        ),
    ]
