# Generated by Django 5.1.4 on 2024-12-11 18:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dynamicflow', '0002_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='FieldType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=50, null=True)),
                ('name_ara', models.CharField(blank=True, max_length=50, null=True)),
                ('code', models.CharField(blank=True, max_length=20, null=True)),
                ('active_ind', models.BooleanField(blank=True, default=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('_field_name', models.CharField(blank=True, max_length=50, null=True, verbose_name='Field Name')),
                ('_sequence', models.IntegerField(blank=True, null=True)),
                ('_field_display_name', models.CharField(blank=True, max_length=50, null=True, verbose_name='Field Display Name')),
                ('_field_display_name_ara', models.CharField(blank=True, max_length=50, null=True, verbose_name='Field Display Name Ara')),
                ('_max_length', models.PositiveIntegerField(blank=True, null=True)),
                ('_mandatory', models.BooleanField(blank=True, default=False, null=True)),
                ('_min_length', models.PositiveIntegerField(blank=True, null=True)),
                ('_value_greater_than', models.IntegerField(blank=True, null=True)),
                ('_value_less_than', models.IntegerField(blank=True, null=True)),
                ('_date_less_than', models.DateField(blank=True, null=True)),
                ('_date_greater_than', models.DateField(blank=True, null=True)),
                ('_size_greater_than', models.IntegerField(blank=True, null=True)),
                ('_size_less_than', models.IntegerField(blank=True, null=True)),
                ('_only_positive', models.BooleanField(blank=True, default=False, null=True)),
                ('_is_hidden', models.BooleanField(blank=True, default=False, null=True)),
                ('_is_disabled', models.BooleanField(blank=True, default=False, null=True)),
                ('_category', models.ManyToManyField(blank=True, to='dynamicflow.category')),
                ('_field_type', models.ForeignKey(blank=True, max_length=50, null=True, on_delete=django.db.models.deletion.CASCADE, to='dynamicflow.fieldtype')),
            ],
        ),
    ]
