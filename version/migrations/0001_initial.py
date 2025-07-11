# Generated by Django 3.0.7 on 2021-11-16 13:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Version',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version_number', models.CharField(blank=True, max_length=15, null=True)),
                ('operating_system', models.CharField(blank=True, choices=[('IOS', 'IOS'), ('Android', 'Android')], max_length=10, null=True)),
                ('_environment', models.CharField(blank=True, choices=[('0', 'Staging'), ('1', 'Production'), ('2', 'Development'), ('3', 'Local')], max_length=1, null=True)),
                ('backend_endpoint', models.CharField(blank=True, max_length=200, null=True)),
                ('active_ind', models.BooleanField(default=True)),
                ('expiration_date', models.DateField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ListOfActiveOldApp',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
