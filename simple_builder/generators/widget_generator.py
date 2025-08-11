from typing import Dict, List, Any, Set
from simple_builder.models import WidgetMapping
from .property_mapper import PropertyMapper


class WidgetGenerator:
    """Simplified Flutter widget code generator"""

    def __init__(self):
        self.imports: Set[str] = set()
        self.property_mapper = PropertyMapper()

    def generate_widget(self, widget_data: Dict[str, Any], indent: int = 0) -> str:
        """Generate Flutter code for a widget"""
        if not widget_data:
            return self._generate_empty_container(indent)

        widget_type = widget_data.get('type', '').lower()
        properties = widget_data.get('properties', {})
        children = widget_data.get('children', [])

        # Check for specific generator methods
        method_name = f'_generate_{widget_type}'
        if hasattr(self, method_name):
            return getattr(self, method_name)(properties, children, indent)

        # Try widget mapping from database
        try:
            mapping = WidgetMapping.objects.get(ui_type=widget_type, is_active=True)
            if mapping.import_statements:
                for imp in mapping.import_statements.split('\n'):
                    if imp.strip():
                        self.imports.add(imp.strip())
            return self._generate_generic_widget(mapping, properties, children, indent)
        except WidgetMapping.DoesNotExist:
            return self._generate_unknown_widget(widget_type, indent)

    def _generate_empty_container(self, indent: int) -> str:
        spaces = '  ' * indent
        return f"{spaces}Container()"

    def _generate_text(self, properties: Dict, children: List, indent: int) -> str:
        spaces = '  ' * indent
        text = self.property_mapper.map_value(properties.get('text', 'Text'))

        style_props = []
        if 'fontSize' in properties:
            style_props.append(f"fontSize: {properties['fontSize']}.0")
        if 'color' in properties:
            color = self.property_mapper.map_color(properties['color'])
            if color != 'null':
                style_props.append(f"color: {color}")
        if 'fontWeight' in properties:
            weight = self.property_mapper.map_font_weight(properties['fontWeight'])
            style_props.append(f"fontWeight: {weight}")

        if style_props:
            style = f"style: TextStyle({', '.join(style_props)})"
            return f"{spaces}Text({text}, {style})"
        else:
            return f"{spaces}Text({text})"

    def _generate_container(self, properties: Dict, children: List, indent: int) -> str:
        spaces = '  ' * indent
        props = []

        if properties.get('width') is not None:
            props.append(f"width: {properties['width']}.0")
        if properties.get('height') is not None:
            props.append(f"height: {properties['height']}.0")

        if 'color' in properties:
            color = self.property_mapper.map_color(properties['color'])
            if color != 'null':
                props.append(f"color: {color}")

        if 'padding' in properties:
            padding = self.property_mapper.map_edge_insets(properties['padding'])
            props.append(f"padding: {padding}")

        if 'margin' in properties:
            margin = self.property_mapper.map_edge_insets(properties['margin'])
            props.append(f"margin: {margin}")

        if 'alignment' in properties:
            alignment = self.property_mapper.map_alignment(properties['alignment'])
            props.append(f"alignment: {alignment}")

        if children and len(children) > 0:
            child_code = self.generate_widget(children[0], indent + 1)
            props.append(f"child:\n{child_code}")

        if props:
            props_str = f",\n{spaces}  ".join(props)
            return f"{spaces}Container(\n{spaces}  {props_str},\n{spaces})"
        else:
            return f"{spaces}Container()"

    def _generate_column(self, properties: Dict, children: List, indent: int) -> str:
        spaces = '  ' * indent
        props = []

        if 'mainAxisAlignment' in properties:
            alignment = self.property_mapper.map_main_axis_alignment(properties['mainAxisAlignment'])
            props.append(f"mainAxisAlignment: {alignment}")

        if 'crossAxisAlignment' in properties:
            alignment = self.property_mapper.map_cross_axis_alignment(properties['crossAxisAlignment'])
            props.append(f"crossAxisAlignment: {alignment}")

        if children:
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
        spaces = '  ' * indent
        props = []

        if 'mainAxisAlignment' in properties:
            alignment = self.property_mapper.map_main_axis_alignment(properties['mainAxisAlignment'])
            props.append(f"mainAxisAlignment: {alignment}")

        if 'crossAxisAlignment' in properties:
            alignment = self.property_mapper.map_cross_axis_alignment(properties['crossAxisAlignment'])
            props.append(f"crossAxisAlignment: {alignment}")

        if children:
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
        spaces = '  ' * indent
        text = self.property_mapper.map_value(properties.get('text', 'Button'))
        on_pressed = properties.get('onPressed', '() {}')

        return f"{spaces}ElevatedButton(\n{spaces}  onPressed: {on_pressed},\n{spaces}  child: Text({text}),\n{spaces})"

    def _generate_textfield(self, properties: Dict, children: List, indent: int) -> str:
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
        spaces = '  ' * indent
        icon_name = properties.get('icon', 'help')
        props = [f"Icons.{icon_name}"]

        if 'size' in properties:
            props.append(f"size: {properties['size']}.0")

        if 'color' in properties:
            color = self.property_mapper.map_color(properties['color'])
            if color != 'null':
                props.append(f"color: {color}")

        return f"{spaces}Icon({', '.join(props)})"

    def _generate_image(self, properties: Dict, children: List, indent: int) -> str:
        spaces = '  ' * indent
        source = properties.get('source', '')
        props = []

        if properties.get('width'):
            props.append(f"width: {properties['width']}.0")
        if properties.get('height'):
            props.append(f"height: {properties['height']}.0")

        if properties.get('fit'):
            fit = self.property_mapper.map_box_fit(properties['fit'])
            props.append(f"fit: {fit}")

        image_constructor = f"Image.network('{source}'"

        if props:
            props_str = f", {', '.join(props)}"
            return f"{spaces}{image_constructor}{props_str})"
        else:
            return f"{spaces}{image_constructor})"

    def _generate_stack(self, properties: Dict, children: List, indent: int) -> str:
        spaces = '  ' * indent
        props = []

        if 'alignment' in properties:
            alignment = self.property_mapper.map_alignment(properties['alignment'])
            props.append(f"alignment: {alignment}")

        if children:
            children_code = []
            for child in children:
                children_code.append(self.generate_widget(child, indent + 2))
            children_str = ',\n'.join(children_code)
            props.append(f"children: [\n{children_str},\n{spaces}  ]")
        else:
            props.append("children: <Widget>[]")

        props_str = f",\n{spaces}  ".join(props)
        return f"{spaces}Stack(\n{spaces}  {props_str},\n{spaces})"

    def _generate_scaffold(self, properties: Dict, children: List, indent: int) -> str:
        spaces = '  ' * indent
        props = []

        if properties.get('backgroundColor'):
            color = self.property_mapper.map_color(properties['backgroundColor'])
            if color != 'null':
                props.append(f"backgroundColor: {color}")

        if children and len(children) > 0:
            body_code = self.generate_widget(children[0], indent + 1)
            props.append(f"body:\n{body_code}")
        else:
            props.append("body: Center(child: Text('Empty Scaffold'))")

        if props:
            props_str = f",\n{spaces}  ".join(props)
            return f"{spaces}Scaffold(\n{spaces}  {props_str},\n{spaces})"
        else:
            return f"{spaces}Scaffold()"

    def _generate_appbar(self, properties: Dict, children: List, indent: int) -> str:
        spaces = '  ' * indent
        props = []

        if properties.get('title'):
            title_text = self.property_mapper.map_value(properties.get('title', 'App'))
            props.append(f"title: Text({title_text})")

        if properties.get('backgroundColor'):
            color = self.property_mapper.map_color(properties['backgroundColor'])
            if color != 'null':
                props.append(f"backgroundColor: {color}")

        if properties.get('elevation') is not None:
            props.append(f"elevation: {properties['elevation']}.0")

        if props:
            props_str = f",\n{spaces}  ".join(props)
            return f"{spaces}AppBar(\n{spaces}  {props_str},\n{spaces})"
        else:
            return f"{spaces}AppBar()"

    def _generate_generic_widget(self, mapping: WidgetMapping, properties: Dict,
                                 children: List, indent: int) -> str:
        """Generate code for generic widgets using mapping"""
        spaces = '  ' * indent
        flutter_widget = mapping.flutter_widget

        prop_strings = []
        for ui_prop, flutter_prop in mapping.properties_mapping.items():
            if ui_prop in properties:
                value = self.property_mapper.map_value(properties[ui_prop])
                if value is not None:
                    prop_string = flutter_prop.replace('{{value}}', str(value))
                    prop_strings.append(prop_string)

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
        return f"{spaces}Container(\n{spaces}  child: Text('Unknown widget: {widget_type}'),\n{spaces})"

    def _generate_checkbox(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Checkbox widget"""
        spaces = '  ' * indent
        value = properties.get('value', False)

        # Checkbox REQUIRES onChanged callback
        return f"{spaces}Checkbox(\n{spaces}  value: {str(value).lower()},\n{spaces}  onChanged: (value) {{}},\n{spaces})"

    def _generate_switch(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Switch widget"""
        spaces = '  ' * indent
        value = properties.get('value', False)

        # Switch REQUIRES onChanged callback
        return f"{spaces}Switch(\n{spaces}  value: {str(value).lower()},\n{spaces}  onChanged: (value) {{}},\n{spaces})"

    def _generate_listview(self, properties: Dict, children: List, indent: int) -> str:
        """Generate ListView widget"""
        spaces = '  ' * indent
        props = []

        # Scroll direction
        if properties.get('scrollDirection'):
            axis = self.property_mapper.map_axis(properties['scrollDirection'])
            props.append(f"scrollDirection: {axis}")

        # Shrink wrap for nested scrollables
        if properties.get('shrinkWrap'):
            props.append(f"shrinkWrap: {str(properties['shrinkWrap']).lower()}")
        else:
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

        # Padding - handle null value
        if properties.get('padding') is not None:
            padding = self.property_mapper.map_edge_insets(properties['padding'])
            if padding != "null":
                props.append(f"padding: {padding}")

        # Children - ListView uses children, not child
        if children:
            children_code = []
            for child in children:
                children_code.append(self.generate_widget(child, indent + 2))
            children_str = ',\n'.join(children_code)
            props.append(f"children: [\n{children_str},\n{spaces}  ]")
        else:
            props.append("children: const <Widget>[]")

        props_str = f",\n{spaces}  ".join(props)
        return f"{spaces}ListView(\n{spaces}  {props_str},\n{spaces})"

    def _generate_listtile(self, properties: Dict, children: List, indent: int) -> str:
        """Generate ListTile widget"""
        spaces = '  ' * indent
        props = []

        if properties.get('title'):
            title_text = self.property_mapper.map_value(properties['title'])
            props.append(f"title: Text({title_text})")

        if properties.get('subtitle'):
            subtitle_text = self.property_mapper.map_value(properties['subtitle'])
            props.append(f"subtitle: Text({subtitle_text})")

        if properties.get('onTap'):
            props.append(f"onTap: () {{}}")

        if props:
            props_str = f",\n{spaces}  ".join(props)
            return f"{spaces}ListTile(\n{spaces}  {props_str},\n{spaces})"
        else:
            return f"{spaces}ListTile()"

    def _generate_divider(self, properties: Dict, children: List, indent: int) -> str:
        """Generate Divider widget"""
        spaces = '  ' * indent
        props = []

        if properties.get('height'):
            props.append(f"height: {properties['height']}.0")

        if properties.get('thickness'):
            props.append(f"thickness: {properties['thickness']}.0")

        if properties.get('color'):
            color = self.property_mapper.map_color(properties['color'])
            if color != 'null':
                props.append(f"color: {color}")

        if props:
            props_str = f",\n{spaces}  ".join(props)
            return f"{spaces}Divider(\n{spaces}  {props_str},\n{spaces})"
        else:
            return f"{spaces}Divider()"