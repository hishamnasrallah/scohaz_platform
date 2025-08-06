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
            {
                'ui_type': 'image',
                'flutter_widget': 'Image',
                'properties_mapping': {
                    'source': 'Image.network({{value}})',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': False,
            },
            {
                'ui_type': 'icon',
                'flutter_widget': 'Icon',
                'properties_mapping': {
                    'icon': 'Icons.{{value}}',
                    'size': 'size: {{value}}',
                    'color': 'color: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': False,
            },
            {
                'ui_type': 'stack',
                'flutter_widget': 'Stack',
                'properties_mapping': {},
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': True,
            },
            {
                'ui_type': 'listview',
                'flutter_widget': 'ListView',
                'properties_mapping': {
                    'scrollDirection': 'scrollDirection: Axis.{{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': True,
            },
            {
                'ui_type': 'card',
                'flutter_widget': 'Card',
                'properties_mapping': {
                    'elevation': 'elevation: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': True,
            },
            {
                'ui_type': 'appbar',
                'flutter_widget': 'AppBar',
                'properties_mapping': {
                    'title': 'title: Text({{value}})',
                    'backgroundColor': 'backgroundColor: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': False,
            },
        ]

        created_count = 0
        updated_count = 0

        for mapping_data in mappings:
            widget_mapping, created = WidgetMapping.objects.update_or_create(
                ui_type=mapping_data['ui_type'],
                defaults=mapping_data
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} and updated {updated_count} widget mappings'
            )
        )