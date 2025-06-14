# Generated by Django 5.1.4 on 2024-12-10 06:44

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('lookup', '0002_lookupconfig'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Case',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('serial_number', models.CharField(editable=False, max_length=30, unique=True, verbose_name='Serial Number')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('additional_data', models.JSONField(blank=True, help_text='Store additional case-specific information.', null=True, verbose_name='Additional Data')),
                ('applicant_type', models.ForeignKey(blank=True, limit_choices_to={'category': 'ApplicantType'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='case_applicant_type', to='lookup.lookup', verbose_name='Applicant Type')),
                ('assigned_emp', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='case_assigned_emp', to=settings.AUTH_USER_MODEL, verbose_name='Assigned Employee')),
                ('assigned_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='case_assigned_group', to='auth.group', verbose_name='Assigned Group')),
                ('beneficiary', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cases', to=settings.AUTH_USER_MODEL, verbose_name='Beneficiary')),
                ('case_type', models.ForeignKey(blank=True, limit_choices_to={'category': 'Service'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='case_type', to='lookup.lookup', verbose_name='Case Type')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_cases', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
            ],
        ),
    ]
