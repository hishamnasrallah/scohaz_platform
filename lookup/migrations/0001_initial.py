# Generated by Django 5.1.4 on 2024-12-09 11:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Lookup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.IntegerField(choices=[(1, 'Lookup'), (2, 'Lookup Value')], default=2)),
                ('name', models.CharField(blank=True, max_length=50, null=True)),
                ('name_ara', models.CharField(blank=True, max_length=50, null=True)),
                ('code', models.CharField(blank=True, max_length=20, null=True)),
                ('icon', models.CharField(blank=True, max_length=100, null=True)),
                ('active_ind', models.BooleanField(blank=True, default=True, null=True)),
                ('parent_lookup', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lookup_children', to='lookup.lookup')),
            ],
        ),
    ]
