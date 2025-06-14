# Generated by Django 5.1.4 on 2024-12-09 11:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_customuser_activated_account_customuser_sms_code_and_more'),
        ('lookup', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='phonenumber',
            name='number_type',
            field=models.ForeignKey(limit_choices_to={'parent_lookup__name': 'Phone Types', 'type': 2}, on_delete=django.db.models.deletion.CASCADE, to='lookup.lookup', verbose_name='Number Type'),
        ),
    ]
