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
        widget_type = widget_data.get('type')
        properties = widget_data.get('properties', {})
        children = widget_data.get('children', [])

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

    def _generate_text(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Text widget"""
        spaces = '  ' * indent
        text = self.property_mapper.map_value(properties.get('text', 'Text'))

        style_props = []
        if 'fontSize' in properties:
            style_props.append(f"fontSize: {properties['fontSize']}")
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
        if properties.get('width'):
            props.append(f"width: {properties['width']}")
        if properties.get('height'):
            props.append(f"height: {properties['height']}")

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

        # Child
        if children:
            child_code = self.generate_widget(children[0], indent + 1)
            props.append(f"child:\n{child_code}")

        if props:
            return f"{spaces}Container(\n{spaces}  {f',{chr(10)}{spaces}  '.join(props)}\n{spaces})"
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

        if 'crossAxisAlignment' in properties:
            alignment = self.property_mapper.map_cross_axis_alignment(properties['crossAxisAlignment'])
            props.append(f"crossAxisAlignment: {alignment}")

        # Children
        if children:
            children_code = []
            for child in children:
                children_code.append(self.generate_widget(child, indent + 2))
            props.append(f"children: [\n{','.join(children_code)},\n{spaces}  ]")

        return f"{spaces}Column(\n{spaces}  {f',{chr(10)}{spaces}  '.join(props)}\n{spaces})"

    def _generate_row(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Row widget"""
        spaces = '  ' * indent
        props = []

        # Alignment properties
        if 'mainAxisAlignment' in properties:
            alignment = self.property_mapper.map_main_axis_alignment(properties['mainAxisAlignment'])
            props.append(f"mainAxisAlignment: {alignment}")

        if 'crossAxisAlignment' in properties:
            alignment = self.property_mapper.map_cross_axis_alignment(properties['crossAxisAlignment'])
            props.append(f"crossAxisAlignment: {alignment}")

        # Children
        if children:
            children_code = []
            for child in children:
                children_code.append(self.generate_widget(child, indent + 2))
            props.append(f"children: [\n{','.join(children_code)},\n{spaces}  ]")

        return f"{spaces}Row(\n{spaces}  {f',{chr(10)}{spaces}  '.join(props)}\n{spaces})"

    def _generate_button(self, properties: Dict, children: List, indent: int) -> str:
        """Generate ElevatedButton widget"""
        spaces = '  ' * indent
        text = self.property_mapper.map_value(properties.get('text', 'Button'))

        on_pressed = properties.get('onPressed', 'null')
        if on_pressed == 'null':
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
                prop_strings.append(f"children: [\n{','.join(children_code)},\n{spaces}  ]")

        if prop_strings:
            return f"{spaces}{flutter_widget}(\n{spaces}  {f',{chr(10)}{spaces}  '.join(prop_strings)}\n{spaces})"
        else:
            return f"{spaces}{flutter_widget}()"

    def _generate_unknown_widget(self, widget_type: str, indent: int) -> str:
        """Fallback for unknown widget types"""
        spaces = '  ' * indent
        return f"{spaces}// TODO: Unknown widget type '{widget_type}'"