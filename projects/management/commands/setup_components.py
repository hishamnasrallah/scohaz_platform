from django.core.management.base import BaseCommand
from projects.models import ComponentTemplate


class Command(BaseCommand):
    help = 'Create basic component templates for the visual builder'

    def handle(self, *args, **options):
        components = [
            {
                'name': 'Scaffold',
                'category': 'layout',
                'flutter_widget': 'Scaffold',
                'icon': '🏗️',
                'description': 'Basic app screen structure with app bar and body',
                'default_properties': {
                    'backgroundColor': '#FFFFFF'
                },
                'can_have_children': True,
                'allowed_child_types': ['appBar', 'body', 'floatingActionButton'],
                'is_active': True
            },
            {
                'name': 'AppBar',
                'category': 'navigation',
                'flutter_widget': 'AppBar',
                'icon': '📱',
                'description': 'Top app bar with title and actions',
                'default_properties': {
                    'title': 'App Title',
                    'backgroundColor': '#2196F3',
                    'elevation': 4
                },
                'can_have_children': False,
                'is_active': True
            },
            {
                'name': 'Container',
                'category': 'layout',
                'flutter_widget': 'Container',
                'icon': '📦',
                'description': 'Box with styling and child widget',
                'default_properties': {
                    'padding': 16,
                    'margin': 8
                },
                'can_have_children': True,
                'max_children': 1,
                'allowed_child_types': ['*'],
                'is_active': True
            },
            {
                'name': 'Column',
                'category': 'layout',
                'flutter_widget': 'Column',
                'icon': '⬇️',
                'description': 'Vertical layout for multiple children',
                'default_properties': {
                    'mainAxisAlignment': 'start',
                    'crossAxisAlignment': 'center'
                },
                'can_have_children': True,
                'allowed_child_types': ['*'],
                'is_active': True
            },
            {
                'name': 'Text',
                'category': 'basic',
                'flutter_widget': 'Text',
                'icon': '📝',
                'description': 'Display text content',
                'default_properties': {
                    'content': 'Hello World',
                    'style': {
                        'fontSize': 16,
                        'color': '#000000'
                    }
                },
                'can_have_children': False,
                'is_active': True
            },
            {
                'name': 'Button',
                'category': 'input',
                'flutter_widget': 'ElevatedButton',
                'icon': '🔘',
                'description': 'Clickable button',
                'default_properties': {
                    'text': 'Click Me',
                    'onPressed': 'handlePress'
                },
                'can_have_children': False,
                'is_active': True
            },
            {
                'name': 'Center',
                'category': 'layout',
                'flutter_widget': 'Center',
                'icon': '🎯',
                'description': 'Centers its child',
                'default_properties': {},
                'can_have_children': True,
                'max_children': 1,
                'allowed_child_types': ['*'],
                'is_active': True
            }
        ]

        for comp_data in components:
            component, created = ComponentTemplate.objects.update_or_create(
                name=comp_data['name'],
                defaults=comp_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created component: {component.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Updated component: {component.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('Successfully created/updated all component templates')
        )