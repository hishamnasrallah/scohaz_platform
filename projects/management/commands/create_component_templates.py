# File: projects/management/commands/create_component_templates.py

from django.core.management.base import BaseCommand
from projects.models import ComponentTemplate


class Command(BaseCommand):
    help = 'Create initial Flutter component templates'

    def handle(self, *args, **options):
        components = [
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
                    'width': None,
                    'height': None,
                    'color': '#FFFFFF',
                    'padding': {'all': 0},
                    'margin': {'all': 0},
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
                    'fontSize': 14,
                    'color': '#000000',
                    'fontWeight': 'normal',
                }
            },
            {
                'name': 'Image',
                'category': 'display',
                'flutter_widget': 'Image',
                'icon': 'image',
                'description': 'Display an image',
                'default_properties': {
                    'source': '',
                    'width': None,
                    'height': None,
                    'fit': 'contain',
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
                }
            },

            # Input Components
            {
                'name': 'Button',
                'category': 'input',
                'flutter_widget': 'ElevatedButton',
                'icon': 'smart_button',
                'description': 'A material design elevated button',
                'default_properties': {
                    'text': 'Click Me',
                    'onPressed': 'null',
                }
            },
            {
                'name': 'Text Field',
                'category': 'input',
                'flutter_widget': 'TextField',
                'icon': 'input',
                'description': 'Text input field',
                'default_properties': {
                    'hintText': 'Enter text',
                    'labelText': '',
                }
            },
            {
                'name': 'Checkbox',
                'category': 'input',
                'flutter_widget': 'Checkbox',
                'icon': 'check_box',
                'description': 'A checkbox input',
                'default_properties': {
                    'value': False,
                    'onChanged': 'null',
                }
            },
            {
                'name': 'Switch',
                'category': 'input',
                'flutter_widget': 'Switch',
                'icon': 'toggle_on',
                'description': 'A toggle switch',
                'default_properties': {
                    'value': False,
                    'onChanged': 'null',
                }
            },

            # Navigation Components
            {
                'name': 'App Bar',
                'category': 'navigation',
                'flutter_widget': 'AppBar',
                'icon': 'view_headline',
                'description': 'Material Design app bar',
                'default_properties': {
                    'title': 'App Title',
                    'backgroundColor': '#2196F3',
                }
            },
            {
                'name': 'Bottom Navigation',
                'category': 'navigation',
                'flutter_widget': 'BottomNavigationBar',
                'icon': 'menu',
                'description': 'Bottom navigation bar',
                'default_properties': {
                    'items': [],
                    'currentIndex': 0,
                }
            },
        ]

        created_count = 0
        updated_count = 0

        for comp_data in components:
            component, created = ComponentTemplate.objects.update_or_create(
                flutter_widget=comp_data['flutter_widget'],
                defaults=comp_data
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} and updated {updated_count} component templates'
            )
        )