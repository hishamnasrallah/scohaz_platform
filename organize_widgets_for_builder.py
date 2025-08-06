# File: add_builder_components.py
# Run this to add ALL Flutter component templates organized for Angular builder
# Similar pattern to add_missing_mappings.py

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scohaz_platform.settings')
django.setup()

from projects.models import ComponentTemplate

# Complete list of Flutter components organized for Angular builder
builder_components = [
    # Basic Layout Components (Most Used)
    {
        'name': 'Container',
        'category': 'layout',
        'flutter_widget': 'Container',
        'icon': 'crop_free',
        'description': 'A box that can contain other widgets with padding, margin, and styling',
        'can_have_children': True,
        'max_children': 1,
        'default_properties': {
            'width': None,
            'height': None,
            'color': '#FFFFFF',
            'padding': {'all': 16},
            'margin': {'all': 0},
            'alignment': 'center',
            'display_order': 1,
            'widget_group': 'Basic Layout',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Column',
        'category': 'layout',
        'flutter_widget': 'Column',
        'icon': 'view_column',
        'description': 'Arranges children widgets vertically',
        'can_have_children': True,
        'default_properties': {
            'mainAxisAlignment': 'start',
            'crossAxisAlignment': 'center',
            'mainAxisSize': 'max',
            'display_order': 2,
            'widget_group': 'Basic Layout',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Row',
        'category': 'layout',
        'flutter_widget': 'Row',
        'icon': 'view_stream',
        'description': 'Arranges children widgets horizontally',
        'can_have_children': True,
        'default_properties': {
            'mainAxisAlignment': 'start',
            'crossAxisAlignment': 'center',
            'mainAxisSize': 'max',
            'display_order': 3,
            'widget_group': 'Basic Layout',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Stack',
        'category': 'layout',
        'flutter_widget': 'Stack',
        'icon': 'layers',
        'description': 'Overlaps children widgets on top of each other',
        'can_have_children': True,
        'default_properties': {
            'alignment': 'center',
            'fit': 'loose',
            'display_order': 4,
            'widget_group': 'Basic Layout',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Center',
        'category': 'layout',
        'flutter_widget': 'Center',
        'icon': 'center_focus_weak',
        'description': 'Centers its child widget',
        'can_have_children': True,
        'max_children': 1,
        'default_properties': {
            'widthFactor': None,
            'heightFactor': None,
            'display_order': 5,
            'widget_group': 'Basic Layout',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Padding',
        'category': 'layout',
        'flutter_widget': 'Padding',
        'icon': 'space_bar',
        'description': 'Adds padding around its child widget',
        'can_have_children': True,
        'max_children': 1,
        'default_properties': {
            'padding': {'all': 16},
            'display_order': 6,
            'widget_group': 'Basic Layout',
            'show_in_builder': True,
        },
        'is_active': True,
    },

    # Display Components
    {
        'name': 'Text',
        'category': 'display',
        'flutter_widget': 'Text',
        'icon': 'text_fields',
        'description': 'Display text content with styling options',
        'can_have_children': False,
        'default_properties': {
            'text': 'Sample Text',
            'fontSize': 16,
            'color': '#000000',
            'fontWeight': 'normal',
            'textAlign': 'left',
            'maxLines': None,
            'display_order': 10,
            'widget_group': 'Basic Display',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Image',
        'category': 'display',
        'flutter_widget': 'Image',
        'icon': 'image',
        'description': 'Display images from network or assets',
        'can_have_children': False,
        'default_properties': {
            'source': 'https://via.placeholder.com/150',
            'width': 150,
            'height': 150,
            'fit': 'cover',
            'alignment': 'center',
            'display_order': 11,
            'widget_group': 'Basic Display',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Icon',
        'category': 'display',
        'flutter_widget': 'Icon',
        'icon': 'star',
        'description': 'Display Material Design icons',
        'can_have_children': False,
        'default_properties': {
            'icon': 'star',
            'size': 24,
            'color': '#000000',
            'display_order': 12,
            'widget_group': 'Basic Display',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Divider',
        'category': 'display',
        'flutter_widget': 'Divider',
        'icon': 'horizontal_rule',
        'description': 'Horizontal line to separate content',
        'can_have_children': False,
        'default_properties': {
            'height': 1,
            'thickness': 1,
            'color': '#E0E0E0',
            'indent': 0,
            'endIndent': 0,
            'display_order': 13,
            'widget_group': 'Basic Display',
            'show_in_builder': True,
        },
        'is_active': True,
    },

    # Input Components
    {
        'name': 'Button',
        'category': 'input',
        'flutter_widget': 'ElevatedButton',
        'icon': 'smart_button',
        'description': 'Material Design elevated button',
        'can_have_children': False,
        'default_properties': {
            'text': 'Button',
            'onPressed': 'null',
            'style': 'elevated',
            'color': 'primary',
            'display_order': 20,
            'widget_group': 'Input Controls',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Text Field',
        'category': 'input',
        'flutter_widget': 'TextField',
        'icon': 'input',
        'description': 'Text input field for user input',
        'can_have_children': False,
        'default_properties': {
            'hintText': 'Enter text here...',
            'labelText': 'Label',
            'obscureText': False,
            'keyboardType': 'text',
            'maxLines': 1,
            'display_order': 21,
            'widget_group': 'Input Controls',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Checkbox',
        'category': 'input',
        'flutter_widget': 'Checkbox',
        'icon': 'check_box',
        'description': 'Checkbox for boolean input',
        'can_have_children': False,
        'default_properties': {
            'value': False,
            'onChanged': 'null',
            'activeColor': '#2196F3',
            'checkColor': '#FFFFFF',
            'display_order': 22,
            'widget_group': 'Input Controls',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Switch',
        'category': 'input',
        'flutter_widget': 'Switch',
        'icon': 'toggle_on',
        'description': 'Toggle switch for boolean input',
        'can_have_children': False,
        'default_properties': {
            'value': False,
            'onChanged': 'null',
            'activeColor': '#2196F3',
            'activeTrackColor': '#81C784',
            'display_order': 23,
            'widget_group': 'Input Controls',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Slider',
        'category': 'input',
        'flutter_widget': 'Slider',
        'icon': 'tune',
        'description': 'Slider for numeric input within range',
        'can_have_children': False,
        'default_properties': {
            'value': 50,
            'min': 0,
            'max': 100,
            'divisions': 10,
            'onChanged': 'null',
            'activeColor': '#2196F3',
            'display_order': 24,
            'widget_group': 'Input Controls',
            'show_in_builder': True,
        },
        'is_active': True,
    },

    # Navigation Components
    {
        'name': 'App Bar',
        'category': 'navigation',
        'flutter_widget': 'AppBar',
        'icon': 'view_headline',
        'description': 'Material Design app bar for navigation',
        'can_have_children': False,
        'default_properties': {
            'title': 'App Title',
            'backgroundColor': '#2196F3',
            'elevation': 4,
            'centerTitle': True,
            'actions': [],
            'display_order': 30,
            'widget_group': 'Navigation',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Bottom Navigation',
        'category': 'navigation',
        'flutter_widget': 'BottomNavigationBar',
        'icon': 'menu',
        'description': 'Bottom navigation bar with multiple tabs',
        'can_have_children': False,
        'default_properties': {
            'items': [
                {'icon': 'home', 'label': 'Home'},
                {'icon': 'search', 'label': 'Search'},
                {'icon': 'person', 'label': 'Profile'},
            ],
            'currentIndex': 0,
            'onTap': 'null',
            'backgroundColor': '#FFFFFF',
            'selectedItemColor': '#2196F3',
            'display_order': 31,
            'widget_group': 'Navigation',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Tab Bar',
        'category': 'navigation',
        'flutter_widget': 'TabBar',
        'icon': 'tab',
        'description': 'Horizontal tab navigation',
        'can_have_children': False,
        'default_properties': {
            'tabs': [
                {'text': 'Tab 1'},
                {'text': 'Tab 2'},
                {'text': 'Tab 3'},
            ],
            'controller': 'null',
            'isScrollable': False,
            'indicatorColor': '#2196F3',
            'display_order': 32,
            'widget_group': 'Navigation',
            'show_in_builder': True,
        },
        'is_active': True,
    },

    # Material Design Components
    {
        'name': 'Card',
        'category': 'layout',
        'flutter_widget': 'Card',
        'icon': 'crop_landscape',
        'description': 'Material Design card container',
        'can_have_children': True,
        'max_children': 1,
        'default_properties': {
            'elevation': 2,
            'color': '#FFFFFF',
            'margin': {'all': 8},
            'shape': 'rounded',
            'display_order': 40,
            'widget_group': 'Material Design',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'List Tile',
        'category': 'display',
        'flutter_widget': 'ListTile',
        'icon': 'list',
        'description': 'Pre-built list item with title and subtitle',
        'can_have_children': False,
        'default_properties': {
            'title': 'Title',
            'subtitle': 'Subtitle',
            'leading': None,
            'trailing': None,
            'onTap': 'null',
            'dense': False,
            'display_order': 41,
            'widget_group': 'Material Design',
            'show_in_builder': True,
        },
        'is_active': True,
    },

    # Advanced Layout Components
    {
        'name': 'Expanded',
        'category': 'layout',
        'flutter_widget': 'Expanded',
        'icon': 'open_in_full',
        'description': 'Expands child to fill available space in Flex widgets',
        'can_have_children': True,
        'max_children': 1,
        'default_properties': {
            'flex': 1,
            'display_order': 50,
            'widget_group': 'Advanced Layout',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'Flexible',
        'category': 'layout',
        'flutter_widget': 'Flexible',
        'icon': 'fit_screen',
        'description': 'Gives child flexibility to occupy space in Flex widgets',
        'can_have_children': True,
        'max_children': 1,
        'default_properties': {
            'flex': 1,
            'fit': 'loose',
            'display_order': 51,
            'widget_group': 'Advanced Layout',
            'show_in_builder': True,
        },
        'is_active': True,
    },
    {
        'name': 'SizedBox',
        'category': 'layout',
        'flutter_widget': 'SizedBox',
        'icon': 'crop_din',
        'description': 'Box with specific width and height',
        'can_have_children': True,
        'max_children': 1,
        'default_properties': {
            'width': 100,
            'height': 100,
            'display_order': 52,
            'widget_group': 'Advanced Layout',
            'show_in_builder': True,
        },
        'is_active': True,
    },
]

print("Adding all Flutter component templates for Angular builder...\n")

# Add all component templates
created_count = 0
updated_count = 0

for component_data in builder_components:
    component, created = ComponentTemplate.objects.update_or_create(
        name=component_data['name'],
        category=component_data['category'],
        defaults=component_data
    )

    if created:
        print(f"✓ Created component template for {component_data['name']}")
        created_count += 1
    else:
        print(f"✓ Updated component template for {component_data['name']}")
        updated_count += 1

print(f"\n{'=' * 60}")
print(f"Total Flutter components: {len(builder_components)}")
print(f"Created: {created_count}")
print(f"Updated: {updated_count}")
print(f"{'=' * 60}")

# Verify all components
print("\nVerifying Flutter component templates...")
builder_components_in_db = ComponentTemplate.objects.filter(is_active=True).count()
print(f"Active components in database: {builder_components_in_db}")

# List all components by widget group
print("\nAvailable components organized by widget group:")
widget_groups = {}
for component in ComponentTemplate.objects.filter(is_active=True):
    props = component.default_properties or {}
    group = props.get('widget_group', 'Other')
    order = props.get('display_order', 999)

    if group not in widget_groups:
        widget_groups[group] = []
    widget_groups[group].append((component.name, order, component.icon))

# Sort and display
for group_name in sorted(widget_groups.keys()):
    print(f"\n{group_name.upper()}:")
    components = sorted(widget_groups[group_name], key=lambda x: x[1])
    for component_name, order, icon in components:
        print(f"  {order:2d}. {component_name} (icon: {icon})")

print("\n✅ All Flutter component templates have been added successfully!")
print("\nThese components are now ready for the Angular visual builder!")
print("\nNext steps:")
print("1. Backend AI: Create API endpoint to serve this organized data")
print("2. Frontend AI: Fetch and display these in Angular toolbox")
print("3. Use default_properties for Angular property panels")
print("4. Save designs to Screen.ui_structure as JSON")