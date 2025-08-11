from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from simple_project.models import FlutterProject, Screen
import uuid

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a sample Flutter project with two screens showcasing all widgets'

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
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User {username} does not exist. Creating...')
            )
            user = User.objects.create_superuser(
                username=username,
                email='admin@example.com',
                password='admin123'
            )

        # Create Flutter Project
        project = FlutterProject.objects.create(
            name='Sample Widget Demo',
            description='A demo app showcasing all available widgets',
            package_name='com.example.widgetdemo',
            user=user,
            primary_color='#2196F3',
            secondary_color='#FF4081',
            default_language='en'
        )

        # Create Home Screen with all display and input widgets
        home_screen_structure = {
            "id": str(uuid.uuid4()),
            "type": "scaffold",
            "properties": {
                "backgroundColor": "#F5F5F5"
            },
            "children": [
                {
                    "id": str(uuid.uuid4()),
                    "type": "column",
                    "properties": {
                        "mainAxisAlignment": "start",
                        "crossAxisAlignment": "stretch"
                    },
                    "children": [
                        # AppBar
                        {
                            "id": str(uuid.uuid4()),
                            "type": "appbar",
                            "properties": {
                                "title": "Widget Demo - Home",
                                "backgroundColor": "#2196F3",
                                "elevation": 4
                            }
                        },
                        # Scrollable content
                        {
                            "id": str(uuid.uuid4()),
                            "type": "listview",
                            "properties": {
                                "shrinkWrap": True,
                                "scrollDirection": "vertical"
                            },
                            "children": [
                                # Padding wrapper
                                {
                                    "id": str(uuid.uuid4()),
                                    "type": "padding",
                                    "properties": {
                                        "padding": {"all": 16}
                                    },
                                    "children": [
                                        {
                                            "id": str(uuid.uuid4()),
                                            "type": "column",
                                            "properties": {
                                                "crossAxisAlignment": "stretch"
                                            },
                                            "children": [
                                                # Title Text
                                                {
                                                    "id": str(uuid.uuid4()),
                                                    "type": "text",
                                                    "properties": {
                                                        "text": "Welcome to Widget Demo",
                                                        "fontSize": 24,
                                                        "fontWeight": "bold",
                                                        "color": "#333333"
                                                    }
                                                },
                                                # SizedBox for spacing
                                                {
                                                    "id": str(uuid.uuid4()),
                                                    "type": "sizedbox",
                                                    "properties": {
                                                        "height": 16
                                                    }
                                                },
                                                # Card with content
                                                {
                                                    "id": str(uuid.uuid4()),
                                                    "type": "card",
                                                    "properties": {
                                                        "elevation": 4
                                                    },
                                                    "children": [
                                                        {
                                                            "id": str(uuid.uuid4()),
                                                            "type": "padding",
                                                            "properties": {
                                                                "padding": {"all": 16}
                                                            },
                                                            "children": [
                                                                {
                                                                    "id": str(uuid.uuid4()),
                                                                    "type": "column",
                                                                    "properties": {},
                                                                    "children": [
                                                                        # Row with icon and text
                                                                        {
                                                                            "id": str(uuid.uuid4()),
                                                                            "type": "row",
                                                                            "properties": {
                                                                                "mainAxisAlignment": "start"
                                                                            },
                                                                            "children": [
                                                                                {
                                                                                    "id": str(uuid.uuid4()),
                                                                                    "type": "icon",
                                                                                    "properties": {
                                                                                        "icon": "info",
                                                                                        "size": 32,
                                                                                        "color": "#2196F3"
                                                                                    }
                                                                                },
                                                                                {
                                                                                    "id": str(uuid.uuid4()),
                                                                                    "type": "sizedbox",
                                                                                    "properties": {
                                                                                        "width": 16
                                                                                    }
                                                                                },
                                                                                {
                                                                                    "id": str(uuid.uuid4()),
                                                                                    "type": "text",
                                                                                    "properties": {
                                                                                        "text": "Card Title",
                                                                                        "fontSize": 18,
                                                                                        "fontWeight": "bold"
                                                                                    }
                                                                                }
                                                                            ]
                                                                        },
                                                                        # Divider
                                                                        {
                                                                            "id": str(uuid.uuid4()),
                                                                            "type": "divider",
                                                                            "properties": {
                                                                                "height": 16,
                                                                                "thickness": 1,
                                                                                "color": "#E0E0E0"
                                                                            }
                                                                        },
                                                                        # Description text
                                                                        {
                                                                            "id": str(uuid.uuid4()),
                                                                            "type": "text",
                                                                            "properties": {
                                                                                "text": "This card demonstrates nested layouts with various widgets.",
                                                                                "fontSize": 14,
                                                                                "color": "#666666"
                                                                            }
                                                                        }
                                                                    ]
                                                                }
                                                            ]
                                                        }
                                                    ]
                                                },
                                                # SizedBox for spacing
                                                {
                                                    "id": str(uuid.uuid4()),
                                                    "type": "sizedbox",
                                                    "properties": {
                                                        "height": 24
                                                    }
                                                },
                                                # Input Section
                                                {
                                                    "id": str(uuid.uuid4()),
                                                    "type": "text",
                                                    "properties": {
                                                        "text": "Input Widgets",
                                                        "fontSize": 20,
                                                        "fontWeight": "bold",
                                                        "color": "#333333"
                                                    }
                                                },
                                                {
                                                    "id": str(uuid.uuid4()),
                                                    "type": "sizedbox",
                                                    "properties": {
                                                        "height": 16
                                                    }
                                                },
                                                # TextField
                                                {
                                                    "id": str(uuid.uuid4()),
                                                    "type": "textfield",
                                                    "properties": {
                                                        "hintText": "Enter your name",
                                                        "labelText": "Name"
                                                    }
                                                },
                                                {
                                                    "id": str(uuid.uuid4()),
                                                    "type": "sizedbox",
                                                    "properties": {
                                                        "height": 16
                                                    }
                                                },
                                                # Row with Checkbox and Switch
                                                {
                                                    "id": str(uuid.uuid4()),
                                                    "type": "row",
                                                    "properties": {
                                                        "mainAxisAlignment": "spaceAround"
                                                    },
                                                    "children": [
                                                        {
                                                            "id": str(uuid.uuid4()),
                                                            "type": "row",
                                                            "properties": {},
                                                            "children": [
                                                                {
                                                                    "id": str(uuid.uuid4()),
                                                                    "type": "checkbox",
                                                                    "properties": {
                                                                        "value": False
                                                                    }
                                                                },
                                                                {
                                                                    "id": str(uuid.uuid4()),
                                                                    "type": "text",
                                                                    "properties": {
                                                                        "text": "Checkbox"
                                                                    }
                                                                }
                                                            ]
                                                        },
                                                        {
                                                            "id": str(uuid.uuid4()),
                                                            "type": "row",
                                                            "properties": {},
                                                            "children": [
                                                                {
                                                                    "id": str(uuid.uuid4()),
                                                                    "type": "switch",
                                                                    "properties": {
                                                                        "value": False
                                                                    }
                                                                },
                                                                {
                                                                    "id": str(uuid.uuid4()),
                                                                    "type": "text",
                                                                    "properties": {
                                                                        "text": "Switch"
                                                                    }
                                                                }
                                                            ]
                                                        }
                                                    ]
                                                },
                                                {
                                                    "id": str(uuid.uuid4()),
                                                    "type": "sizedbox",
                                                    "properties": {
                                                        "height": 24
                                                    }
                                                },
                                                # Navigation Button (redirects to second screen)
                                                {
                                                    "id": str(uuid.uuid4()),
                                                    "type": "center",
                                                    "properties": {},
                                                    "children": [
                                                        {
                                                            "id": str(uuid.uuid4()),
                                                            "type": "button",
                                                            "properties": {
                                                                "text": "Go to Second Screen",
                                                                "route": "/second"  # Navigation property
                                                            }
                                                        }
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        home_screen = Screen.objects.create(
            project=project,
            name='Home Screen',
            route='/home',
            is_home=True,
            ui_structure=home_screen_structure
        )

        # Create Second Screen with different layout patterns
        second_screen_structure = {
            "id": str(uuid.uuid4()),
            "type": "scaffold",
            "properties": {
                "backgroundColor": "#FFFFFF"
            },
            "children": [
                {
                    "id": str(uuid.uuid4()),
                    "type": "column",
                    "properties": {},
                    "children": [
                        # AppBar
                        {
                            "id": str(uuid.uuid4()),
                            "type": "appbar",
                            "properties": {
                                "title": "Second Screen",
                                "backgroundColor": "#FF4081",
                                "elevation": 4
                            }
                        },
                        # Stack layout example
                        {
                            "id": str(uuid.uuid4()),
                            "type": "stack",
                            "properties": {
                                "alignment": "center"
                            },
                            "children": [
                                # Background container
                                {
                                    "id": str(uuid.uuid4()),
                                    "type": "container",
                                    "properties": {
                                        "width": 350,
                                        "height": 200,
                                        "color": "#E3F2FD"
                                    }
                                },
                                # Center text on top
                                {
                                    "id": str(uuid.uuid4()),
                                    "type": "center",
                                    "properties": {},
                                    "children": [
                                        {
                                            "id": str(uuid.uuid4()),
                                            "type": "text",
                                            "properties": {
                                                "text": "Stack Layout Example",
                                                "fontSize": 20,
                                                "fontWeight": "bold",
                                                "color": "#1976D2"
                                            }
                                        }
                                    ]
                                }
                            ]
                        },
                        # ListTile examples
                        {
                            "id": str(uuid.uuid4()),
                            "type": "padding",
                            "properties": {
                                "padding": {"all": 16}
                            },
                            "children": [
                                {
                                    "id": str(uuid.uuid4()),
                                    "type": "column",
                                    "properties": {},
                                    "children": [
                                        {
                                            "id": str(uuid.uuid4()),
                                            "type": "listtile",
                                            "properties": {
                                                "title": "List Item 1",
                                                "subtitle": "This is the first item"
                                            }
                                        },
                                        {
                                            "id": str(uuid.uuid4()),
                                            "type": "divider",
                                            "properties": {}
                                        },
                                        {
                                            "id": str(uuid.uuid4()),
                                            "type": "listtile",
                                            "properties": {
                                                "title": "List Item 2",
                                                "subtitle": "This is the second item"
                                            }
                                        },
                                        {
                                            "id": str(uuid.uuid4()),
                                            "type": "divider",
                                            "properties": {}
                                        },
                                        {
                                            "id": str(uuid.uuid4()),
                                            "type": "listtile",
                                            "properties": {
                                                "title": "List Item 3",
                                                "subtitle": "This is the third item"
                                            }
                                        }
                                    ]
                                }
                            ]
                        },
                        # Image example
                        {
                            "id": str(uuid.uuid4()),
                            "type": "center",
                            "properties": {},
                            "children": [
                                {
                                    "id": str(uuid.uuid4()),
                                    "type": "image",
                                    "properties": {
                                        "source": "https://via.placeholder.com/200",
                                        "width": 200,
                                        "height": 200,
                                        "fit": "cover"
                                    }
                                }
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "type": "sizedbox",
                            "properties": {
                                "height": 24
                            }
                        },
                        # Back button
                        {
                            "id": str(uuid.uuid4()),
                            "type": "center",
                            "properties": {},
                            "children": [
                                {
                                    "id": str(uuid.uuid4()),
                                    "type": "button",
                                    "properties": {
                                        "text": "Go Back",
                                        "route": "/home"  # Navigate back
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        second_screen = Screen.objects.create(
            project=project,
            name='Second Screen',
            route='/second',
            is_home=False,
            ui_structure=second_screen_structure
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created sample project "{project.name}" with 2 screens'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(f'Project ID: {project.id}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Home Screen ID: {home_screen.id}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Second Screen ID: {second_screen.id}')
        )