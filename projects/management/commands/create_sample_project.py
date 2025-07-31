from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from version.models import Version, LocalVersion
from projects.models import FlutterProject, Screen


class Command(BaseCommand):
    help = 'Creates a sample Flutter project with screens for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username for the project owner'
        )

    def handle(self, *args, **options):
        username = options['username']

        # Get or create user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@example.com'}
        )

        if created:
            user.set_password('password123')
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Created user: {username}')
            )

        # Create version
        version = Version.objects.create(
            version_number="1.0.0",
            operating_system="Android",
            _environment='1',
            active_ind=True
        )

        # Get or create language versions
        en_lang, _ = LocalVersion.objects.get_or_create(
            lang='en',
            defaults={
                'language_name': 'English',
                'active_ind': True
            }
        )

        ar_lang, _ = LocalVersion.objects.get_or_create(
            lang='ar',
            defaults={
                'language_name': 'Arabic',
                'active_ind': True
            }
        )

        # Create Flutter project
        project = FlutterProject.objects.create(
            name="Sample Shopping App",
            package_name="com.example.shopping",
            user=user,
            app_version=version,
            default_language='en',
            ui_structure={
                "app_name": "Shopping App",
                "theme": {
                    "primary_color": "#2196F3",
                    "accent_color": "#FF5722"
                }
            }
        )

        # Add languages
        project.supported_languages.add(en_lang, ar_lang)

        # Create home screen
        home_screen = Screen.objects.create(
            project=project,
            name="Home Screen",
            route="/",
            is_home=True,
            ui_structure={
                "type": "scaffold",
                "properties": {
                    "appBar": {
                        "title": "Shopping App",
                        "backgroundColor": "#2196F3"
                    }
                },
                "body": {
                    "type": "column",
                    "properties": {
                        "padding": 16,
                        "crossAxisAlignment": "stretch"
                    },
                    "children": [
                        {
                            "type": "text",
                            "properties": {
                                "useTranslation": True,
                                "translationKey": "welcome_message",
                                "style": {
                                    "fontSize": 24,
                                    "fontWeight": "bold"
                                }
                            }
                        },
                        {
                            "type": "container",
                            "properties": {
                                "height": 200,
                                "margin": {"top": 20}
                            },
                            "child": {
                                "type": "image",
                                "properties": {
                                    "source": "assets/banner.png",
                                    "fit": "cover"
                                }
                            }
                        },
                        {
                            "type": "button",
                            "properties": {
                                "text": "Browse Products",
                                "onPressed": "navigateToProducts",
                                "style": "elevated"
                            }
                        }
                    ]
                }
            }
        )

        # Create products screen
        products_screen = Screen.objects.create(
            project=project,
            name="Products",
            route="/products",
            is_home=False,
            ui_structure={
                "type": "scaffold",
                "properties": {
                    "appBar": {
                        "title": "Products",
                        "backgroundColor": "#2196F3"
                    }
                },
                "body": {
                    "type": "listview",
                    "properties": {
                        "padding": 8
                    },
                    "children": [
                        {
                            "type": "card",
                            "properties": {
                                "margin": 8,
                                "elevation": 4
                            },
                            "child": {
                                "type": "listtile",
                                "properties": {
                                    "title": "Product Item",
                                    "subtitle": "Product description",
                                    "leading": {
                                        "type": "icon",
                                        "name": "shopping_cart"
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created sample project:\n'
                f'- Project: {project.name}\n'
                f'- Package: {project.package_name}\n'
                f'- Version: {version.version_number}\n'
                f'- Languages: {", ".join([l.lang for l in project.supported_languages.all()])}\n'
                f'- Screens: {project.screen_count}\n'
                f'\nAccess Django admin at: /admin/\n'
                f'Username: {username}\n'
                f'Password: password123'
            )
        )