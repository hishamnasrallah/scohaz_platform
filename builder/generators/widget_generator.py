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

        widget_type = widget_data.get('type')
        properties = widget_data.get('properties', {})
        children = widget_data.get('children', [])

        # Handle navigatable widgets
        if widget_type and widget_type.startswith('navigatable_'):
            return self._generate_navigatable_widget(widget_type, properties, children, indent)

        # Get widget mapping
        try:
            mapping = WidgetMapping.objects.get(ui_type=widget_type, is_active=True)
        except WidgetMapping.DoesNotExist:
            # Fallback for unknown widgets
            return self._generate_unknown_widget(widget_type, indent)

        # Add imports
        if mapping.import_statements:
            for imp in mapping.import_statements.split('\n'):
                if imp.strip():
                    self.imports.add(imp.strip())

        # Generate widget based on type
        method_name = f'_generate_{widget_type}'
        if hasattr(self, method_name):
            return getattr(self, method_name)(properties, children, indent)
        else:
            return self._generate_generic_widget(mapping, properties, children, indent)

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
        if 'padding' in properties:
            padding = self.property_mapper.map_edge_insets(properties['padding'])
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
                value = self.property_mapper.map_value(properties[ui_prop])
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

    def _generate_unknown_widget(self, widget_type: str, indent: int) -> str:
        """Fallback for unknown widget types"""
        spaces = '  ' * indent
        return f"{spaces}Container(\n{spaces}  child: Center(\n{spaces}    child: Text('Unknown widget: {widget_type}'),\n{spaces}  ),\n{spaces})"