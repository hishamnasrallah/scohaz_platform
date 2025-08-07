# File: builder/generators/widget_generator.py

from typing import Dict, List, Any, Set
from builder.models import WidgetMapping
from .property_mapper import PropertyMapper


class WidgetGenerator:
    """Generates Flutter widget code from UI structure"""

    def __init__(self):
        self.imports: Set[str] = set()
        self.property_mapper = PropertyMapper()

    def generate_widget(self, widget_data: Dict[str, Any], indent: int = 0) -> str:
        """Generate Flutter code for a widget"""
        if not widget_data:
            return self._generate_empty_container(indent)

        widget_type = widget_data.get('type', '')
        # NORMALIZE TO LOWERCASE for matching
        widget_type_normalized = widget_type.lower() if widget_type else ''

        properties = widget_data.get('properties', {})
        children = widget_data.get('children', [])

        # Handle navigatable widgets
        if widget_type_normalized and widget_type_normalized.startswith('navigatable_'):
            return self._generate_navigatable_widget(widget_type_normalized, properties, children, indent)

        # Check if we have a specific method for this widget type (using lowercase)
        method_name = f'_generate_{widget_type_normalized}'
        if hasattr(self, method_name):
            return getattr(self, method_name)(properties, children, indent)

        # Try to get widget mapping from database (using lowercase)
        try:
            mapping = WidgetMapping.objects.get(ui_type=widget_type_normalized, is_active=True)
            # Add imports
            if mapping.import_statements:
                for imp in mapping.import_statements.split('\n'):
                    if imp.strip():
                        self.imports.add(imp.strip())
            return self._generate_generic_widget(mapping, properties, children, indent)
        except WidgetMapping.DoesNotExist:
            pass

        # Fallback for unknown widgets
        return self._generate_unknown_widget(widget_type, indent)

    def _generate_navigatable_widget(self, widget_type: str, properties: Dict, children: List, indent: int) -> str:
        """Generate navigatable widgets with onTap/onPressed handlers"""
        spaces = '  ' * indent
        route = properties.get('route', '/')

        # Remove 'navigatable_' prefix to get base widget type
        base_type = widget_type.replace('navigatable_', '')

        if base_type == 'button':
            text = self.property_mapper.map_value(properties.get('text', 'Button'))
            return f"""{spaces}ElevatedButton(
{spaces}  onPressed: () {{
{spaces}    Navigator.pushNamed(context, '{route}');
{spaces}  }},
{spaces}  child: Text({text}),
{spaces})"""

        elif base_type == 'icon':
            icon_name = properties.get('icon', 'help')
            icon_map = {
                'star': 'Icons.star',
                'home': 'Icons.home',
                'person': 'Icons.person',
                'settings': 'Icons.settings',
                'shopping_cart': 'Icons.shopping_cart',
                'favorite': 'Icons.favorite',
                'search': 'Icons.search',
                'menu': 'Icons.menu',
                'arrow_back': 'Icons.arrow_back',
                'arrow_forward': 'Icons.arrow_forward',
            }
            flutter_icon = icon_map.get(icon_name, f'Icons.{icon_name}')

            props = []
            if 'size' in properties:
                props.append(f"iconSize: {properties['size']}.0")
            if 'color' in properties:
                color = self.property_mapper.map_color(properties['color'])
                props.append(f"color: {color}")

            props_str = f",\n{spaces}  ".join(props) if props else ""

            return f"""{spaces}IconButton(
{spaces}  icon: Icon({flutter_icon}),
{spaces}  {"" if not props_str else props_str + ","}
{spaces}  onPressed: () {{
{spaces}    Navigator.pushNamed(context, '{route}');
{spaces}  }},
{spaces})"""

        elif base_type == 'container':
            # Generate container wrapped in GestureDetector
            container_props = properties.copy()
            container_props.pop('route', None)  # Remove route from container properties

            # Generate the container
            container_widget = self._generate_container(container_props, children, indent + 1)

            return f"""{spaces}GestureDetector(
{spaces}  onTap: () {{
{spaces}    Navigator.pushNamed(context, '{route}');
{spaces}  }},
{spaces}  child: {container_widget},
{spaces})"""

        elif base_type == 'column' or base_type == 'row':
            # Generate column/row wrapped in GestureDetector
            widget_props = properties.copy()
            widget_props.pop('route', None)

            if base_type == 'column':
                inner_widget = self._generate_column(widget_props, children, indent + 1)
            else:
                inner_widget = self._generate_row(widget_props, children, indent + 1)

            return f"""{spaces}GestureDetector(
{spaces}  onTap: () {{
{spaces}    Navigator.pushNamed(context, '{route}');
{spaces}  }},
{spaces}  child: {inner_widget},
{spaces})"""

        else:
            # For any other navigatable widget, wrap in GestureDetector
            inner_widget_data = {
                'type': base_type,
                'properties': {k: v for k, v in properties.items() if k != 'route'},
                'children': children
            }
            inner_widget = self.generate_widget(inner_widget_data, indent + 1)

            return f"""{spaces}GestureDetector(
{spaces}  onTap: () {{
{spaces}    Navigator.pushNamed(context, '{route}');
{spaces}  }},
{spaces}  child: {inner_widget},
{spaces})"""

    def _generate_empty_container(self, indent: int) -> str:
        """Generate an empty container as fallback"""
        spaces = '  ' * indent
        return f"{spaces}Container()"

    def _generate_text(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Text widget"""
        spaces = '  ' * indent
        text = self.property_mapper.map_value(properties.get('text', 'Text'))

        style_props = []
        if 'fontSize' in properties:
            style_props.append(f"fontSize: {properties['fontSize']}.0")
        if 'color' in properties:
            color = self.property_mapper.map_color(properties['color'])
            if color != 'null':
                style_props.append(f"color: {color}")
        if 'fontWeight' in properties and properties['fontWeight'] != 'normal':
            style_props.append(f"fontWeight: FontWeight.{properties['fontWeight']}")

        if style_props:
            style = f"style: TextStyle({', '.join(style_props)})"
            return f"{spaces}Text({text}, {style})"
        else:
            return f"{spaces}Text({text})"

    def _generate_container(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Container widget"""
        spaces = '  ' * indent
        props = []

        # Width and Height
        if properties.get('width') is not None:
            props.append(f"width: {properties['width']}.0")
        if properties.get('height') is not None:
            props.append(f"height: {properties['height']}.0")

        # Color
        if 'color' in properties:
            color = self.property_mapper.map_color(properties['color'])
            if color != 'null':
                props.append(f"color: {color}")

        # Padding
        if 'padding' in properties and properties['padding'] is not None:
            padding = self.property_mapper.map_edge_insets(properties['padding'])
            if padding != "EdgeInsets.zero":
                props.append(f"padding: {padding}")

        # Margin
        if 'margin' in properties:
            margin = self.property_mapper.map_edge_insets(properties['margin'])
            props.append(f"margin: {margin}")

        # Alignment
        if not children or len(children) == 0:
            if 'width' not in properties and 'height' not in properties:
                props.append("width: double.infinity")
                props.append("height: double.infinity")
        else:
            props.append("alignment: Alignment.center")

        # Child
        if children and len(children) > 0:
            child_code = self.generate_widget(children[0], indent + 1)
            props.append(f"child:\n{child_code}")

        # Build the container
        if props:
            props_str = f",\n{spaces}  ".join(props)
            return f"{spaces}Container(\n{spaces}  {props_str},\n{spaces})"
        else:
            return f"{spaces}Container()"

    def _generate_column(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Column widget"""
        spaces = '  ' * indent
        props = []

        # Alignment properties
        if 'mainAxisAlignment' in properties:
            alignment = self.property_mapper.map_main_axis_alignment(properties['mainAxisAlignment'])
            props.append(f"mainAxisAlignment: {alignment}")
        else:
            props.append("mainAxisAlignment: MainAxisAlignment.start")

        if 'crossAxisAlignment' in properties:
            alignment = self.property_mapper.map_cross_axis_alignment(properties['crossAxisAlignment'])
            props.append(f"crossAxisAlignment: {alignment}")
        else:
            props.append("crossAxisAlignment: CrossAxisAlignment.center")

        # Children
        if children and len(children) > 0:
            children_code = []
            for child in children:
                children_code.append(self.generate_widget(child, indent + 2))
            children_str = ',\n'.join(children_code)
            props.append(f"children: [\n{children_str},\n{spaces}  ]")
        else:
            props.append("children: <Widget>[]")

        props_str = f",\n{spaces}  ".join(props)
        return f"{spaces}Column(\n{spaces}  {props_str},\n{spaces})"

    def _generate_row(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Row widget"""
        spaces = '  ' * indent
        props = []

        # Alignment properties
        if 'mainAxisAlignment' in properties:
            alignment = self.property_mapper.map_main_axis_alignment(properties['mainAxisAlignment'])
            props.append(f"mainAxisAlignment: {alignment}")
        else:
            props.append("mainAxisAlignment: MainAxisAlignment.start")

        if 'crossAxisAlignment' in properties:
            alignment = self.property_mapper.map_cross_axis_alignment(properties['crossAxisAlignment'])
            props.append(f"crossAxisAlignment: {alignment}")
        else:
            props.append("crossAxisAlignment: CrossAxisAlignment.center")

        # Children
        if children and len(children) > 0:
            children_code = []
            for child in children:
                children_code.append(self.generate_widget(child, indent + 2))
            children_str = ',\n'.join(children_code)
            props.append(f"children: [\n{children_str},\n{spaces}  ]")
        else:
            props.append("children: <Widget>[]")

        props_str = f",\n{spaces}  ".join(props)
        return f"{spaces}Row(\n{spaces}  {props_str},\n{spaces})"

    def _generate_button(self, properties: Dict, children: List, indent: int) -> str:
        """Generate ElevatedButton widget"""
        spaces = '  ' * indent
        text = self.property_mapper.map_value(properties.get('text', 'Button'))

        on_pressed = properties.get('onPressed', 'null')
        if on_pressed == 'null' or not on_pressed:
            on_pressed = '() {}'  # Empty function

        return f"{spaces}ElevatedButton(\n{spaces}  onPressed: {on_pressed},\n{spaces}  child: Text({text}),\n{spaces})"

    def _generate_textfield(self, properties: Dict, children: List, indent: int) -> str:
        """Generate TextField widget"""
        spaces = '  ' * indent
        decoration_props = []

        if 'hintText' in properties:
            hint = self.property_mapper.map_value(properties['hintText'])
            decoration_props.append(f"hintText: {hint}")

        if 'labelText' in properties:
            label = self.property_mapper.map_value(properties['labelText'])
            decoration_props.append(f"labelText: {label}")

        if decoration_props:
            decoration = f"decoration: InputDecoration({', '.join(decoration_props)})"
            return f"{spaces}TextField(\n{spaces}  {decoration},\n{spaces})"
        else:
            return f"{spaces}TextField()"

    def _generate_icon(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Icon widget"""
        spaces = '  ' * indent
        icon_name = properties.get('icon', 'help')

        # Map common icon names to Flutter Icons
        icon_map = {
            'star': 'Icons.star',
            'home': 'Icons.home',
            'person': 'Icons.person',
            'settings': 'Icons.settings',
            'shopping_cart': 'Icons.shopping_cart',
            'favorite': 'Icons.favorite',
            'favorite_border': 'Icons.favorite_border',
            'search': 'Icons.search',
            'menu': 'Icons.menu',
            'arrow_back': 'Icons.arrow_back',
            'arrow_forward': 'Icons.arrow_forward',
            'arrow_forward_ios': 'Icons.arrow_forward_ios',
            'check': 'Icons.check',
            'close': 'Icons.close',
            'add': 'Icons.add',
            'remove': 'Icons.remove',
            'edit': 'Icons.edit',
            'delete': 'Icons.delete',
            'share': 'Icons.share',
            'notifications': 'Icons.notifications',
            'help': 'Icons.help',
            'location_on': 'Icons.location_on',
            'phone_android': 'Icons.phone_android',
            'checkroom': 'Icons.checkroom',
            'sports_soccer': 'Icons.sports_soccer',
            'headphones': 'Icons.headphones',
            'watch': 'Icons.watch',
            'shopping_bag': 'Icons.shopping_bag',
            'payment': 'Icons.payment',
            'star_half': 'Icons.star_half',
            'add_circle_outline': 'Icons.add_circle_outline',
            'remove_circle_outline': 'Icons.remove_circle_outline',
            'format_quote': 'Icons.format_quote',
            'refresh': 'Icons.refresh',
            'directions_walk': 'Icons.directions_walk',
            'local_fire_department': 'Icons.local_fire_department',
            'pool': 'Icons.pool',
        }

        flutter_icon = icon_map.get(icon_name, f'Icons.{icon_name}')

        props = [flutter_icon]

        if 'size' in properties:
            props.append(f"size: {properties['size']}.0")

        if 'color' in properties:
            color = self.property_mapper.map_color(properties['color'])
            if color != 'null':
                props.append(f"color: {color}")

        return f"{spaces}Icon({', '.join(props)})"

    def _generate_switch(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Switch widget"""
        spaces = '  ' * indent
        value = properties.get('value', False)

        return f"{spaces}Switch(\n{spaces}  value: {str(value).lower()},\n{spaces}  onChanged: (value) {{}},\n{spaces})"

    def _generate_generic_widget(self, mapping: WidgetMapping, properties: Dict,
                                 children: List, indent: int) -> str:
        """Generate code for generic widgets using mapping"""
        spaces = '  ' * indent
        flutter_widget = mapping.flutter_widget

        # Build properties string
        prop_strings = []
        for ui_prop, flutter_prop in mapping.properties_mapping.items():
            if ui_prop in properties:
                # Check if this is a color property
                if 'color' in ui_prop.lower() or ui_prop in ['backgroundColor', 'foregroundColor', 'shadowColor']:
                    value = self.property_mapper.map_color(properties[ui_prop])
                elif ui_prop == 'scrollDirection' and 'Axis.' not in flutter_prop:
                    # Only map axis if the mapping doesn't already include Axis.
                    value = self.property_mapper.map_axis(properties[ui_prop])
                elif 'Axis.{{value}}' in flutter_prop or 'Icons.{{value}}' in flutter_prop:
                    # For mappings that already include the enum prefix, just use the raw value
                    value = properties[ui_prop]
                else:
                    value = self.property_mapper.map_value(properties[ui_prop])

                # Skip null values - don't include them in the generated code
                if value is not None:
                    prop_string = flutter_prop.replace('{{value}}', str(value))
                    prop_strings.append(prop_string)

        # Add children if any
        if children and mapping.can_have_children:
            if len(children) == 1:
                child_code = self.generate_widget(children[0], indent + 1)
                prop_strings.append(f"child:\n{child_code}")
            else:
                children_code = []
                for child in children:
                    children_code.append(self.generate_widget(child, indent + 2))
                children_str = ',\n'.join(children_code)
                prop_strings.append(f"children: [\n{children_str},\n{spaces}  ]")

        if prop_strings:
            props_str = f",\n{spaces}  ".join(prop_strings)
            return f"{spaces}{flutter_widget}(\n{spaces}  {props_str},\n{spaces})"
        else:
            return f"{spaces}{flutter_widget}()"

    # def _generate_unknown_widget(self, widget_type: str, indent: int) -> str:
    #     """Fallback for unknown widget types"""
    #     spaces = '  ' * indent
    #     return f"{spaces}Container(\n{spaces}  child: Center(\n{spaces}    child: Text('Unknown widget: {widget_type}'),\n{spaces}  ),\n{spaces})"

    # Add this method to the WidgetGenerator class if it doesn't exist
    def _generate_center(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Center widget"""
        spaces = '  ' * indent

        # Center only accepts a single child
        if children and len(children) > 0:
            child_code = self.generate_widget(children[0], indent + 1)
            return f"{spaces}Center(\n{spaces}  child:\n{child_code},\n{spaces})"
        else:
            return f"{spaces}Center()"

    def _generate_padding(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Padding widget"""
        spaces = '  ' * indent
        props = []

        # Handle padding property
        if 'padding' in properties:
            padding = self.property_mapper.map_edge_insets(properties.get('padding', {}))
            props.append(f"padding: {padding}")
        else:
            props.append("padding: EdgeInsets.zero")

        # Child
        if children and len(children) > 0:
            child_code = self.generate_widget(children[0], indent + 1)
            props.append(f"child:\n{child_code}")

        props_str = f",\n{spaces}  ".join(props)
        return f"{spaces}Padding(\n{spaces}  {props_str},\n{spaces})"

    def _generate_grid(self, properties: Dict, children: List, indent: int) -> str:
        """Generate GridView widget"""
        spaces = '  ' * indent
        props = []

        # Default crossAxisCount if not specified
        cross_axis_count = properties.get('crossAxisCount', 2)
        props.append(f"crossAxisCount: {cross_axis_count}")

        # Optional spacing
        if 'mainAxisSpacing' in properties:
            props.append(f"mainAxisSpacing: {properties['mainAxisSpacing']}.0")

        if 'crossAxisSpacing' in properties:
            props.append(f"crossAxisSpacing: {properties['crossAxisSpacing']}.0")

        # Padding
        if 'padding' in properties and properties['padding'] is not None:
            padding = self.property_mapper.map_edge_insets(properties['padding'])
            if padding != "EdgeInsets.zero":
                props.append(f"padding: {padding}")

        # Shrink wrap for nested scrollables
        props.append("shrinkWrap: true")
        props.append("physics: NeverScrollableScrollPhysics()")

        # Children
        if children and len(children) > 0:
            children_code = []
            for child in children:
                children_code.append(self.generate_widget(child, indent + 2))
            children_str = ',\n'.join(children_code)
            props.append(f"children: [\n{children_str},\n{spaces}  ]")
        else:
            props.append("children: <Widget>[]")

        props_str = f",\n{spaces}  ".join(props)
        return f"{spaces}GridView.count(\n{spaces}  {props_str},\n{spaces})"

    def _generate_scrollable(self, properties: Dict, children: List, indent: int) -> str:
        """Generate SingleChildScrollView widget"""
        spaces = '  ' * indent
        props = []

        # Scroll direction
        if 'scrollDirection' in properties:
            axis = self.property_mapper.map_axis(properties['scrollDirection'])
            props.append(f"scrollDirection: {axis}")

        # Child
        if children and len(children) > 0:
            child_code = self.generate_widget(children[0], indent + 1)
            props.append(f"child:\n{child_code}")

        if props:
            props_str = f",\n{spaces}  ".join(props)
            return f"{spaces}SingleChildScrollView(\n{spaces}  {props_str},\n{spaces})"
        else:
            return f"{spaces}SingleChildScrollView()"

    def _generate_spacer(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Spacer widget"""
        spaces = '  ' * indent

        # Check if flex is specified
        if 'flex' in properties and properties['flex'] is not None:
            flex = properties['flex']
            return f"{spaces}Spacer(flex: {flex})"
        else:
            return f"{spaces}Spacer()"



    def _generate_scaffold(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Scaffold widget"""
        spaces = '  ' * indent
        props = []

        # Background color
        if properties.get('backgroundColor'):
            color = self.property_mapper.map_color(properties['backgroundColor'])
            if color != 'null':
                props.append(f"backgroundColor: {color}")

        # AppBar
        if properties.get('appBar'):
            # Generate AppBar from properties
            app_bar_props = []

            if properties.get('title'):
                title_text = self.property_mapper.map_value(properties.get('title', 'App'))
                app_bar_props.append(f"title: Text({title_text})")

            if properties.get('appBarColor'):
                color = self.property_mapper.map_color(properties['appBarColor'])
                if color != 'null':
                    app_bar_props.append(f"backgroundColor: {color}")

            if app_bar_props:
                app_bar_str = f",\n{spaces}    ".join(app_bar_props)
                props.append(f"appBar: AppBar(\n{spaces}    {app_bar_str},\n{spaces}  )")

        # Body - handle children
        if children and len(children) > 0:
            body_code = self.generate_widget(children[0], indent + 1)
            props.append(f"body:\n{body_code}")
        else:
            # Default body if no children
            props.append("body: Center(child: Text('Empty Scaffold'))")

        # Build the scaffold
        if props:
            props_str = f",\n{spaces}  ".join(props)
            return f"{spaces}Scaffold(\n{spaces}  {props_str},\n{spaces})"
        else:
            return f"{spaces}Scaffold()"


    def _generate_appbar(self, properties: Dict, children: List, indent: int) -> str:
        """Generate AppBar widget"""
        spaces = '  ' * indent
        props = []

        # Title
        if properties.get('title'):
            title_text = self.property_mapper.map_value(properties.get('title', 'App'))
            props.append(f"title: Text({title_text})")

        # Background color
        if properties.get('backgroundColor'):
            color = self.property_mapper.map_color(properties['backgroundColor'])
            if color != 'null':
                props.append(f"backgroundColor: {color}")

        # Elevation
        if properties.get('elevation') is not None:
            props.append(f"elevation: {properties['elevation']}.0")

        # Center title
        if properties.get('centerTitle') is not None:
            props.append(f"centerTitle: {str(properties['centerTitle']).lower()}")

        # Actions
        if properties.get('actions'):
            # Handle action buttons
            action_widgets = []
            for action in properties['actions']:
                if isinstance(action, dict):
                    action_widget = self.generate_widget(action, indent + 2)
                    action_widgets.append(action_widget)

            if action_widgets:
                actions_str = ',\n'.join(action_widgets)
                props.append(f"actions: [\n{actions_str},\n{spaces}  ]")

        # Build the AppBar
        if props:
            props_str = f",\n{spaces}  ".join(props)
            return f"{spaces}AppBar(\n{spaces}  {props_str},\n{spaces})"
        else:
            return f"{spaces}AppBar()"


    def _generate_expanded(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Expanded widget"""
        spaces = '  ' * indent
        props = []

        # Flex factor
        if properties.get('flex'):
            props.append(f"flex: {properties['flex']}")

        # Child
        if children and len(children) > 0:
            child_code = self.generate_widget(children[0], indent + 1)
            props.append(f"child:\n{child_code}")

        if props:
            props_str = f",\n{spaces}  ".join(props)
            return f"{spaces}Expanded(\n{spaces}  {props_str},\n{spaces})"
        else:
            return f"{spaces}Expanded(child: Container())"


    def _generate_flexible(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Flexible widget"""
        spaces = '  ' * indent
        props = []

        # Flex factor
        if properties.get('flex'):
            props.append(f"flex: {properties['flex']}")

        # Fit
        if properties.get('fit'):
            fit_map = {
                'tight': 'FlexFit.tight',
                'loose': 'FlexFit.loose',
            }
            props.append(f"fit: {fit_map.get(properties['fit'], 'FlexFit.loose')}")

        # Child
        if children and len(children) > 0:
            child_code = self.generate_widget(children[0], indent + 1)
            props.append(f"child:\n{child_code}")

        if props:
            props_str = f",\n{spaces}  ".join(props)
            return f"{spaces}Flexible(\n{spaces}  {props_str},\n{spaces})"
        else:
            return f"{spaces}Flexible(child: Container())"


    def _generate_listview(self, properties: Dict, children: List, indent: int) -> str:
        """Generate ListView widget"""
        spaces = '  ' * indent
        props = []

        # Scroll direction
        if properties.get('scrollDirection'):
            axis = self.property_mapper.map_axis(properties['scrollDirection'])
            props.append(f"scrollDirection: {axis}")

        # Shrink wrap for nested scrollables
        props.append("shrinkWrap: true")

        # Physics
        if properties.get('physics'):
            physics_map = {
                'never': 'NeverScrollableScrollPhysics()',
                'always': 'AlwaysScrollableScrollPhysics()',
                'bouncing': 'BouncingScrollPhysics()',
                'clamping': 'ClampingScrollPhysics()',
            }
            props.append(f"physics: {physics_map.get(properties['physics'], 'AlwaysScrollableScrollPhysics()')}")

        # Padding
        if properties.get('padding'):
            padding = self.property_mapper.map_edge_insets(properties['padding'])
            props.append(f"padding: {padding}")

        # Children
        if children and len(children) > 0:
            children_code = []
            for child in children:
                children_code.append(self.generate_widget(child, indent + 2))
            children_str = ',\n'.join(children_code)
            props.append(f"children: [\n{children_str},\n{spaces}  ]")
        else:
            props.append("children: <Widget>[]")

        props_str = f",\n{spaces}  ".join(props)
        return f"{spaces}ListView(\n{spaces}  {props_str},\n{spaces})"


    def _generate_card(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Card widget"""
        spaces = '  ' * indent
        props = []

        # Elevation
        if properties.get('elevation') is not None:
            props.append(f"elevation: {properties['elevation']}.0")

        # Color
        if properties.get('color'):
            color = self.property_mapper.map_color(properties['color'])
            if color != 'null':
                props.append(f"color: {color}")

        # Shape
        if properties.get('borderRadius'):
            props.append(
                f"shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular({properties['borderRadius']}.0))")

        # Margin
        if properties.get('margin'):
            margin = self.property_mapper.map_edge_insets(properties['margin'])
            props.append(f"margin: {margin}")

        # Child
        if children and len(children) > 0:
            child_code = self.generate_widget(children[0], indent + 1)
            props.append(f"child:\n{child_code}")

        if props:
            props_str = f",\n{spaces}  ".join(props)
            return f"{spaces}Card(\n{spaces}  {props_str},\n{spaces})"
        else:
            return f"{spaces}Card()"


    def _generate_image(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Image widget"""
        spaces = '  ' * indent

        # Get image source
        source = properties.get('source', '')
        image_type = properties.get('imageType', 'network')  # network, asset, or file

        props = []

        # Width and Height
        if properties.get('width'):
            props.append(f"width: {properties['width']}.0")
        if properties.get('height'):
            props.append(f"height: {properties['height']}.0")

        # Fit
        if properties.get('fit'):
            fit_map = {
                'fill': 'BoxFit.fill',
                'contain': 'BoxFit.contain',
                'cover': 'BoxFit.cover',
                'fitWidth': 'BoxFit.fitWidth',
                'fitHeight': 'BoxFit.fitHeight',
                'none': 'BoxFit.none',
                'scaleDown': 'BoxFit.scaleDown',
            }
            props.append(f"fit: {fit_map.get(properties['fit'], 'BoxFit.contain')}")

        # Build image based on type
        if image_type == 'asset':
            image_constructor = f"Image.asset('{source}'"
        elif image_type == 'file':
            image_constructor = f"Image.file(File('{source}')"
        else:  # network
            image_constructor = f"Image.network('{source}'"

        if props:
            props_str = f", {', '.join(props)}"
            return f"{spaces}{image_constructor}{props_str})"
        else:
            return f"{spaces}{image_constructor})"


    def _generate_stack(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Stack widget"""
        spaces = '  ' * indent
        props = []

        # Alignment
        if properties.get('alignment'):
            alignment = self.property_mapper.map_alignment(properties['alignment'])
            props.append(f"alignment: {alignment}")

        # Fit
        if properties.get('fit'):
            fit_map = {
                'loose': 'StackFit.loose',
                'expand': 'StackFit.expand',
                'passthrough': 'StackFit.passthrough',
            }
            props.append(f"fit: {fit_map.get(properties['fit'], 'StackFit.loose')}")

        # Children
        if children and len(children) > 0:
            children_code = []
            for child in children:
                children_code.append(self.generate_widget(child, indent + 2))
            children_str = ',\n'.join(children_code)
            props.append(f"children: [\n{children_str},\n{spaces}  ]")
        else:
            props.append("children: <Widget>[]")

        props_str = f",\n{spaces}  ".join(props)
        return f"{spaces}Stack(\n{spaces}  {props_str},\n{spaces})"


    def _generate_positioned(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Positioned widget for use in Stack"""
        spaces = '  ' * indent
        props = []

        # Position properties
        if properties.get('top') is not None:
            props.append(f"top: {properties['top']}.0")
        if properties.get('bottom') is not None:
            props.append(f"bottom: {properties['bottom']}.0")
        if properties.get('left') is not None:
            props.append(f"left: {properties['left']}.0")
        if properties.get('right') is not None:
            props.append(f"right: {properties['right']}.0")

        # Width and Height
        if properties.get('width'):
            props.append(f"width: {properties['width']}.0")
        if properties.get('height'):
            props.append(f"height: {properties['height']}.0")

        # Child
        if children and len(children) > 0:
            child_code = self.generate_widget(children[0], indent + 1)
            props.append(f"child:\n{child_code}")

        if props:
            props_str = f",\n{spaces}  ".join(props)
            return f"{spaces}Positioned(\n{spaces}  {props_str},\n{spaces})"
        else:
            return f"{spaces}Positioned(child: Container())"

    def _generate_unknown_widget(self, widget_type: str, indent: int) -> str:
        """Fallback for unknown widget types with better error handling"""
        spaces = '  ' * indent

        # Common widget type corrections
        widget_corrections = {
            'scafold': 'scaffold',  # Common typo
            'scaffolds': 'scaffold',
            'col': 'column',
            'btn': 'button',
            'txt': 'text',
            'img': 'image',
            'list': 'listview',
        }

        # Check if it's a typo
        corrected_type = widget_corrections.get(widget_type.lower())

        if corrected_type:
            # Log the correction
            print(f"Warning: Widget type '{widget_type}' might be a typo. Did you mean '{corrected_type}'?")

            # Try to generate with the corrected type
            method_name = f'_generate_{corrected_type}'
            if hasattr(self, method_name):
                # Create a simple widget structure for the corrected type
                return getattr(self, method_name)({}, [], indent)

        # Return a more helpful error widget
        return f"""{spaces}Container(
    {spaces}  decoration: BoxDecoration(
    {spaces}    color: Colors.red[100],
    {spaces}    border: Border.all(color: Colors.red, width: 2),
    {spaces}    borderRadius: BorderRadius.circular(8),
    {spaces}  ),
    {spaces}  padding: EdgeInsets.all(16),
    {spaces}  child: Column(
    {spaces}    mainAxisSize: MainAxisSize.min,
    {spaces}    children: [
    {spaces}      Icon(Icons.error, color: Colors.red, size: 48),
    {spaces}      SizedBox(height: 8),
    {spaces}      Text(
    {spaces}        'Unknown widget: {widget_type}',
    {spaces}        style: TextStyle(
    {spaces}          color: Colors.red[900],
    {spaces}          fontWeight: FontWeight.bold,
    {spaces}        ),
    {spaces}      ),
    {spaces}      Text(
    {spaces}        'Please check the widget type',
    {spaces}        style: TextStyle(color: Colors.red[700]),
    {spaces}      ),
    {spaces}    ],
    {spaces}  ),
    {spaces})"""