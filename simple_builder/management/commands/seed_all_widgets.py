from django.core.management.base import BaseCommand
from simple_builder.models import WidgetMapping, ComponentTemplate


class Command(BaseCommand):
    help = 'Seed all widget mappings and component templates'

    def handle(self, *args, **options):
        # Create all widget mappings
        widget_mappings = [
            {
                'ui_type': 'text',
                'flutter_widget': 'Text',
                'properties_mapping': {
                    'text': '{{value}}',
                    'style': 'style: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': False,
            },
            {
                'ui_type': 'container',
                'flutter_widget': 'Container',
                'properties_mapping': {
                    'width': 'width: {{value}}',
                    'height': 'height: {{value}}',
                    'color': 'color: {{value}}',
                    'padding': 'padding: {{value}}',
                    'margin': 'margin: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': True,
            },
            {
                'ui_type': 'column',
                'flutter_widget': 'Column',
                'properties_mapping': {
                    'mainAxisAlignment': 'mainAxisAlignment: {{value}}',
                    'crossAxisAlignment': 'crossAxisAlignment: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': True,
            },
            {
                'ui_type': 'row',
                'flutter_widget': 'Row',
                'properties_mapping': {
                    'mainAxisAlignment': 'mainAxisAlignment: {{value}}',
                    'crossAxisAlignment': 'crossAxisAlignment: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': True,
            },
            {
                'ui_type': 'button',
                'flutter_widget': 'ElevatedButton',
                'properties_mapping': {
                    'text': 'child: Text({{value}})',
                    'onPressed': 'onPressed: {{value}}',
                },
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
                    'width': 'width: {{value}}',
                    'height': 'height: {{value}}',
                    'fit': 'fit: {{value}}',
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
                'properties_mapping': {
                    'alignment': 'alignment: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': True,
            },
            {
                'ui_type': 'scaffold',
                'flutter_widget': 'Scaffold',
                'properties_mapping': {
                    'backgroundColor': 'backgroundColor: {{value}}',
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
                    'elevation': 'elevation: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': False,
            },
            {
                'ui_type': 'card',
                'flutter_widget': 'Card',
                'properties_mapping': {
                    'elevation': 'elevation: {{value}}',
                    'color': 'color: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': True,
            },
            {
                'ui_type': 'listview',
                'flutter_widget': 'ListView',
                'properties_mapping': {
                    'scrollDirection': 'scrollDirection: {{value}}',
                    'shrinkWrap': 'shrinkWrap: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': True,
            },
            {
                'ui_type': 'sizedbox',
                'flutter_widget': 'SizedBox',
                'properties_mapping': {
                    'width': 'width: {{value}}',
                    'height': 'height: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': True,
            },
            {
                'ui_type': 'padding',
                'flutter_widget': 'Padding',
                'properties_mapping': {
                    'padding': 'padding: {{value}}',
                },
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
                'ui_type': 'switch',
                'flutter_widget': 'Switch',
                'properties_mapping': {
                    'value': 'value: {{value}}',
                    'onChanged': 'onChanged: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': False,
            },
            {
                'ui_type': 'checkbox',
                'flutter_widget': 'Checkbox',
                'properties_mapping': {
                    'value': 'value: {{value}}',
                    'onChanged': 'onChanged: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': False,
            },
            {
                'ui_type': 'divider',
                'flutter_widget': 'Divider',
                'properties_mapping': {
                    'height': 'height: {{value}}',
                    'thickness': 'thickness: {{value}}',
                    'color': 'color: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': False,
            },
            {
                'ui_type': 'listtile',
                'flutter_widget': 'ListTile',
                'properties_mapping': {
                    'title': 'title: Text({{value}})',
                    'subtitle': 'subtitle: Text({{value}})',
                    'onTap': 'onTap: {{value}}',
                },
                'import_statements': "import 'package:flutter/material.dart';",
                'can_have_children': False,
            },
        ]

        # Create widget mappings
        created_mappings = 0
        for mapping_data in widget_mappings:
            widget_mapping, created = WidgetMapping.objects.update_or_create(
                ui_type=mapping_data['ui_type'],
                defaults=mapping_data
            )
            if created:
                created_mappings += 1

        self.stdout.write(
            self.style.SUCCESS(f'Created {created_mappings} widget mappings')
        )

        # Create component templates
        component_templates = [
            # Layout Components
            {
                'name': 'Container',
                'category': 'layout',
                'flutter_widget': 'Container',
                'icon': 'square',
                'description': 'A box that can contain other widgets',
                'can_have_children': True,
                'max_children': 1,
                'default_properties': {
                    'width': 200,
                    'height': 200,
                    'color': '#FFFFFF',
                    'padding': {'all': 8},
                    'margin': {'all': 0},
                    'widget_group': 'Basic Layout',
                    'display_order': 1,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'Column',
                'category': 'layout',
                'flutter_widget': 'Column',
                'icon': 'view_column',
                'description': 'Arranges children vertically',
                'can_have_children': True,
                'default_properties': {
                    'mainAxisAlignment': 'start',
                    'crossAxisAlignment': 'center',
                    'widget_group': 'Basic Layout',
                    'display_order': 2,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'Row',
                'category': 'layout',
                'flutter_widget': 'Row',
                'icon': 'view_stream',
                'description': 'Arranges children horizontally',
                'can_have_children': True,
                'default_properties': {
                    'mainAxisAlignment': 'start',
                    'crossAxisAlignment': 'center',
                    'widget_group': 'Basic Layout',
                    'display_order': 3,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'Stack',
                'category': 'layout',
                'flutter_widget': 'Stack',
                'icon': 'layers',
                'description': 'Overlaps children widgets',
                'can_have_children': True,
                'default_properties': {
                    'alignment': 'topLeft',
                    'widget_group': 'Basic Layout',
                    'display_order': 4,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'Center',
                'category': 'layout',
                'flutter_widget': 'Center',
                'icon': 'center_focus_strong',
                'description': 'Centers a child widget',
                'can_have_children': True,
                'max_children': 1,
                'default_properties': {
                    'widget_group': 'Basic Layout',
                    'display_order': 5,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'Padding',
                'category': 'layout',
                'flutter_widget': 'Padding',
                'icon': 'padding',
                'description': 'Adds padding around a widget',
                'can_have_children': True,
                'max_children': 1,
                'default_properties': {
                    'padding': {'all': 16},
                    'widget_group': 'Basic Layout',
                    'display_order': 6,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'SizedBox',
                'category': 'layout',
                'flutter_widget': 'SizedBox',
                'icon': 'crop_square',
                'description': 'A box with specific size',
                'can_have_children': True,
                'max_children': 1,
                'default_properties': {
                    'width': 100,
                    'height': 100,
                    'widget_group': 'Basic Layout',
                    'display_order': 7,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'ListView',
                'category': 'layout',
                'flutter_widget': 'ListView',
                'icon': 'list',
                'description': 'Scrollable list of widgets',
                'can_have_children': True,
                'default_properties': {
                    'scrollDirection': 'vertical',
                    'shrinkWrap': True,
                    'widget_group': 'Scrollable',
                    'display_order': 8,
                    'show_in_builder': True,
                }
            },
            # Display Components
            {
                'name': 'Text',
                'category': 'display',
                'flutter_widget': 'Text',
                'icon': 'text_fields',
                'description': 'Display text',
                'default_properties': {
                    'text': 'Hello World',
                    'fontSize': 16,
                    'color': '#000000',
                    'fontWeight': 'normal',
                    'widget_group': 'Display',
                    'display_order': 10,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'Image',
                'category': 'display',
                'flutter_widget': 'Image',
                'icon': 'image',
                'description': 'Display an image',
                'default_properties': {
                    'source': 'https://via.placeholder.com/150',
                    'width': 150,
                    'height': 150,
                    'fit': 'contain',
                    'widget_group': 'Display',
                    'display_order': 11,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'Icon',
                'category': 'display',
                'flutter_widget': 'Icon',
                'icon': 'star',
                'description': 'Display an icon',
                'default_properties': {
                    'icon': 'star',
                    'size': 24,
                    'color': '#000000',
                    'widget_group': 'Display',
                    'display_order': 12,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'Card',
                'category': 'display',
                'flutter_widget': 'Card',
                'icon': 'credit_card',
                'description': 'Material Design card',
                'can_have_children': True,
                'max_children': 1,
                'default_properties': {
                    'elevation': 4,
                    'widget_group': 'Display',
                    'display_order': 13,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'Divider',
                'category': 'display',
                'flutter_widget': 'Divider',
                'icon': 'remove',
                'description': 'Horizontal line divider',
                'default_properties': {
                    'height': 1,
                    'thickness': 1,
                    'color': '#E0E0E0',
                    'widget_group': 'Display',
                    'display_order': 14,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'ListTile',
                'category': 'display',
                'flutter_widget': 'ListTile',
                'icon': 'list_alt',
                'description': 'Material list item',
                'default_properties': {
                    'title': 'List Item',
                    'subtitle': 'Subtitle text',
                    'widget_group': 'Display',
                    'display_order': 15,
                    'show_in_builder': True,
                }
            },
            # Input Components
            {
                'name': 'Button',
                'category': 'input',
                'flutter_widget': 'ElevatedButton',
                'icon': 'smart_button',
                'description': 'Material elevated button',
                'default_properties': {
                    'text': 'Click Me',
                    'widget_group': 'Input',
                    'display_order': 20,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'TextField',
                'category': 'input',
                'flutter_widget': 'TextField',
                'icon': 'input',
                'description': 'Text input field',
                'default_properties': {
                    'hintText': 'Enter text',
                    'labelText': 'Label',
                    'widget_group': 'Input',
                    'display_order': 21,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'Checkbox',
                'category': 'input',
                'flutter_widget': 'Checkbox',
                'icon': 'check_box',
                'description': 'Checkbox input',
                'default_properties': {
                    'value': False,
                    'widget_group': 'Input',
                    'display_order': 22,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'Switch',
                'category': 'input',
                'flutter_widget': 'Switch',
                'icon': 'toggle_on',
                'description': 'Toggle switch',
                'default_properties': {
                    'value': False,
                    'widget_group': 'Input',
                    'display_order': 23,
                    'show_in_builder': True,
                }
            },
            # Navigation Components
            {
                'name': 'Scaffold',
                'category': 'navigation',
                'flutter_widget': 'Scaffold',
                'icon': 'web',
                'description': 'Basic page structure',
                'can_have_children': True,
                'default_properties': {
                    'backgroundColor': '#FFFFFF',
                    'widget_group': 'Navigation',
                    'display_order': 30,
                    'show_in_builder': True,
                }
            },
            {
                'name': 'AppBar',
                'category': 'navigation',
                'flutter_widget': 'AppBar',
                'icon': 'view_headline',
                'description': 'Material app bar',
                'default_properties': {
                    'title': 'App Title',
                    'backgroundColor': '#2196F3',
                    'elevation': 4,
                    'widget_group': 'Navigation',
                    'display_order': 31,
                    'show_in_builder': True,
                }
            },
        ]

        created_templates = 0
        for template_data in component_templates:
            component, created = ComponentTemplate.objects.update_or_create(
                flutter_widget=template_data['flutter_widget'],
                defaults=template_data
            )
            if created:
                created_templates += 1

        self.stdout.write(
            self.style.SUCCESS(f'Created {created_templates} component templates')
        )