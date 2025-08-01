"""Widget generation for Flutter components"""

from typing import Dict, Any, List, Set, Optional
from .property_mapper import PropertyMapper


class WidgetGenerator:
    """Generates Flutter widget code from UI component definitions"""

    def __init__(self):
        self.property_mapper = PropertyMapper()
        self.imports = set()
        self.used_translation_keys = set()

    def generate_widget(self, widget_data: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Generate Flutter widget code from widget data"""
        if not widget_data or 'type' not in widget_data:
            return 'Container()'

        widget_type = widget_data['type'].lower()
        properties = widget_data.get('properties', {})

        # Map to specific generator method
        generator_map = {
            'scaffold': self._generate_scaffold,
            'appbar': self._generate_app_bar,
            'container': self._generate_container,
            'column': self._generate_column,
            'row': self._generate_row,
            'stack': self._generate_stack,
            'text': self._generate_text,
            'button': self._generate_button,
            'elevatedbutton': self._generate_elevated_button,
            'textbutton': self._generate_text_button,
            'outlinedbutton': self._generate_outlined_button,
            'iconbutton': self._generate_icon_button,
            'image': self._generate_image,
            'icon': self._generate_icon,
            'textfield': self._generate_textfield,
            'checkbox': self._generate_checkbox,
            'switch': self._generate_switch,
            'radio': self._generate_radio,
            'slider': self._generate_slider,
            'card': self._generate_card,
            'listtile': self._generate_list_tile,
            'listview': self._generate_list_view,
            'gridview': self._generate_grid_view,
            'sizedbox': self._generate_sized_box,
            'expanded': self._generate_expanded,
            'flexible': self._generate_flexible,
            'padding': self._generate_padding,
            'center': self._generate_center,
            'align': self._generate_align,
            'positioned': self._generate_positioned,
            'divider': self._generate_divider,
            'wrap': self._generate_wrap,
            'form': self._generate_form,
            'bottomnavigationbar': self._generate_bottom_navigation_bar,
            'drawer': self._generate_drawer,
            'tabbar': self._generate_tab_bar,
        }

        generator = generator_map.get(widget_type, self._generate_unknown)
        return generator(widget_data, properties, context)

    def _generate_scaffold(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Scaffold widget"""
        parts = []

        # AppBar
        if 'appBar' in properties:
            # Check if appBar is a dict (properties) or a widget definition
            if isinstance(properties['appBar'], dict):
                # If it has a 'type' key, it's a widget definition
                if 'type' in properties['appBar']:
                    app_bar_code = self.generate_widget(properties['appBar'], context)
                else:
                    # Otherwise, it's properties for an AppBar
                    app_bar_code = self._generate_app_bar_from_properties(properties['appBar'])
            else:
                app_bar_code = 'null'
            parts.append(f'appBar: {app_bar_code}')

        # Body
        if 'body' in widget_data:
            body_code = self.generate_widget(widget_data['body'], context)
            parts.append(f'body: {body_code}')
        elif 'body' in properties:
            # Handle body in properties as well
            body_code = self.generate_widget(properties['body'], context)
            parts.append(f'body: {body_code}')

        # Drawer
        if 'drawer' in properties:
            drawer_code = self.generate_widget(properties['drawer'], context)
            parts.append(f'drawer: {drawer_code}')

        # Bottom Navigation Bar
        if 'bottomNavigationBar' in properties:
            bottom_nav_code = self.generate_widget(properties['bottomNavigationBar'], context)
            parts.append(f'bottomNavigationBar: {bottom_nav_code}')

        # Floating Action Button
        if 'floatingActionButton' in properties:
            fab_code = self._generate_floating_action_button(properties['floatingActionButton'])
            parts.append(f'floatingActionButton: {fab_code}')

        # Background color
        if 'backgroundColor' in properties:
            color = self.property_mapper.map_color(properties['backgroundColor'])
            parts.append(f'backgroundColor: {color}')

        return self._format_widget('Scaffold', parts)

    def _generate_app_bar_from_properties(self, app_bar_data: Dict) -> str:
        """Generate AppBar from properties"""
        parts = []

        # Title
        if 'title' in app_bar_data:
            if isinstance(app_bar_data['title'], dict):
                if app_bar_data['title'].get('useTranslation'):
                    key = app_bar_data['title']['translationKey']
                    self.used_translation_keys.add(key)
                    parts.append(f'title: Text(AppLocalizations.of(context)!.{key})')
                else:
                    title_widget = self.generate_widget(app_bar_data['title'])
                    parts.append(f'title: {title_widget}')
            else:
                # Simple string title
                title_text = self._escape_string(app_bar_data['title'])
                parts.append(f'title: Text({title_text})')

        # Background color
        if 'backgroundColor' in app_bar_data:
            color = self.property_mapper.map_color(app_bar_data['backgroundColor'])
            parts.append(f'backgroundColor: {color}')

        # Elevation
        if 'elevation' in app_bar_data:
            parts.append(f'elevation: {app_bar_data["elevation"]}')

        # Center title
        if 'centerTitle' in app_bar_data:
            parts.append(f'centerTitle: {str(app_bar_data["centerTitle"]).lower()}')

        # Actions
        if 'actions' in app_bar_data and isinstance(app_bar_data['actions'], list):
            action_widgets = [self.generate_widget(action) for action in app_bar_data['actions']]
            parts.append(f'actions: [{", ".join(action_widgets)}]')

        return self._format_widget('AppBar', parts)

    def _generate_container(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Container widget"""
        parts = []

        # Width and height
        if 'width' in properties:
            width = 'double.infinity' if properties['width'] == 'infinity' else properties['width']
            parts.append(f'width: {width}')

        if 'height' in properties:
            height = 'double.infinity' if properties['height'] == 'infinity' else properties['height']
            parts.append(f'height: {height}')

        # Padding
        if 'padding' in properties:
            padding = self.property_mapper.map_edge_insets(properties['padding'])
            parts.append(f'padding: {padding}')

        # Margin
        if 'margin' in properties:
            margin = self.property_mapper.map_edge_insets(properties['margin'])
            parts.append(f'margin: {margin}')

        # Alignment
        if 'alignment' in properties:
            alignment = self.property_mapper.map_alignment(properties['alignment'])
            parts.append(f'alignment: {alignment}')

        # Decoration
        if 'decoration' in properties or 'color' in properties or 'borderRadius' in properties:
            decoration_props = properties.get('decoration', {})

            # Merge color and borderRadius into decoration
            if 'color' in properties:
                decoration_props['color'] = properties['color']
            if 'borderRadius' in properties:
                decoration_props['borderRadius'] = properties['borderRadius']

            decoration = self.property_mapper.map_decoration(decoration_props)
            if decoration != 'null':
                parts.append(f'decoration: {decoration}')

        # Constraints
        if 'constraints' in properties:
            constraints = self.property_mapper.map_constraints(properties['constraints'])
            parts.append(f'constraints: {constraints}')

        # Child
        child = self._get_child_widget(widget_data, context)
        if child:
            parts.append(f'child: {child}')

        return self._format_widget('Container', parts)

    def _generate_column(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Column widget"""
        parts = []

        # Main axis alignment
        if 'mainAxisAlignment' in properties:
            alignment = self.property_mapper.map_axis_alignment(properties['mainAxisAlignment'], True)
            parts.append(f'mainAxisAlignment: {alignment}')

        # Cross axis alignment
        if 'crossAxisAlignment' in properties:
            alignment = self.property_mapper.map_axis_alignment(properties['crossAxisAlignment'], False)
            parts.append(f'crossAxisAlignment: {alignment}')

        # Main axis size
        if 'mainAxisSize' in properties:
            size = 'MainAxisSize.min' if properties['mainAxisSize'] == 'min' else 'MainAxisSize.max'
            parts.append(f'mainAxisSize: {size}')

        # Children
        children = self._generate_children(widget_data.get('children', []), context)
        if children:
            parts.append(f'children: {children}')

        return self._format_widget('Column', parts)

    def _generate_row(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Row widget"""
        parts = []

        # Main axis alignment
        if 'mainAxisAlignment' in properties:
            alignment = self.property_mapper.map_axis_alignment(properties['mainAxisAlignment'], True)
            parts.append(f'mainAxisAlignment: {alignment}')

        # Cross axis alignment
        if 'crossAxisAlignment' in properties:
            alignment = self.property_mapper.map_axis_alignment(properties['crossAxisAlignment'], False)
            parts.append(f'crossAxisAlignment: {alignment}')

        # Main axis size
        if 'mainAxisSize' in properties:
            size = 'MainAxisSize.min' if properties['mainAxisSize'] == 'min' else 'MainAxisSize.max'
            parts.append(f'mainAxisSize: {size}')

        # Children
        children = self._generate_children(widget_data.get('children', []), context)
        if children:
            parts.append(f'children: {children}')

        return self._format_widget('Row', parts)

    def _generate_stack(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Stack widget"""
        parts = []

        # Alignment
        if 'alignment' in properties:
            alignment = self.property_mapper.map_alignment(properties['alignment'])
            parts.append(f'alignment: {alignment}')

        # Fit
        if 'fit' in properties:
            fit_map = {
                'loose': 'StackFit.loose',
                'expand': 'StackFit.expand',
                'passthrough': 'StackFit.passthrough',
            }
            fit = fit_map.get(properties['fit'], 'StackFit.loose')
            parts.append(f'fit: {fit}')

        # Children
        children = self._generate_children(widget_data.get('children', []), context)
        if children:
            parts.append(f'children: {children}')

        return self._format_widget('Stack', parts)

    # In widget_generator.py, update the _generate_text method:
    def _generate_app_bar(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate AppBar widget"""
        parts = []

        # Title
        if 'title' in properties:
            if isinstance(properties['title'], dict):
                # Title is a widget
                if properties['title'].get('useTranslation'):
                    key = properties['title']['translationKey']
                    self.used_translation_keys.add(key)
                    parts.append(f'title: Text(AppLocalizations.of(context)!.{key})')
                else:
                    title_widget = self.generate_widget(properties['title'], context)
                    parts.append(f'title: {title_widget}')
            else:
                # Simple string title
                title_text = self._escape_string(properties['title'])
                parts.append(f'title: Text({title_text})')

        # Background color
        if 'backgroundColor' in properties:
            color = self.property_mapper.map_color(properties['backgroundColor'])
            parts.append(f'backgroundColor: {color}')

        # Elevation
        if 'elevation' in properties:
            parts.append(f'elevation: {properties["elevation"]}')

        # Center title
        if 'centerTitle' in properties:
            parts.append(f'centerTitle: {str(properties["centerTitle"]).lower()}')

        # Leading widget
        if 'leading' in properties:
            if isinstance(properties['leading'], dict):
                leading_widget = self.generate_widget(properties['leading'], context)
                parts.append(f'leading: {leading_widget}')
            elif isinstance(properties['leading'], str):
                # Assume it's an icon name
                icon_code = self._get_icon_code(properties['leading'])
                parts.append(f'leading: Icon({icon_code})')

        # Actions
        if 'actions' in properties and isinstance(properties['actions'], list):
            action_widgets = [self.generate_widget(action, context) for action in properties['actions']]
            parts.append(f'actions: [{", ".join(action_widgets)}]')

        # Bottom (for TabBar, etc.)
        if 'bottom' in properties:
            if isinstance(properties['bottom'], dict):
                bottom_widget = self.generate_widget(properties['bottom'], context)
                parts.append(f'bottom: {bottom_widget}')

        # Toolbar height
        if 'toolbarHeight' in properties:
            parts.append(f'toolbarHeight: {properties["toolbarHeight"]}')

        # Automatically imply leading
        if 'automaticallyImplyLeading' in properties:
            parts.append(f'automaticallyImplyLeading: {str(properties["automaticallyImplyLeading"]).lower()}')

        # Foreground color
        if 'foregroundColor' in properties:
            color = self.property_mapper.map_color(properties['foregroundColor'])
            parts.append(f'foregroundColor: {color}')

        return self._format_widget('AppBar', parts)
    def _generate_text(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Text widget with translation support"""
        # Get text content
        if properties.get('useTranslation'):
            key = properties.get('translationKey', 'undefined_key')
            self.used_translation_keys.add(key)
            text_content = f'AppLocalizations.of(context)!.{key}'
        else:
            content = properties.get('content', properties.get('text', ''))
            text_content = self._escape_string(content)

        parts = []

        # Text style
        if 'style' in properties:
            style = self.property_mapper.map_text_style(properties['style'])
            if style != 'null':
                parts.append(f'style: {style}')

        # Text align
        if 'textAlign' in properties:
            align_map = {
                'left': 'TextAlign.left',
                'right': 'TextAlign.right',
                'center': 'TextAlign.center',
                'justify': 'TextAlign.justify',
                'start': 'TextAlign.start',
                'end': 'TextAlign.end',
            }
            align = align_map.get(properties['textAlign'], 'TextAlign.start')
            parts.append(f'textAlign: {align}')

        # Max lines
        if 'maxLines' in properties:
            parts.append(f'maxLines: {properties["maxLines"]}')

        # Overflow
        if 'overflow' in properties:
            overflow_map = {
                'clip': 'TextOverflow.clip',
                'fade': 'TextOverflow.fade',
                'ellipsis': 'TextOverflow.ellipsis',
                'visible': 'TextOverflow.visible',
            }
            overflow = overflow_map.get(properties['overflow'], 'TextOverflow.ellipsis')
            parts.append(f'overflow: {overflow}')

        if parts:
            return f'Text({text_content}, {", ".join(parts)})'
        else:
            return f'Text({text_content})'

    def _generate_button(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate generic button (defaults to ElevatedButton)"""
        button_type = properties.get('buttonType', 'elevated')

        if button_type == 'text':
            return self._generate_text_button(widget_data, properties, context)
        elif button_type == 'outlined':
            return self._generate_outlined_button(widget_data, properties, context)
        else:
            return self._generate_elevated_button(widget_data, properties, context)

    def _generate_elevated_button(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate ElevatedButton widget"""
        parts = []

        # onPressed
        on_pressed = properties.get('onPressed', 'null')
        if on_pressed and on_pressed != 'null':
            parts.append(f'onPressed: () {{ /* TODO: Implement {on_pressed} */ }}')
        else:
            parts.append('onPressed: null')

        # Style
        style_parts = []
        if 'backgroundColor' in properties:
            color = self.property_mapper.map_color(properties['backgroundColor'])
            style_parts.append(f'backgroundColor: MaterialStateProperty.all({color})')

        if 'padding' in properties:
            padding = self.property_mapper.map_edge_insets(properties['padding'])
            style_parts.append(f'padding: MaterialStateProperty.all({padding})')

        if style_parts:
            parts.append(f'style: ElevatedButton.styleFrom({", ".join(style_parts)})')

        # Child
        child_text = properties.get('text', properties.get('label', 'Button'))
        child = f'Text(\'{child_text}\')'

        if 'child' in widget_data:
            child = self.generate_widget(widget_data['child'], context)

        parts.append(f'child: {child}')

        return self._format_widget('ElevatedButton', parts)

    def _generate_text_button(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate TextButton widget"""
        parts = []

        # onPressed
        on_pressed = properties.get('onPressed', 'null')
        if on_pressed and on_pressed != 'null':
            parts.append(f'onPressed: () {{ /* TODO: Implement {on_pressed} */ }}')
        else:
            parts.append('onPressed: null')

        # Child
        child_text = properties.get('text', properties.get('label', 'Button'))
        child = f'Text(\'{child_text}\')'

        if 'child' in widget_data:
            child = self.generate_widget(widget_data['child'], context)

        parts.append(f'child: {child}')

        return self._format_widget('TextButton', parts)

    def _generate_outlined_button(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate OutlinedButton widget"""
        parts = []

        # onPressed
        on_pressed = properties.get('onPressed', 'null')
        if on_pressed and on_pressed != 'null':
            parts.append(f'onPressed: () {{ /* TODO: Implement {on_pressed} */ }}')
        else:
            parts.append('onPressed: null')

        # Child
        child_text = properties.get('text', properties.get('label', 'Button'))
        child = f'Text(\'{child_text}\')'

        if 'child' in widget_data:
            child = self.generate_widget(widget_data['child'], context)

        parts.append(f'child: {child}')

        return self._format_widget('OutlinedButton', parts)

    def _generate_icon_button(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate IconButton widget"""
        parts = []

        # Icon
        icon_name = properties.get('icon', 'add')
        icon_code = self._get_icon_code(icon_name)
        parts.append(f'icon: Icon({icon_code})')

        # onPressed
        on_pressed = properties.get('onPressed', 'null')
        if on_pressed and on_pressed != 'null':
            parts.append(f'onPressed: () {{ /* TODO: Implement {on_pressed} */ }}')
        else:
            parts.append('onPressed: null')

        # Icon size
        if 'iconSize' in properties:
            parts.append(f'iconSize: {properties["iconSize"]}')

        # Color
        if 'color' in properties:
            color = self.property_mapper.map_color(properties['color'])
            parts.append(f'color: {color}')

        return self._format_widget('IconButton', parts)

    def _generate_image(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Image widget"""
        source = properties.get('source', properties.get('src', ''))

        if not source:
            return 'Container() // No image source provided'

        parts = []

        # Width and height
        if 'width' in properties:
            parts.append(f'width: {properties["width"]}')
        if 'height' in properties:
            parts.append(f'height: {properties["height"]}')

        # Fit
        if 'fit' in properties:
            fit_map = {
                'fill': 'BoxFit.fill',
                'contain': 'BoxFit.contain',
                'cover': 'BoxFit.cover',
                'fitWidth': 'BoxFit.fitWidth',
                'fitHeight': 'BoxFit.fitHeight',
                'none': 'BoxFit.none',
                'scaleDown': 'BoxFit.scaleDown',
            }
            fit = fit_map.get(properties['fit'], 'BoxFit.contain')
            parts.append(f'fit: {fit}')

        # Determine image type
        if source.startswith('http://') or source.startswith('https://'):
            return f'Image.network(\'{source}\'{", " + ", ".join(parts) if parts else ""})'
        elif source.startswith('assets/'):
            return f'Image.asset(\'{source}\'{", " + ", ".join(parts) if parts else ""})'
        else:
            # Assume it's an asset
            return f'Image.asset(\'assets/images/{source}\'{", " + ", ".join(parts) if parts else ""})'

    def _generate_icon(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Icon widget"""
        icon_name = properties.get('icon', 'help')
        icon_code = self._get_icon_code(icon_name)

        parts = []

        # Size
        if 'size' in properties:
            parts.append(f'size: {properties["size"]}')

        # Color
        if 'color' in properties:
            color = self.property_mapper.map_color(properties['color'])
            parts.append(f'color: {color}')

        if parts:
            return f'Icon({icon_code}, {", ".join(parts)})'
        else:
            return f'Icon({icon_code})'

    def _generate_textfield(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate TextField widget"""
        parts = []

        # Controller (would be defined in StatefulWidget)
        if 'controller' in properties:
            parts.append(f'controller: {properties["controller"]}Controller')

        # Decoration
        decoration_parts = []

        if 'hintText' in properties:
            decoration_parts.append(f'hintText: \'{properties["hintText"]}\'')

        if 'labelText' in properties:
            decoration_parts.append(f'labelText: \'{properties["labelText"]}\'')

        if 'prefixIcon' in properties:
            icon_code = self._get_icon_code(properties['prefixIcon'])
            decoration_parts.append(f'prefixIcon: Icon({icon_code})')

        if 'suffixIcon' in properties:
            icon_code = self._get_icon_code(properties['suffixIcon'])
            decoration_parts.append(f'suffixIcon: Icon({icon_code})')

        if 'border' in properties:
            border_type = properties['border']
            if border_type == 'outline':
                decoration_parts.append('border: OutlineInputBorder()')
            elif border_type == 'underline':
                decoration_parts.append('border: UnderlineInputBorder()')

        if decoration_parts:
            parts.append(f'decoration: InputDecoration({", ".join(decoration_parts)})')

        # Other properties
        if 'obscureText' in properties:
            parts.append(f'obscureText: {str(properties["obscureText"]).lower()}')

        if 'maxLines' in properties:
            parts.append(f'maxLines: {properties["maxLines"]}')

        if 'keyboardType' in properties:
            keyboard_map = {
                'text': 'TextInputType.text',
                'number': 'TextInputType.number',
                'email': 'TextInputType.emailAddress',
                'phone': 'TextInputType.phone',
                'multiline': 'TextInputType.multiline',
                'url': 'TextInputType.url',
            }
            keyboard = keyboard_map.get(properties['keyboardType'], 'TextInputType.text')
            parts.append(f'keyboardType: {keyboard}')

        return self._format_widget('TextField', parts)

    def _generate_checkbox(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Checkbox widget"""
        parts = []

        # Value
        value = properties.get('value', 'false')
        parts.append(f'value: {str(value).lower()}')

        # onChanged
        parts.append('onChanged: (value) { /* TODO: Handle change */ }')

        # Active color
        if 'activeColor' in properties:
            color = self.property_mapper.map_color(properties['activeColor'])
            parts.append(f'activeColor: {color}')

        return self._format_widget('Checkbox', parts)

    def _generate_switch(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Switch widget"""
        parts = []

        # Value
        value = properties.get('value', 'false')
        parts.append(f'value: {str(value).lower()}')

        # onChanged
        parts.append('onChanged: (value) { /* TODO: Handle change */ }')

        # Active color
        if 'activeColor' in properties:
            color = self.property_mapper.map_color(properties['activeColor'])
            parts.append(f'activeColor: {color}')

        return self._format_widget('Switch', parts)

    def _generate_radio(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Radio widget"""
        parts = []

        # Value and group value
        value = properties.get('value', '1')
        group_value = properties.get('groupValue', '1')

        parts.append(f'value: {value}')
        parts.append(f'groupValue: {group_value}')
        parts.append('onChanged: (value) { /* TODO: Handle change */ }')

        return self._format_widget('Radio', parts)

    def _generate_slider(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Slider widget"""
        parts = []

        # Value
        value = properties.get('value', 0.5)
        parts.append(f'value: {value}')

        # Min and max
        parts.append(f'min: {properties.get("min", 0)}')
        parts.append(f'max: {properties.get("max", 1)}')

        # onChanged
        parts.append('onChanged: (value) { /* TODO: Handle change */ }')

        # Divisions
        if 'divisions' in properties:
            parts.append(f'divisions: {properties["divisions"]}')

        # Active color
        if 'activeColor' in properties:
            color = self.property_mapper.map_color(properties['activeColor'])
            parts.append(f'activeColor: {color}')

        return self._format_widget('Slider', parts)

    def _generate_card(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Card widget"""
        parts = []

        # Elevation
        if 'elevation' in properties:
            parts.append(f'elevation: {properties["elevation"]}')

        # Color
        if 'color' in properties:
            color = self.property_mapper.map_color(properties['color'])
            parts.append(f'color: {color}')

        # Shape
        if 'borderRadius' in properties:
            radius = self.property_mapper.map_border_radius(properties['borderRadius'])
            parts.append(f'shape: RoundedRectangleBorder(borderRadius: {radius})')

        # Margin
        if 'margin' in properties:
            margin = self.property_mapper.map_edge_insets(properties['margin'])
            parts.append(f'margin: {margin}')

        # Child
        child = self._get_child_widget(widget_data, context)
        if child:
            parts.append(f'child: {child}')

        return self._format_widget('Card', parts)

    def _generate_list_tile(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate ListTile widget"""
        parts = []

        # Leading
        if 'leading' in properties:
            if isinstance(properties['leading'], str):
                # Assume it's an icon name
                icon_code = self._get_icon_code(properties['leading'])
                parts.append(f'leading: Icon({icon_code})')
            else:
                leading = self.generate_widget(properties['leading'], context)
                parts.append(f'leading: {leading}')

        # Title
        if 'title' in properties:
            if isinstance(properties['title'], str):
                parts.append(f'title: Text(\'{properties["title"]}\')')
            else:
                title = self.generate_widget(properties['title'], context)
                parts.append(f'title: {title}')

        # Subtitle
        if 'subtitle' in properties:
            if isinstance(properties['subtitle'], str):
                parts.append(f'subtitle: Text(\'{properties["subtitle"]}\')')
            else:
                subtitle = self.generate_widget(properties['subtitle'], context)
                parts.append(f'subtitle: {subtitle}')

        # Trailing
        if 'trailing' in properties:
            if isinstance(properties['trailing'], str):
                icon_code = self._get_icon_code(properties['trailing'])
                parts.append(f'trailing: Icon({icon_code})')
            else:
                trailing = self.generate_widget(properties['trailing'], context)
                parts.append(f'trailing: {trailing}')

        # onTap
        if 'onTap' in properties:
            parts.append('onTap: () { /* TODO: Handle tap */ }')

        return self._format_widget('ListTile', parts)

    def _generate_list_view(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate ListView widget"""
        children = widget_data.get('children', [])

        if not children:
            return 'ListView(children: [])'

        parts = []

        # Scroll direction
        if 'scrollDirection' in properties:
            direction = 'Axis.horizontal' if properties['scrollDirection'] == 'horizontal' else 'Axis.vertical'
            parts.append(f'scrollDirection: {direction}')

        # Padding
        if 'padding' in properties:
            padding = self.property_mapper.map_edge_insets(properties['padding'])
            parts.append(f'padding: {padding}')

        # Shrink wrap
        if 'shrinkWrap' in properties:
            parts.append(f'shrinkWrap: {str(properties["shrinkWrap"]).lower()}')

        # Physics
        if 'physics' in properties:
            physics_map = {
                'never': 'NeverScrollableScrollPhysics()',
                'bouncing': 'BouncingScrollPhysics()',
                'clamping': 'ClampingScrollPhysics()',
                'always': 'AlwaysScrollableScrollPhysics()',
            }
            physics = physics_map.get(properties['physics'], 'BouncingScrollPhysics()')
            parts.append(f'physics: {physics}')

        # Generate children or use builder
        if properties.get('itemCount'):
            # Use ListView.builder
            parts.append(f'itemCount: {properties["itemCount"]}')
            parts.append('itemBuilder: (context, index) { /* TODO: Build item */ }')
            return self._format_widget('ListView.builder', parts)
        else:
            # Use regular ListView with children
            children_code = self._generate_children(children, context)
            parts.append(f'children: {children_code}')
            return self._format_widget('ListView', parts)

    def _generate_grid_view(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate GridView widget"""
        parts = []

        # Grid delegate
        cross_axis_count = properties.get('crossAxisCount', 2)
        parts.append(f'gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: {cross_axis_count})')

        # Children
        children = self._generate_children(widget_data.get('children', []), context)
        parts.append(f'children: {children}')

        return self._format_widget('GridView', parts)

    def _generate_sized_box(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate SizedBox widget"""
        parts = []

        # Width
        if 'width' in properties:
            width = 'double.infinity' if properties['width'] == 'infinity' else properties['width']
            parts.append(f'width: {width}')

        # Height
        if 'height' in properties:
            height = 'double.infinity' if properties['height'] == 'infinity' else properties['height']
            parts.append(f'height: {height}')

        # Child
        child = self._get_child_widget(widget_data, context)
        if child:
            parts.append(f'child: {child}')

        return self._format_widget('SizedBox', parts)

    def _generate_expanded(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Expanded widget"""
        parts = []

        # Flex
        if 'flex' in properties:
            parts.append(f'flex: {properties["flex"]}')

        # Child
        child = self._get_child_widget(widget_data, context)
        if child:
            parts.append(f'child: {child}')
        else:
            parts.append('child: Container()')

        return self._format_widget('Expanded', parts)

    def _generate_flexible(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Flexible widget"""
        parts = []

        # Flex
        if 'flex' in properties:
            parts.append(f'flex: {properties["flex"]}')

        # Fit
        if 'fit' in properties:
            fit = 'FlexFit.tight' if properties['fit'] == 'tight' else 'FlexFit.loose'
            parts.append(f'fit: {fit}')

        # Child
        child = self._get_child_widget(widget_data, context)
        if child:
            parts.append(f'child: {child}')
        else:
            parts.append('child: Container()')

        return self._format_widget('Flexible', parts)

    def _generate_padding(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Padding widget"""
        parts = []

        # Padding
        padding_value = properties.get('padding', 16)
        padding = self.property_mapper.map_edge_insets(padding_value)
        parts.append(f'padding: {padding}')

        # Child
        child = self._get_child_widget(widget_data, context)
        if child:
            parts.append(f'child: {child}')
        else:
            parts.append('child: Container()')

        return self._format_widget('Padding', parts)

    def _generate_center(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Center widget"""
        child = self._get_child_widget(widget_data, context)
        if child:
            return f'Center(child: {child})'
        else:
            return 'Center(child: Container())'

    def _generate_align(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Align widget"""
        parts = []

        # Alignment
        alignment = properties.get('alignment', 'center')
        parts.append(f'alignment: {self.property_mapper.map_alignment(alignment)}')

        # Child
        child = self._get_child_widget(widget_data, context)
        if child:
            parts.append(f'child: {child}')

        return self._format_widget('Align', parts)

    def _generate_positioned(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Positioned widget"""
        parts = []

        # Position properties
        for prop in ['left', 'top', 'right', 'bottom', 'width', 'height']:
            if prop in properties:
                parts.append(f'{prop}: {properties[prop]}')

        # Child
        child = self._get_child_widget(widget_data, context)
        if child:
            parts.append(f'child: {child}')

        return self._format_widget('Positioned', parts)

    def _generate_divider(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Divider widget"""
        parts = []

        # Height
        if 'height' in properties:
            parts.append(f'height: {properties["height"]}')

        # Thickness
        if 'thickness' in properties:
            parts.append(f'thickness: {properties["thickness"]}')

        # Color
        if 'color' in properties:
            color = self.property_mapper.map_color(properties['color'])
            parts.append(f'color: {color}')

        # Indent
        if 'indent' in properties:
            parts.append(f'indent: {properties["indent"]}')

        if 'endIndent' in properties:
            parts.append(f'endIndent: {properties["endIndent"]}')

        return self._format_widget('Divider', parts)

    def _generate_wrap(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Wrap widget"""
        parts = []

        # Direction
        if 'direction' in properties:
            direction = 'Axis.vertical' if properties['direction'] == 'vertical' else 'Axis.horizontal'
            parts.append(f'direction: {direction}')

        # Alignment
        if 'alignment' in properties:
            align_map = {
                'start': 'WrapAlignment.start',
                'end': 'WrapAlignment.end',
                'center': 'WrapAlignment.center',
                'spaceBetween': 'WrapAlignment.spaceBetween',
                'spaceAround': 'WrapAlignment.spaceAround',
                'spaceEvenly': 'WrapAlignment.spaceEvenly',
            }
            alignment = align_map.get(properties['alignment'], 'WrapAlignment.start')
            parts.append(f'alignment: {alignment}')

        # Spacing
        if 'spacing' in properties:
            parts.append(f'spacing: {properties["spacing"]}')

        if 'runSpacing' in properties:
            parts.append(f'runSpacing: {properties["runSpacing"]}')

        # Children
        children = self._generate_children(widget_data.get('children', []), context)
        parts.append(f'children: {children}')

        return self._format_widget('Wrap', parts)

    def _generate_form(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Form widget"""
        parts = []

        # Key (would be defined in StatefulWidget)
        if properties.get('key'):
            parts.append('key: _formKey')

        # Child
        child = self._get_child_widget(widget_data, context)
        if child:
            parts.append(f'child: {child}')

        return self._format_widget('Form', parts)

    def _generate_bottom_navigation_bar(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate BottomNavigationBar widget"""
        parts = []

        # Current index
        parts.append(f'currentIndex: {properties.get("currentIndex", 0)}')

        # onTap
        parts.append('onTap: (index) { /* TODO: Handle navigation */ }')

        # Items
        items = properties.get('items', [])
        if items:
            item_widgets = []
            for item in items:
                icon_code = self._get_icon_code(item.get('icon', 'home'))
                label = item.get('label', 'Tab')
                item_widgets.append(f'BottomNavigationBarItem(icon: Icon({icon_code}), label: \'{label}\')')
            parts.append(f'items: [{", ".join(item_widgets)}]')
        else:
            # Default items
            parts.append('items: [BottomNavigationBarItem(icon: Icon(Icons.home), label: \'Home\'), BottomNavigationBarItem(icon: Icon(Icons.settings), label: \'Settings\')]')

        return self._format_widget('BottomNavigationBar', parts)

    def _generate_drawer(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate Drawer widget"""
        child = self._get_child_widget(widget_data, context)
        if not child:
            # Default drawer content
            child = '''ListView(
      padding: EdgeInsets.zero,
      children: [
        const DrawerHeader(
          decoration: BoxDecoration(color: Colors.blue),
          child: Text('Drawer Header', style: TextStyle(color: Colors.white, fontSize: 24)),
        ),
        ListTile(
          leading: const Icon(Icons.home),
          title: const Text('Home'),
          onTap: () { /* TODO: Handle navigation */ },
        ),
      ],
    )'''

        return f'Drawer(child: {child})'

    def _generate_tab_bar(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate TabBar widget"""
        parts = []

        # Tabs
        tabs = properties.get('tabs', [])
        if tabs:
            tab_widgets = []
            for tab in tabs:
                if isinstance(tab, str):
                    tab_widgets.append(f'Tab(text: \'{tab}\')')
                elif isinstance(tab, dict):
                    text = tab.get('text', '')
                    icon = tab.get('icon')
                    if icon:
                        icon_code = self._get_icon_code(icon)
                        tab_widgets.append(f'Tab(text: \'{text}\', icon: Icon({icon_code}))')
                    else:
                        tab_widgets.append(f'Tab(text: \'{text}\')')
            parts.append(f'tabs: [{", ".join(tab_widgets)}]')

        return self._format_widget('TabBar', parts)

    def _generate_floating_action_button(self, fab_data: Dict) -> str:
        """Generate FloatingActionButton"""
        parts = []

        # onPressed
        parts.append('onPressed: () { /* TODO: Handle FAB press */ }')

        # Child (icon or text)
        if 'icon' in fab_data:
            icon_code = self._get_icon_code(fab_data['icon'])
            parts.append(f'child: Icon({icon_code})')
        elif 'text' in fab_data:
            parts.append(f'child: Text(\'{fab_data["text"]}\')')
        else:
            parts.append('child: Icon(Icons.add)')

        # Background color
        if 'backgroundColor' in fab_data:
            color = self.property_mapper.map_color(fab_data['backgroundColor'])
            parts.append(f'backgroundColor: {color}')

        return self._format_widget('FloatingActionButton', parts)

    def _generate_unknown(self, widget_data: Dict, properties: Dict, context: Dict) -> str:
        """Generate placeholder for unknown widgets"""
        widget_type = widget_data.get('type', 'unknown')
        return f'Container() // TODO: Implement {widget_type} widget'

    def _generate_children(self, children: List[Dict], context: Dict) -> str:
        """Generate list of child widgets"""
        if not children:
            return '[]'

        child_widgets = []
        for child in children:
            widget_code = self.generate_widget(child, context)
            child_widgets.append(widget_code)

        return f'[{", ".join(child_widgets)}]'

    def _get_child_widget(self, widget_data: Dict, context: Dict) -> Optional[str]:
        """Get single child widget from widget data"""
        if 'child' in widget_data:
            return self.generate_widget(widget_data['child'], context)

        if 'children' in widget_data:
            children = widget_data['children']
            if len(children) == 1:
                return self.generate_widget(children[0], context)
            elif len(children) > 1:
                # Wrap multiple children in Column
                return self.generate_widget({
                    'type': 'column',
                    'children': children
                }, context)

        return None

    def _format_widget(self, widget_name: str, properties: List[str]) -> str:
        """Format widget with properties"""
        if not properties:
            return f'{widget_name}()'

        if len(properties) == 1:
            return f'{widget_name}({properties[0]})'

        # Multi-line format for better readability
        props_str = ',\n      '.join(properties)
        return f'''{widget_name}(
      {props_str},
    )'''

    def _escape_string(self, text: str) -> str:
        """Escape string for Dart code"""
        if not text:
            return "''"

        # Escape single quotes and backslashes
        escaped = text.replace('\\', '\\\\').replace("'", "\\'")
        return f"'{escaped}'"

    def _get_icon_code(self, icon_name: str) -> str:
        """Get Flutter Icons code from icon name"""
        # Map common icon names to Flutter Icons
        icon_map = {
            'home': 'Icons.home',
            'settings': 'Icons.settings',
            'person': 'Icons.person',
            'search': 'Icons.search',
            'menu': 'Icons.menu',
            'add': 'Icons.add',
            'edit': 'Icons.edit',
            'delete': 'Icons.delete',
            'save': 'Icons.save',
            'close': 'Icons.close',
            'back': 'Icons.arrow_back',
            'forward': 'Icons.arrow_forward',
            'up': 'Icons.arrow_upward',
            'down': 'Icons.arrow_downward',
            'email': 'Icons.email',
            'phone': 'Icons.phone',
            'calendar': 'Icons.calendar_today',
            'location': 'Icons.location_on',
            'star': 'Icons.star',
            'favorite': 'Icons.favorite',
            'share': 'Icons.share',
            'info': 'Icons.info',
            'warning': 'Icons.warning',
            'error': 'Icons.error',
            'check': 'Icons.check',
            'checkbox': 'Icons.check_box',
            'radio': 'Icons.radio_button_checked',
        }

        return icon_map.get(icon_name.lower(), f'Icons.{icon_name}')

    def get_required_imports(self) -> Set[str]:
        """Get all required imports for generated widgets"""
        return self.imports

    def get_used_translation_keys(self) -> Set[str]:
        """Get all translation keys used in widgets"""
        return self.used_translation_keys