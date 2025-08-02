# File: add_all_widget_mappings.py
# Run this to add ALL widget mappings

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scohaz_platform.settings')
django.setup()

from builder.models import WidgetMapping

# Complete list of all widget mappings
all_widget_mappings = [
    # Layout Widgets
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
        'ui_type': 'stack',
        'flutter_widget': 'Stack',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'center',
        'flutter_widget': 'Center',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'padding',
        'flutter_widget': 'Padding',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'expanded',
        'flutter_widget': 'Expanded',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'flexible',
        'flutter_widget': 'Flexible',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'wrap',
        'flutter_widget': 'Wrap',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'listview',
        'flutter_widget': 'ListView',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'gridview',
        'flutter_widget': 'GridView',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'sizedbox',
        'flutter_widget': 'SizedBox',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },

    # Display Widgets
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
        'ui_type': 'richtext',
        'flutter_widget': 'RichText',
        'properties_mapping': {},
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
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'circularprogressindicator',
        'flutter_widget': 'CircularProgressIndicator',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'linearprogressindicator',
        'flutter_widget': 'LinearProgressIndicator',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'divider',
        'flutter_widget': 'Divider',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'chip',
        'flutter_widget': 'Chip',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },

    # Input Widgets
    {
        'ui_type': 'button',
        'flutter_widget': 'ElevatedButton',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'textbutton',
        'flutter_widget': 'TextButton',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'outlinedbutton',
        'flutter_widget': 'OutlinedButton',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'iconbutton',
        'flutter_widget': 'IconButton',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'floatingactionbutton',
        'flutter_widget': 'FloatingActionButton',
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
        'ui_type': 'textformfield',
        'flutter_widget': 'TextFormField',
        'properties_mapping': {
            'hintText': 'decoration: InputDecoration(hintText: {{value}})',
            'labelText': 'decoration: InputDecoration(labelText: {{value}})',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'checkbox',
        'flutter_widget': 'Checkbox',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'switch',
        'flutter_widget': 'Switch',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'radio',
        'flutter_widget': 'Radio',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'slider',
        'flutter_widget': 'Slider',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'dropdown',
        'flutter_widget': 'DropdownButton',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },

    # Material Design Widgets
    {
        'ui_type': 'card',
        'flutter_widget': 'Card',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'listtile',
        'flutter_widget': 'ListTile',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
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
    {
        'ui_type': 'drawer',
        'flutter_widget': 'Drawer',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'bottomnavigationbar',
        'flutter_widget': 'BottomNavigationBar',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'tabbar',
        'flutter_widget': 'TabBar',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'snackbar',
        'flutter_widget': 'SnackBar',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'alertdialog',
        'flutter_widget': 'AlertDialog',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'bottomsheet',
        'flutter_widget': 'BottomSheet',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'expansiontile',
        'flutter_widget': 'ExpansionTile',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'stepper',
        'flutter_widget': 'Stepper',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },

    # Styling Widgets
    {
        'ui_type': 'opacity',
        'flutter_widget': 'Opacity',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'transform',
        'flutter_widget': 'Transform',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'decoratedbox',
        'flutter_widget': 'DecoratedBox',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'cliprrect',
        'flutter_widget': 'ClipRRect',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'hero',
        'flutter_widget': 'Hero',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
]

print("Adding all widget mappings...\n")

# Clear existing mappings first (optional)
# WidgetMapping.objects.all().delete()

# Add all mappings
created_count = 0
updated_count = 0

for mapping_data in all_widget_mappings:
    widget_mapping, created = WidgetMapping.objects.update_or_create(
        ui_type=mapping_data['ui_type'],
        defaults=mapping_data
    )
    if created:
        print(f"✓ Created mapping for {mapping_data['ui_type']}")
        created_count += 1
    else:
        print(f"✓ Updated mapping for {mapping_data['ui_type']}")
        updated_count += 1

print(f"\n{'='*50}")
print(f"Total widget mappings: {len(all_widget_mappings)}")
print(f"Created: {created_count}")
print(f"Updated: {updated_count}")
print(f"{'='*50}")

# Verify all mappings
print("\nVerifying widget mappings...")
db_count = WidgetMapping.objects.filter(is_active=True).count()
print(f"Active widget mappings in database: {db_count}")

# List all UI types
print("\nAvailable widget types:")
for mapping in WidgetMapping.objects.filter(is_active=True).order_by('ui_type'):
    print(f"  - {mapping.ui_type} → {mapping.flutter_widget}")

print("\n✅ All widget mappings have been added successfully!")