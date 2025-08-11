# management/commands/populate_builder_components.py
import json
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from builder.models import WidgetMapping
from projects.models import ComponentTemplate, WidgetTemplate, StylePreset

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate ComponentTemplate, WidgetTemplate, and StylePreset from WidgetMapping'

    def __init__(self):
        super().__init__()
        # Widget categorization mappings
        self.widget_categories = {
            'layout': [
                'container', 'column', 'row', 'stack', 'center', 'padding', 'expanded',
                'flexible', 'wrap', 'sizedbox', 'positioned', 'align', 'constrainedbox',
                'fittedbox', 'aspectratio', 'fractionallysizedbox', 'intrinsicheight',
                'intrinsicwidth', 'limitedbox', 'offstage', 'overflowbox', 'scaffold',
                'indexedstack', 'flow', 'spacer', 'table'
            ],
            'display': [
                'text', 'richtext', 'image', 'icon', 'card', 'listtile', 'chip',
                'circleavatar', 'badge', 'divider', 'placeholder', 'tooltip',
                'datatable', 'choicechip', 'filterchip', 'actionchip', 'inputchip',
                'material', 'decoratedbox', 'cliprrect', 'clipoval', 'clippath',
                'backdropfilter', 'custompaint'
            ],
            'input': [
                'button', 'textbutton', 'outlinedbutton', 'iconbutton', 'floatingactionbutton',
                'textfield', 'textformfield', 'checkbox', 'switch', 'radio', 'slider',
                'dropdown', 'rangeslider', 'popupmenubutton', 'checkboxlisttile',
                'radiolisttile', 'switchlisttile', 'form', 'fab', 'segmentedbutton'
            ],
            'navigation': [
                'appbar', 'drawer', 'bottomnavigationbar', 'tabbar', 'navigationrail',
                'navigationbar', 'sliverappbar', 'stepper', 'pageview'
            ],
            'feedback': [
                'circularprogressindicator', 'linearprogressindicator', 'snackbar',
                'alertdialog', 'bottomsheet', 'expansiontile', 'banner', 'refreshindicator'
            ],
            'scrollable': [
                'listview', 'gridview', 'singlechildscrollview', 'scrollable', 'grid',
                'customscrollview', 'nestedscrollview', 'scrollbar', 'draggablescrollablesheet'
            ],
            'animation': [
                'animatedcontainer', 'animatedopacity', 'animatedpadding', 'animatedpositioned',
                'animatedswitcher', 'hero', 'opacity', 'transform', 'visibility'
            ],
            'interaction': [
                'gesturedetector', 'inkwell', 'ignorepointer', 'absorbpointer'
            ]
        }

        # Material icon mappings
        self.widget_icons = {
            'container': 'crop_square',
            'column': 'view_column',
            'row': 'view_stream',
            'stack': 'layers',
            'center': 'center_focus_strong',
            'padding': 'format_indent_increase',
            'expanded': 'unfold_more',
            'flexible': 'aspect_ratio',
            'wrap': 'wrap_text',
            'listview': 'list',
            'gridview': 'grid_on',
            'sizedbox': 'crop_din',
            'text': 'text_fields',
            'richtext': 'text_format',
            'image': 'image',
            'icon': 'insert_emoticon',
            'circularprogressindicator': 'refresh',
            'linearprogressindicator': 'linear_scale',
            'divider': 'horizontal_rule',
            'chip': 'label',
            'button': 'smart_button',
            'textbutton': 'text_snippet',
            'outlinedbutton': 'crop_16_9',
            'iconbutton': 'touch_app',
            'floatingactionbutton': 'add_circle',
            'textfield': 'input',
            'textformfield': 'edit_note',
            'checkbox': 'check_box',
            'switch': 'toggle_on',
            'radio': 'radio_button_checked',
            'slider': 'tune',
            'dropdown': 'arrow_drop_down',
            'card': 'credit_card',
            'listtile': 'list_alt',
            'appbar': 'web_asset',
            'drawer': 'menu',
            'bottomnavigationbar': 'navigation',
            'tabbar': 'tab',
            'snackbar': 'announcement',
            'alertdialog': 'warning',
            'bottomsheet': 'vertical_align_bottom',
            'expansiontile': 'expand_more',
            'stepper': 'format_list_numbered',
            'opacity': 'opacity',
            'transform': 'transform',
            'scaffold': 'dashboard',
            'form': 'dynamic_form',
            'badge': 'verified',
            'circleavatar': 'account_circle',
            'gesturedetector': 'touch_app',
            'inkwell': 'touch_app',
            'spacer': 'space_bar',
            'positioned': 'picture_in_picture',
            'align': 'format_align_center',
            'constrainedbox': 'aspect_ratio',
            'fittedbox': 'fit_screen',
            'aspectratio': 'aspect_ratio',
            'fractionallysizedbox': 'photo_size_select_large',
            'tooltip': 'help',
            'datatable': 'table_chart',
            'scrollable': 'swap_vert',
            'singlechildscrollview': 'swap_vert',
            'grid': 'grid_view',
            'placeholder': 'crop_din',
            'visibility': 'visibility',
            'navigationrail': 'view_sidebar',
            'refreshindicator': 'refresh',
            'scrollbar': 'height',
            'material': 'layers',
            'pageview': 'view_carousel',
            'indexedstack': 'layers',
            'flow': 'view_quilt',
            'custompaint': 'brush',
            'cliprrect': 'crop_square',
            'clipoval': 'circle',
            'clippath': 'timeline',
            'backdropfilter': 'blur_on',
            'decoratedbox': 'format_paint',
            'hero': 'animation',
            'animatedcontainer': 'animation',
            'animatedopacity': 'animation',
            'animatedpadding': 'animation',
            'animatedpositioned': 'animation',
            'animatedswitcher': 'animation',
            'ignorepointer': 'block',
            'absorbpointer': 'block',
            'customscrollview': 'view_stream',
            'nestedscrollview': 'view_stream',
            'draggablescrollablesheet': 'drag_handle',
            'intrinsicheight': 'height',
            'intrinsicwidth': 'width',
            'limitedbox': 'crop_free',
            'offstage': 'visibility_off',
            'overflowbox': 'fullscreen',
            'table': 'table_chart',
            'rangeslider': 'tune',
            'popupmenubutton': 'more_vert',
            'checkboxlisttile': 'checklist',
            'radiolisttile': 'radio_button_checked',
            'switchlisttile': 'toggle_on',
            'sliverappbar': 'web_asset',
            'fab': 'add_circle',
            'choicechip': 'label',
            'filterchip': 'filter_alt',
            'actionchip': 'label',
            'inputchip': 'label',
            'banner': 'campaign',
            'navigationbar': 'navigation',
            'segmentedbutton': 'view_week'
        }

        # Widget groups for UI organization
        self.widget_groups = {
            'Basic Layout': ['container', 'column', 'row', 'stack', 'center', 'padding'],
            'Advanced Layout': ['expanded', 'flexible', 'wrap', 'positioned', 'align', 'sizedbox'],
            'Constraints': ['constrainedbox', 'fittedbox', 'aspectratio', 'fractionallysizedbox', 'limitedbox'],
            'Text & Display': ['text', 'richtext', 'icon', 'image', 'divider'],
            'Input Controls': ['textfield', 'textformfield', 'button', 'textbutton', 'outlinedbutton', 'iconbutton'],
            'Selection Controls': ['checkbox', 'switch', 'radio', 'slider', 'dropdown', 'rangeslider'],
            'Material Components': ['card', 'listtile', 'chip', 'badge', 'circleavatar'],
            'Navigation': ['appbar', 'drawer', 'bottomnavigationbar', 'tabbar', 'navigationrail'],
            'Feedback': ['circularprogressindicator', 'linearprogressindicator', 'snackbar', 'alertdialog'],
            'Scrolling': ['listview', 'gridview', 'singlechildscrollview', 'customscrollview', 'pageview'],
            'Animation': ['animatedcontainer', 'animatedopacity', 'hero', 'animatedswitcher'],
            'Interaction': ['gesturedetector', 'inkwell', 'tooltip'],
            'Advanced': ['scaffold', 'form', 'stepper', 'datatable', 'custompaint']
        }

    def handle(self, *args, **options):
        """Main command handler."""
        self.stdout.write(self.style.SUCCESS('Starting population of builder components...'))

        try:
            with transaction.atomic():
                # Get or create a default user for templates and presets
                self.default_user = self.get_or_create_default_user()

                # Process widget mappings
                widget_mappings = WidgetMapping.objects.filter(is_active=True)
                self.stdout.write(f'Found {widget_mappings.count()} active widget mappings')

                # Populate each model
                self.populate_component_templates(widget_mappings)
                self.populate_widget_templates()
                self.populate_style_presets()

                self.stdout.write(self.style.SUCCESS('Successfully populated all builder components!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            raise

    def get_or_create_default_user(self):
        """Get or create a default system user for templates."""
        user, created = User.objects.get_or_create(
            username='system_builder',
            defaults={
                'email': 'system@builder.com',
                'first_name': 'System',
                'last_name': 'Builder',
                'is_staff': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created default system user'))
        return user

    def get_widget_category(self, ui_type):
        """Determine widget category based on ui_type."""
        for category, widgets in self.widget_categories.items():
            if ui_type.lower() in widgets:
                return category
        return 'display'  # Default category

    def get_widget_group(self, ui_type):
        """Determine widget group for UI organization."""
        for group, widgets in self.widget_groups.items():
            if ui_type.lower() in widgets:
                return group
        return 'Other'

    def get_display_order(self, ui_type, category):
        """Calculate display order based on importance and category."""
        # Priority widgets get lower numbers (appear first)
        priority_widgets = {
            'container': 1, 'column': 2, 'row': 3, 'text': 4, 'button': 5,
            'textfield': 6, 'image': 7, 'card': 8, 'listview': 9, 'scaffold': 10
        }

        if ui_type.lower() in priority_widgets:
            return priority_widgets[ui_type.lower()]

        # Category-based ordering
        category_base = {
            'layout': 20, 'display': 40, 'input': 60, 'navigation': 80,
            'feedback': 100, 'scrollable': 120, 'animation': 140, 'interaction': 160
        }

        base_order = category_base.get(category, 180)
        # Add some offset within category
        return base_order + (hash(ui_type) % 20)

    def humanize_name(self, ui_type):
        """Convert ui_type to human-readable name."""
        special_cases = {
            'textfield': 'Text Field',
            'textformfield': 'Text Form Field',
            'textbutton': 'Text Button',
            'outlinedbutton': 'Outlined Button',
            'iconbutton': 'Icon Button',
            'floatingactionbutton': 'Floating Action Button',
            'fab': 'FAB',
            'listtile': 'List Tile',
            'appbar': 'App Bar',
            'bottomnavigationbar': 'Bottom Navigation Bar',
            'tabbar': 'Tab Bar',
            'snackbar': 'Snack Bar',
            'alertdialog': 'Alert Dialog',
            'bottomsheet': 'Bottom Sheet',
            'expansiontile': 'Expansion Tile',
            'sizedbox': 'Sized Box',
            'richtext': 'Rich Text',
            'circularprogressindicator': 'Circular Progress',
            'linearprogressindicator': 'Linear Progress',
            'gridview': 'Grid View',
            'listview': 'List View',
            'singlechildscrollview': 'Single Child Scroll View',
            'circleavatar': 'Circle Avatar',
            'gesturedetector': 'Gesture Detector',
            'inkwell': 'Ink Well',
            'aspectratio': 'Aspect Ratio',
            'fractionallysizedbox': 'Fractionally Sized Box',
            'constrainedbox': 'Constrained Box',
            'fittedbox': 'Fitted Box',
            'intrinsicheight': 'Intrinsic Height',
            'intrinsicwidth': 'Intrinsic Width',
            'limitedbox': 'Limited Box',
            'overflowbox': 'Overflow Box',
            'checkboxlisttile': 'Checkbox List Tile',
            'radiolisttile': 'Radio List Tile',
            'switchlisttile': 'Switch List Tile',
            'rangeslider': 'Range Slider',
            'popupmenubutton': 'Popup Menu Button',
            'navigationrail': 'Navigation Rail',
            'sliverappbar': 'Sliver App Bar',
            'choicechip': 'Choice Chip',
            'filterchip': 'Filter Chip',
            'actionchip': 'Action Chip',
            'inputchip': 'Input Chip',
            'navigationbar': 'Navigation Bar',
            'segmentedbutton': 'Segmented Button',
            'animatedcontainer': 'Animated Container',
            'animatedopacity': 'Animated Opacity',
            'animatedpadding': 'Animated Padding',
            'animatedpositioned': 'Animated Positioned',
            'animatedswitcher': 'Animated Switcher',
            'ignorepointer': 'Ignore Pointer',
            'absorbpointer': 'Absorb Pointer',
            'customscrollview': 'Custom Scroll View',
            'nestedscrollview': 'Nested Scroll View',
            'refreshindicator': 'Refresh Indicator',
            'draggablescrollablesheet': 'Draggable Scrollable Sheet',
            'pageview': 'Page View',
            'indexedstack': 'Indexed Stack',
            'custompaint': 'Custom Paint',
            'cliprrect': 'Clip RRect',
            'clipoval': 'Clip Oval',
            'clippath': 'Clip Path',
            'backdropfilter': 'Backdrop Filter',
            'decoratedbox': 'Decorated Box',
            'datatable': 'Data Table'
        }

        if ui_type.lower() in special_cases:
            return special_cases[ui_type.lower()]

        # Default: capitalize first letter
        return ui_type.capitalize()

    def generate_description(self, ui_type, flutter_widget):
        """Generate meaningful description for widget."""
        descriptions = {
            'container': 'A versatile box widget with customizable dimensions, colors, padding, and decoration',
            'column': 'Arranges children vertically in a column layout',
            'row': 'Arranges children horizontally in a row layout',
            'stack': 'Overlays children widgets on top of each other',
            'center': 'Centers its child widget within itself',
            'padding': 'Adds empty space around its child widget',
            'expanded': 'Expands child to fill available space in Row/Column',
            'flexible': 'Controls how child flexes in Row/Column',
            'wrap': 'Displays children in multiple rows or columns when space runs out',
            'listview': 'Scrollable list of widgets arranged linearly',
            'gridview': 'Scrollable grid layout for displaying items in rows and columns',
            'sizedbox': 'A box with specified width and height',
            'text': 'Displays a string of text with single style',
            'richtext': 'Display text with multiple styles and formatting',
            'image': 'Displays an image from network, asset, or file',
            'icon': 'Material Design icon widget',
            'circularprogressindicator': 'Circular loading indicator',
            'linearprogressindicator': 'Linear loading progress bar',
            'divider': 'Horizontal line to separate content',
            'chip': 'Compact element representing an attribute, text, entity, or action',
            'button': 'Elevated Material Design button',
            'textbutton': 'Flat button with text label',
            'outlinedbutton': 'Button with outlined border',
            'iconbutton': 'Clickable icon button',
            'floatingactionbutton': 'Circular floating action button',
            'textfield': 'Single-line text input field',
            'textformfield': 'Text input with form validation',
            'checkbox': 'Material Design checkbox',
            'switch': 'On/off toggle switch',
            'radio': 'Radio button for single selection',
            'slider': 'Selects value from a range by sliding',
            'dropdown': 'Dropdown menu for selecting options',
            'card': 'Material Design card with elevation',
            'listtile': 'Fixed-height row with leading, title, subtitle, and trailing',
            'appbar': 'Material Design app bar',
            'drawer': 'Slide-out navigation drawer',
            'bottomnavigationbar': 'Bottom navigation with icons and labels',
            'tabbar': 'Horizontal row of tabs',
            'snackbar': 'Brief message shown at bottom of screen',
            'alertdialog': 'Modal dialog with title, content, and actions',
            'bottomsheet': 'Sheet sliding up from bottom',
            'expansiontile': 'List tile that expands to show more content',
            'stepper': 'Displays progress through sequence of steps',
            'scaffold': 'Basic Material Design visual layout structure',
            'form': 'Container for form fields with validation',
            'badge': 'Small status descriptor for UI element',
            'circleavatar': 'Circular user avatar image',
            'gesturedetector': 'Detects gestures on child widget',
            'inkwell': 'Touch ripple effect on tap',
            'opacity': 'Makes child partially transparent',
            'transform': 'Applies transformation matrix to child',
            'visibility': 'Shows or hides child widget',
            'positioned': 'Positions child in Stack',
            'align': 'Aligns child within itself',
            'aspectratio': 'Maintains specific aspect ratio',
            'tooltip': 'Shows helpful text on long press',
            'placeholder': 'Draws a box indicating where content will be',
            'spacer': 'Creates flexible empty space',
            'singlechildscrollview': 'Makes single child scrollable',
            'pageview': 'Scrollable list that works page by page',
            'hero': 'Animates widget between routes',
            'animatedcontainer': 'Container that animates property changes',
            'rangeslider': 'Selects range of values',
            'datatable': 'Shows data in rows and columns',
            'refreshindicator': 'Pull-to-refresh functionality',
            'scrollbar': 'Shows scrollbar for scrollable widget',
            'material': 'Piece of material with elevation and color',
            'custompaint': 'Custom graphics drawn with painter'
        }

        return descriptions.get(ui_type.lower(),
                                f'{flutter_widget} widget for Flutter applications')

    def transform_properties_to_defaults(self, properties_mapping, ui_type):
        """Transform properties_mapping to default_properties with sensible defaults."""
        if not properties_mapping:
            properties_mapping = {}

        # Parse JSON if it's a string
        if isinstance(properties_mapping, str):
            try:
                properties_mapping = json.loads(properties_mapping)
            except:
                properties_mapping = {}

        defaults = {}

        # Extract property names and set defaults based on type
        for prop_name, prop_template in properties_mapping.items():
            if 'color' in prop_name.lower():
                defaults[prop_name] = 'Colors.blue'
            elif 'width' in prop_name.lower() or 'height' in prop_name.lower():
                defaults[prop_name] = 100.0
            elif 'padding' in prop_name.lower() or 'margin' in prop_name.lower():
                defaults[prop_name] = 'EdgeInsets.all(8.0)'
            elif 'text' in prop_name.lower():
                defaults[prop_name] = 'Sample Text'
            elif 'alignment' in prop_name.lower():
                defaults[prop_name] = 'Alignment.center'
            elif 'size' in prop_name.lower():
                defaults[prop_name] = 24.0
            elif prop_name in ['value', 'checked', 'selected']:
                defaults[prop_name] = False
            elif 'onPressed' in prop_name or 'onTap' in prop_name or 'onChanged' in prop_name:
                defaults[prop_name] = '() {}'
            else:
                # Keep original or set null
                defaults[prop_name] = None

        # Add UI metadata
        defaults['widget_group'] = self.get_widget_group(ui_type)
        defaults['display_order'] = self.get_display_order(ui_type, self.get_widget_category(ui_type))
        defaults['show_in_builder'] = True

        # Set common widgets to show by default, hide advanced ones
        if ui_type.lower() in ['intrinsicheight', 'intrinsicwidth', 'offstage', 'overflowbox',
                               'flow', 'custompaint', 'clippath', 'backdropfilter']:
            defaults['show_in_builder'] = False

        return defaults

    def populate_component_templates(self, widget_mappings):
        """Convert WidgetMappings to ComponentTemplates."""
        self.stdout.write('Populating ComponentTemplates...')
        created_count = 0
        updated_count = 0

        for mapping in widget_mappings:
            category = self.get_widget_category(mapping.ui_type)
            icon = self.widget_icons.get(mapping.ui_type.lower(), 'widgets')
            name = self.humanize_name(mapping.ui_type)
            description = self.generate_description(mapping.ui_type, mapping.flutter_widget)
            default_properties = self.transform_properties_to_defaults(
                mapping.properties_mapping,
                mapping.ui_type
            )

            template, created = ComponentTemplate.objects.update_or_create(
                flutter_widget=mapping.flutter_widget,
                defaults={
                    'name': name,
                    'category': category,
                    'icon': icon,
                    'description': description,
                    'default_properties': default_properties,
                    'can_have_children': mapping.can_have_children,
                    'max_children': None if mapping.can_have_children else 0,
                    'is_active': mapping.is_active
                }
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'ComponentTemplates: {created_count} created, {updated_count} updated'
            )
        )

    def populate_widget_templates(self):
        """Create common composite widget patterns."""
        self.stdout.write('Creating WidgetTemplates...')

        templates = [
            {
                'name': 'Login Form',
                'category': 'Forms',
                'description': 'Complete login form with email and password fields',
                'structure': {
                    'type': 'Container',
                    'properties': {'padding': 'EdgeInsets.all(16.0)'},
                    'children': [
                        {
                            'type': 'Column',
                            'properties': {'mainAxisAlignment': 'MainAxisAlignment.center'},
                            'children': [
                                {'type': 'Text', 'properties': {'text': 'Login',
                                                                'style': 'TextStyle(fontSize: 24, fontWeight: FontWeight.bold)'}},
                                {'type': 'SizedBox', 'properties': {'height': 20}},
                                {'type': 'TextField',
                                 'properties': {'labelText': 'Email', 'keyboardType': 'TextInputType.emailAddress'}},
                                {'type': 'SizedBox', 'properties': {'height': 16}},
                                {'type': 'TextField', 'properties': {'labelText': 'Password', 'obscureText': True}},
                                {'type': 'SizedBox', 'properties': {'height': 24}},
                                {'type': 'ElevatedButton',
                                 'properties': {'child': 'Text("Sign In")', 'onPressed': '() {}'}}
                            ]
                        }
                    ]
                },
                'tags': ['form', 'authentication', 'input']
            },
            {
                'name': 'Profile Card',
                'category': 'Cards',
                'description': 'User profile card with avatar and details',
                'structure': {
                    'type': 'Card',
                    'properties': {'elevation': 4},
                    'children': [
                        {
                            'type': 'Padding',
                            'properties': {'padding': 'EdgeInsets.all(16.0)'},
                            'children': [
                                {
                                    'type': 'Row',
                                    'children': [
                                        {'type': 'CircleAvatar',
                                         'properties': {'radius': 40, 'backgroundColor': 'Colors.blue'}},
                                        {'type': 'SizedBox', 'properties': {'width': 16}},
                                        {
                                            'type': 'Column',
                                            'properties': {'crossAxisAlignment': 'CrossAxisAlignment.start'},
                                            'children': [
                                                {'type': 'Text', 'properties': {'text': 'John Doe',
                                                                                'style': 'TextStyle(fontSize: 18, fontWeight: FontWeight.bold)'}},
                                                {'type': 'Text', 'properties': {'text': 'john.doe@example.com',
                                                                                'style': 'TextStyle(color: Colors.grey)'}}
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                'tags': ['profile', 'card', 'user']
            },
            {
                'name': 'List Item',
                'category': 'Lists',
                'description': 'Standard list item with icon, title, and subtitle',
                'structure': {
                    'type': 'ListTile',
                    'properties': {
                        'leading': 'Icon(Icons.folder)',
                        'title': 'Text("Item Title")',
                        'subtitle': 'Text("Item description")',
                        'trailing': 'Icon(Icons.arrow_forward_ios)',
                        'onTap': '() {}'
                    }
                },
                'tags': ['list', 'item', 'navigation']
            },
            {
                'name': 'Empty State',
                'category': 'States',
                'description': 'Empty state with icon, message, and action',
                'structure': {
                    'type': 'Center',
                    'children': [
                        {
                            'type': 'Column',
                            'properties': {'mainAxisAlignment': 'MainAxisAlignment.center'},
                            'children': [
                                {'type': 'Icon',
                                 'properties': {'icon': 'Icons.inbox', 'size': 64, 'color': 'Colors.grey'}},
                                {'type': 'SizedBox', 'properties': {'height': 16}},
                                {'type': 'Text', 'properties': {'text': 'No items found',
                                                                'style': 'TextStyle(fontSize: 18, color: Colors.grey)'}},
                                {'type': 'SizedBox', 'properties': {'height': 8}},
                                {'type': 'Text', 'properties': {'text': 'Try adding some items to get started',
                                                                'style': 'TextStyle(color: Colors.grey)'}},
                                {'type': 'SizedBox', 'properties': {'height': 24}},
                                {'type': 'ElevatedButton',
                                 'properties': {'child': 'Text("Add Item")', 'onPressed': '() {}'}}
                            ]
                        }
                    ]
                },
                'tags': ['empty', 'state', 'placeholder']
            },
            {
                'name': 'Loading Overlay',
                'category': 'States',
                'description': 'Full-screen loading indicator',
                'structure': {
                    'type': 'Container',
                    'properties': {'color': 'Colors.black54'},
                    'children': [
                        {
                            'type': 'Center',
                            'children': [
                                {
                                    'type': 'Card',
                                    'children': [
                                        {
                                            'type': 'Padding',
                                            'properties': {'padding': 'EdgeInsets.all(20.0)'},
                                            'children': [
                                                {
                                                    'type': 'Column',
                                                    'properties': {'mainAxisSize': 'MainAxisSize.min'},
                                                    'children': [
                                                        {'type': 'CircularProgressIndicator'},
                                                        {'type': 'SizedBox', 'properties': {'height': 16}},
                                                        {'type': 'Text', 'properties': {'text': 'Loading...'}}
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                'tags': ['loading', 'progress', 'overlay']
            },
            {
                'name': 'Settings Item',
                'category': 'Settings',
                'description': 'Settings list item with toggle',
                'structure': {
                    'type': 'SwitchListTile',
                    'properties': {
                        'title': 'Text("Enable Notifications")',
                        'subtitle': 'Text("Receive push notifications")',
                        'value': True,
                        'onChanged': '(bool value) {}'
                    }
                },
                'tags': ['settings', 'switch', 'preference']
            },
            {
                'name': 'Header Section',
                'category': 'Headers',
                'description': 'Section header with title and action',
                'structure': {
                    'type': 'Padding',
                    'properties': {'padding': 'EdgeInsets.all(16.0)'},
                    'children': [
                        {
                            'type': 'Row',
                            'properties': {'mainAxisAlignment': 'MainAxisAlignment.spaceBetween'},
                            'children': [
                                {'type': 'Text', 'properties': {'text': 'Section Title',
                                                                'style': 'TextStyle(fontSize: 20, fontWeight: FontWeight.bold)'}},
                                {'type': 'TextButton', 'properties': {'child': 'Text("See All")', 'onPressed': '() {}'}}
                            ]
                        }
                    ]
                },
                'tags': ['header', 'section', 'title']
            },
            {
                'name': 'Search Bar',
                'category': 'Input',
                'description': 'Search input with icon',
                'structure': {
                    'type': 'Container',
                    'properties': {'padding': 'EdgeInsets.symmetric(horizontal: 16.0)'},
                    'children': [
                        {
                            'type': 'TextField',
                            'properties': {
                                'decoration': 'InputDecoration(hintText: "Search...", prefixIcon: Icon(Icons.search), border: OutlineInputBorder(borderRadius: BorderRadius.circular(30.0)))'
                            }
                        }
                    ]
                },
                'tags': ['search', 'input', 'filter']
            },
            {
                'name': 'Stat Card',
                'category': 'Dashboard',
                'description': 'Dashboard statistic card',
                'structure': {
                    'type': 'Card',
                    'properties': {'elevation': 2},
                    'children': [
                        {
                            'type': 'Padding',
                            'properties': {'padding': 'EdgeInsets.all(16.0)'},
                            'children': [
                                {
                                    'type': 'Column',
                                    'properties': {'crossAxisAlignment': 'CrossAxisAlignment.start'},
                                    'children': [
                                        {
                                            'type': 'Row',
                                            'properties': {'mainAxisAlignment': 'MainAxisAlignment.spaceBetween'},
                                            'children': [
                                                {'type': 'Icon',
                                                 'properties': {'icon': 'Icons.trending_up', 'color': 'Colors.green'}},
                                                {'type': 'Text', 'properties': {'text': '+12%',
                                                                                'style': 'TextStyle(color: Colors.green)'}}
                                            ]
                                        },
                                        {'type': 'SizedBox', 'properties': {'height': 8}},
                                        {'type': 'Text', 'properties': {'text': '1,234',
                                                                        'style': 'TextStyle(fontSize: 24, fontWeight: FontWeight.bold)'}},
                                        {'type': 'Text', 'properties': {'text': 'Total Sales',
                                                                        'style': 'TextStyle(color: Colors.grey)'}}
                                    ]
                                }
                            ]
                        }
                    ]
                },
                'tags': ['dashboard', 'statistics', 'card']
            },
            {
                'name': 'Action Buttons',
                'category': 'Buttons',
                'description': 'Row of action buttons',
                'structure': {
                    'type': 'Row',
                    'properties': {'mainAxisAlignment': 'MainAxisAlignment.spaceEvenly'},
                    'children': [
                        {'type': 'OutlinedButton', 'properties': {'child': 'Text("Cancel")', 'onPressed': '() {}'}},
                        {'type': 'ElevatedButton', 'properties': {'child': 'Text("Save")', 'onPressed': '() {}'}}
                    ]
                },
                'tags': ['buttons', 'actions', 'form']
            }
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = WidgetTemplate.objects.update_or_create(
                user=self.default_user,
                name=template_data['name'],
                defaults={
                    'category': template_data['category'],
                    'description': template_data['description'],
                    'structure': template_data['structure'],
                    'is_public': True,
                    'tags': template_data['tags']
                }
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'WidgetTemplates: {created_count} created, {updated_count} updated'
            )
        )

    def populate_style_presets(self):
        """Create common style presets."""
        self.stdout.write('Creating StylePresets...')

        presets = [
            # Text Styles
            {
                'name': 'Heading 1',
                'widget_type': 'text',
                'properties': {
                    'style': 'TextStyle(fontSize: 32, fontWeight: FontWeight.bold)',
                    'textAlign': 'TextAlign.left'
                }
            },
            {
                'name': 'Heading 2',
                'widget_type': 'text',
                'properties': {
                    'style': 'TextStyle(fontSize: 24, fontWeight: FontWeight.bold)',
                    'textAlign': 'TextAlign.left'
                }
            },
            {
                'name': 'Body Text',
                'widget_type': 'text',
                'properties': {
                    'style': 'TextStyle(fontSize: 16)',
                    'textAlign': 'TextAlign.left'
                }
            },
            {
                'name': 'Caption',
                'widget_type': 'text',
                'properties': {
                    'style': 'TextStyle(fontSize: 12, color: Colors.grey)',
                    'textAlign': 'TextAlign.left'
                }
            },

            # Container Styles
            {
                'name': 'Primary Container',
                'widget_type': 'container',
                'properties': {
                    'padding': 'EdgeInsets.all(16.0)',
                    'decoration': 'BoxDecoration(color: Colors.blue, borderRadius: BorderRadius.circular(8.0))'
                }
            },
            {
                'name': 'Card Container',
                'widget_type': 'container',
                'properties': {
                    'padding': 'EdgeInsets.all(12.0)',
                    'decoration': 'BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12.0), boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 4, offset: Offset(0, 2))])'
                }
            },
            {
                'name': 'Rounded Container',
                'widget_type': 'container',
                'properties': {
                    'padding': 'EdgeInsets.all(8.0)',
                    'decoration': 'BoxDecoration(border: Border.all(color: Colors.grey), borderRadius: BorderRadius.circular(16.0))'
                }
            },

            # Button Styles
            {
                'name': 'Primary Button',
                'widget_type': 'button',
                'properties': {
                    'style': 'ElevatedButton.styleFrom(backgroundColor: Colors.blue, padding: EdgeInsets.symmetric(horizontal: 32, vertical: 16))'
                }
            },
            {
                'name': 'Secondary Button',
                'widget_type': 'button',
                'properties': {
                    'style': 'ElevatedButton.styleFrom(backgroundColor: Colors.grey, padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12))'
                }
            },
            {
                'name': 'Danger Button',
                'widget_type': 'button',
                'properties': {
                    'style': 'ElevatedButton.styleFrom(backgroundColor: Colors.red, padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12))'
                }
            },
            {
                'name': 'Success Button',
                'widget_type': 'button',
                'properties': {
                    'style': 'ElevatedButton.styleFrom(backgroundColor: Colors.green, padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12))'
                }
            },

            # Card Styles
            {
                'name': 'Elevated Card',
                'widget_type': 'card',
                'properties': {
                    'elevation': 8,
                    'shape': 'RoundedRectangleBorder(borderRadius: BorderRadius.circular(16.0))',
                    'margin': 'EdgeInsets.all(8.0)'
                }
            },
            {
                'name': 'Flat Card',
                'widget_type': 'card',
                'properties': {
                    'elevation': 0,
                    'shape': 'RoundedRectangleBorder(borderRadius: BorderRadius.circular(8.0), side: BorderSide(color: Colors.grey))',
                    'margin': 'EdgeInsets.all(4.0)'
                }
            },

            # Padding Presets
            {
                'name': 'Small Padding',
                'widget_type': 'padding',
                'properties': {
                    'padding': 'EdgeInsets.all(4.0)'
                }
            },
            {
                'name': 'Medium Padding',
                'widget_type': 'padding',
                'properties': {
                    'padding': 'EdgeInsets.all(16.0)'
                }
            },
            {
                'name': 'Large Padding',
                'widget_type': 'padding',
                'properties': {
                    'padding': 'EdgeInsets.all(32.0)'
                }
            },
            {
                'name': 'Horizontal Padding',
                'widget_type': 'padding',
                'properties': {
                    'padding': 'EdgeInsets.symmetric(horizontal: 16.0)'
                }
            },
            {
                'name': 'Vertical Padding',
                'widget_type': 'padding',
                'properties': {
                    'padding': 'EdgeInsets.symmetric(vertical: 16.0)'
                }
            },

            # TextField Styles
            {
                'name': 'Outlined Input',
                'widget_type': 'textfield',
                'properties': {
                    'decoration': 'InputDecoration(border: OutlineInputBorder(), contentPadding: EdgeInsets.all(12.0))'
                }
            },
            {
                'name': 'Filled Input',
                'widget_type': 'textfield',
                'properties': {
                    'decoration': 'InputDecoration(filled: true, fillColor: Colors.grey[200], border: InputBorder.none)'
                }
            },
            {
                'name': 'Underlined Input',
                'widget_type': 'textfield',
                'properties': {
                    'decoration': 'InputDecoration(border: UnderlineInputBorder())'
                }
            },

            # Column/Row Styles
            {
                'name': 'Centered Column',
                'widget_type': 'column',
                'properties': {
                    'mainAxisAlignment': 'MainAxisAlignment.center',
                    'crossAxisAlignment': 'CrossAxisAlignment.center'
                }
            },
            {
                'name': 'Spaced Row',
                'widget_type': 'row',
                'properties': {
                    'mainAxisAlignment': 'MainAxisAlignment.spaceBetween',
                    'crossAxisAlignment': 'CrossAxisAlignment.center'
                }
            },
            {
                'name': 'Start Aligned Column',
                'widget_type': 'column',
                'properties': {
                    'mainAxisAlignment': 'MainAxisAlignment.start',
                    'crossAxisAlignment': 'CrossAxisAlignment.start'
                }
            }
        ]

        created_count = 0
        updated_count = 0

        for preset_data in presets:
            preset, created = StylePreset.objects.update_or_create(
                user=self.default_user,
                name=preset_data['name'],
                widget_type=preset_data['widget_type'],
                defaults={
                    'properties': preset_data['properties'],
                    'is_public': True
                }
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'StylePresets: {created_count} created, {updated_count} updated'
            )
        )