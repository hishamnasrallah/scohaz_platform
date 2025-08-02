"""Property mapping utilities for converting UI properties to Flutter properties"""

from typing import Dict, Any, Union, List
import re


class PropertyMapper:
    """Maps UI component properties to Flutter widget properties"""

    @staticmethod
    def map_color(color: str) -> str:
        """Convert color values to Flutter Color format"""
        if not color:
            return 'null'

        # Handle null string
        if color.lower() == 'null' or color.lower() == 'none':
            return 'null'

        # Handle hex colors
        if color.startswith('#'):
            hex_color = color[1:].upper()
            # Ensure 6 digit hex
            if len(hex_color) == 3:
                hex_color = ''.join([c*2 for c in hex_color])
            return f'Color(0xFF{hex_color})'

        # Handle RGB/RGBA
        rgb_match = re.match(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', color)
        if rgb_match:
            r, g, b = rgb_match.groups()
            return f'Color.fromRGBO({r}, {g}, {b}, 1.0)'

        # Handle named colors
        color_map = {
            'primary': 'Theme.of(context).primaryColor',
            'accent': 'Theme.of(context).colorScheme.secondary',
            'error': 'Theme.of(context).colorScheme.error',
            'white': 'Colors.white',
            'black': 'Colors.black',
            'red': 'Colors.red',
            'blue': 'Colors.blue',
            'green': 'Colors.green',
            'yellow': 'Colors.yellow',
            'orange': 'Colors.orange',
            'purple': 'Colors.purple',
            'pink': 'Colors.pink',
            'grey': 'Colors.grey',
            'gray': 'Colors.grey',
            'transparent': 'Colors.transparent',
        }

        return color_map.get(color.lower(), 'Colors.black')

    @staticmethod
    def map_alignment(alignment: str) -> str:
        """Convert alignment values to Flutter Alignment"""
        alignment_map = {
            'center': 'Alignment.center',
            'topLeft': 'Alignment.topLeft',
            'topCenter': 'Alignment.topCenter',
            'topRight': 'Alignment.topRight',
            'centerLeft': 'Alignment.centerLeft',
            'centerRight': 'Alignment.centerRight',
            'bottomLeft': 'Alignment.bottomLeft',
            'bottomCenter': 'Alignment.bottomCenter',
            'bottomRight': 'Alignment.bottomRight',
            'top': 'Alignment.topCenter',
            'bottom': 'Alignment.bottomCenter',
            'left': 'Alignment.centerLeft',
            'right': 'Alignment.centerRight',
        }
        return alignment_map.get(alignment, 'Alignment.center')

    @staticmethod
    def map_edge_insets(padding: Union[int, float, Dict, str]) -> str:
        """Convert padding values to EdgeInsets"""
        if isinstance(padding, (int, float)):
            return f'EdgeInsets.all({padding})'

        if isinstance(padding, str):
            # Handle string format like "16" or "16,16,16,16"
            parts = padding.replace(' ', '').split(',')
            if len(parts) == 1:
                return f'EdgeInsets.all({parts[0]})'
            elif len(parts) == 2:
                return f'EdgeInsets.symmetric(vertical: {parts[0]}, horizontal: {parts[1]})'
            elif len(parts) == 4:
                return f'EdgeInsets.fromLTRB({parts[3]}, {parts[0]}, {parts[1]}, {parts[2]})'

        if isinstance(padding, dict):
            if all(key in padding for key in ['left', 'top', 'right', 'bottom']):
                return f"EdgeInsets.fromLTRB({padding['left']}, {padding['top']}, {padding['right']}, {padding['bottom']})"
            elif 'horizontal' in padding or 'vertical' in padding:
                h = padding.get('horizontal', 0)
                v = padding.get('vertical', 0)
                return f'EdgeInsets.symmetric(horizontal: {h}, vertical: {v})'
            elif 'all' in padding:
                return f"EdgeInsets.all({padding['all']})"

        return 'EdgeInsets.zero'

    @staticmethod
    def map_text_style(style: Dict[str, Any]) -> str:
        """Convert text style properties to TextStyle"""
        if not style or not isinstance(style, dict):
            return 'null'

        style_properties = []

        # Font size
        if 'fontSize' in style:
            style_properties.append(f'fontSize: {style["fontSize"]}')

        # Font weight
        if 'fontWeight' in style:
            weight_map = {
                'normal': 'FontWeight.normal',
                'bold': 'FontWeight.bold',
                'w100': 'FontWeight.w100',
                'w200': 'FontWeight.w200',
                'w300': 'FontWeight.w300',
                'w400': 'FontWeight.w400',
                'w500': 'FontWeight.w500',
                'w600': 'FontWeight.w600',
                'w700': 'FontWeight.w700',
                'w800': 'FontWeight.w800',
                'w900': 'FontWeight.w900',
            }
            weight = weight_map.get(style['fontWeight'], 'FontWeight.normal')
            style_properties.append(f'fontWeight: {weight}')

        # Font style
        if 'fontStyle' in style:
            font_style = 'FontStyle.italic' if style['fontStyle'] == 'italic' else 'FontStyle.normal'
            style_properties.append(f'fontStyle: {font_style}')

        # Color
        if 'color' in style:
            color = PropertyMapper.map_color(style['color'])
            style_properties.append(f'color: {color}')

        # Letter spacing
        if 'letterSpacing' in style:
            style_properties.append(f'letterSpacing: {style["letterSpacing"]}')

        # Word spacing
        if 'wordSpacing' in style:
            style_properties.append(f'wordSpacing: {style["wordSpacing"]}')

        # Height (line height)
        if 'height' in style:
            style_properties.append(f'height: {style["height"]}')

        # Text decoration
        if 'decoration' in style:
            decoration_map = {
                'underline': 'TextDecoration.underline',
                'overline': 'TextDecoration.overline',
                'lineThrough': 'TextDecoration.lineThrough',
                'none': 'TextDecoration.none',
            }
            decoration = decoration_map.get(style['decoration'], 'TextDecoration.none')
            style_properties.append(f'decoration: {decoration}')

        # Font family
        if 'fontFamily' in style:
            style_properties.append(f"fontFamily: '{style['fontFamily']}'")

        if style_properties:
            return f'TextStyle({", ".join(style_properties)})'

        return 'null'

    @staticmethod
    def map_border_radius(radius: Union[int, float, Dict, str]) -> str:
        """Convert border radius to BorderRadius"""
        if isinstance(radius, (int, float)):
            return f'BorderRadius.circular({radius})'

        if isinstance(radius, str):
            try:
                value = float(radius)
                return f'BorderRadius.circular({value})'
            except ValueError:
                pass

        if isinstance(radius, dict):
            if 'all' in radius:
                return f"BorderRadius.circular({radius['all']})"

            if all(key in radius for key in ['topLeft', 'topRight', 'bottomLeft', 'bottomRight']):
                return (f"BorderRadius.only("
                        f"topLeft: Radius.circular({radius['topLeft']}), "
                        f"topRight: Radius.circular({radius['topRight']}), "
                        f"bottomLeft: Radius.circular({radius['bottomLeft']}), "
                        f"bottomRight: Radius.circular({radius['bottomRight']})"
                        f")")

        return 'BorderRadius.zero'

    @staticmethod
    def map_box_shadow(shadow: Union[Dict, List[Dict]]) -> str:
        """Convert shadow properties to BoxShadow"""
        if not shadow:
            return 'null'

        shadows = shadow if isinstance(shadow, list) else [shadow]
        shadow_list = []

        for s in shadows:
            if isinstance(s, dict):
                color = PropertyMapper.map_color(s.get('color', '#000000'))
                offset_x = s.get('offsetX', 0)
                offset_y = s.get('offsetY', 0)
                blur_radius = s.get('blurRadius', 0)
                spread_radius = s.get('spreadRadius', 0)

                shadow_list.append(
                    f'BoxShadow(color: {color}, '
                    f'offset: Offset({offset_x}, {offset_y}), '
                    f'blurRadius: {blur_radius}, '
                    f'spreadRadius: {spread_radius})'
                )

        if shadow_list:
            return f'[{", ".join(shadow_list)}]'

        return 'null'

    @staticmethod
    def map_axis_alignment(alignment: str, is_main: bool = True) -> str:
        """Convert axis alignment values"""
        if is_main:
            alignment_map = {
                'start': 'MainAxisAlignment.start',
                'end': 'MainAxisAlignment.end',
                'center': 'MainAxisAlignment.center',
                'spaceBetween': 'MainAxisAlignment.spaceBetween',
                'spaceAround': 'MainAxisAlignment.spaceAround',
                'spaceEvenly': 'MainAxisAlignment.spaceEvenly',
            }
            return alignment_map.get(alignment, 'MainAxisAlignment.start')
        else:
            alignment_map = {
                'start': 'CrossAxisAlignment.start',
                'end': 'CrossAxisAlignment.end',
                'center': 'CrossAxisAlignment.center',
                'stretch': 'CrossAxisAlignment.stretch',
                'baseline': 'CrossAxisAlignment.baseline',
            }
            return alignment_map.get(alignment, 'CrossAxisAlignment.center')

    @staticmethod
    def map_size(size: Union[int, float, str, Dict]) -> Dict[str, str]:
        """Convert size values to width/height properties"""
        result = {}

        if isinstance(size, (int, float)):
            result['width'] = str(size)
            result['height'] = str(size)
        elif isinstance(size, str):
            if size == 'infinity':
                result['width'] = 'double.infinity'
                result['height'] = 'double.infinity'
            else:
                try:
                    value = float(size)
                    result['width'] = str(value)
                    result['height'] = str(value)
                except ValueError:
                    pass
        elif isinstance(size, dict):
            if 'width' in size:
                result['width'] = str(size['width']) if size['width'] != 'infinity' else 'double.infinity'
            if 'height' in size:
                result['height'] = str(size['height']) if size['height'] != 'infinity' else 'double.infinity'

        return result

    @staticmethod
    def map_constraints(constraints: Dict) -> str:
        """Convert constraints to BoxConstraints"""
        if not constraints:
            return 'null'

        parts = []

        if 'minWidth' in constraints:
            parts.append(f"minWidth: {constraints['minWidth']}")
        if 'maxWidth' in constraints:
            parts.append(f"maxWidth: {constraints['maxWidth']}")
        if 'minHeight' in constraints:
            parts.append(f"minHeight: {constraints['minHeight']}")
        if 'maxHeight' in constraints:
            parts.append(f"maxHeight: {constraints['maxHeight']}")

        if parts:
            return f'BoxConstraints({", ".join(parts)})'

        return 'null'

    @staticmethod
    def map_decoration(decoration: Dict) -> str:
        """Convert decoration properties to BoxDecoration"""
        if not decoration:
            return 'null'

        parts = []

        # Background color
        if 'color' in decoration:
            color = PropertyMapper.map_color(decoration['color'])
            parts.append(f'color: {color}')

        # Border radius
        if 'borderRadius' in decoration:
            radius = PropertyMapper.map_border_radius(decoration['borderRadius'])
            parts.append(f'borderRadius: {radius}')

        # Border
        if 'border' in decoration:
            border = decoration['border']
            if isinstance(border, dict):
                color = PropertyMapper.map_color(border.get('color', '#000000'))
                width = border.get('width', 1)
                parts.append(f'border: Border.all(color: {color}, width: {width})')

        # Box shadow
        if 'boxShadow' in decoration:
            shadow = PropertyMapper.map_box_shadow(decoration['boxShadow'])
            if shadow != 'null':
                parts.append(f'boxShadow: {shadow}')

        # Gradient
        if 'gradient' in decoration:
            gradient = PropertyMapper.map_gradient(decoration['gradient'])
            if gradient != 'null':
                parts.append(f'gradient: {gradient}')

        if parts:
            return f'BoxDecoration({", ".join(parts)})'

        return 'null'

    @staticmethod
    def map_gradient(gradient: Dict) -> str:
        """Convert gradient properties to Gradient"""
        if not gradient or not isinstance(gradient, dict):
            return 'null'

        gradient_type = gradient.get('type', 'linear')
        colors = gradient.get('colors', [])

        if not colors:
            return 'null'

        color_list = [PropertyMapper.map_color(c) for c in colors]
        colors_str = f"[{', '.join(color_list)}]"

        if gradient_type == 'linear':
            begin = PropertyMapper.map_alignment(gradient.get('begin', 'centerLeft'))
            end = PropertyMapper.map_alignment(gradient.get('end', 'centerRight'))
            return f'LinearGradient(colors: {colors_str}, begin: {begin}, end: {end})'

        elif gradient_type == 'radial':
            center = PropertyMapper.map_alignment(gradient.get('center', 'center'))
            radius = gradient.get('radius', 0.5)
            return f'RadialGradient(colors: {colors_str}, center: {center}, radius: {radius})'

        return 'null'