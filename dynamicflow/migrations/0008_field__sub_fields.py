# Generated by Django 5.1.4 on 2024-12-15 11:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dynamicflow', '0007_field_active_ind'),
    ]

    operations = [
        migrations.AddField(
            model_name='field',
            name='_sub_fields',
            field=models.ManyToManyField(blank=True, to='dynamicflow.field'),
        ),
    ]
