# File: builder/management/commands/create_widget_mappings.py

from django.core.management.base import BaseCommand
from builder.models import WidgetMapping


class Command(BaseCommand):
    help = 'Create initial widget mappings'

    def handle(self, *args, **options):
        mappings = [
            {
                'ui_type': 'text',
                'flutter_widget': 'Text',
                'properties_mapping': {
                    'text': '{{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': False,
            },
            {
                'ui_type': 'container',
                'flutter_widget': 'Container',
                'properties_mapping': {},
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': True,
            },
            {
                'ui_type': 'column',
                'flutter_widget': 'Column',
                'properties_mapping': {},
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': True,
            },
            {
                'ui_type': 'row',
                'flutter_widget': 'Row',
                'properties_mapping': {},
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': True,
            },
            {
                'ui_type': 'button',
                'flutter_widget': 'ElevatedButton',
                'properties_mapping': {},
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': False,
            },
            {
                'ui_type': 'textfield',
                'flutter_widget': 'TextField',
                'properties_mapping': {
                    'hintText': 'decoration: InputDecoration(hintText: {{value}})',
                    'labelText': 'decoration: InputDecoration(labelText: {{value}})',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': False,
            },
        ]

        for mapping_data in mappings:
            WidgetMapping.objects.update_or_create(
                ui_type=mapping_data['ui_type'],
                defaults=mapping_data
            )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {len(mappings)} widget mappings')
        )