"""
Color Converter Utility
Converts various color formats to Flutter Color objects
"""

import re
from typing import Optional, Tuple


class ColorConverter:
    """Converts color values to Flutter format"""

    # Material color palette
    MATERIAL_COLORS = {
        'red': 'Colors.red',
        'pink': 'Colors.pink',
        'purple': 'Colors.purple',
        'deepPurple': 'Colors.deepPurple',
        'indigo': 'Colors.indigo',
        'blue': 'Colors.blue',
        'lightBlue': 'Colors.lightBlue',
        'cyan': 'Colors.cyan',
        'teal': 'Colors.teal',
        'green': 'Colors.green',
        'lightGreen': 'Colors.lightGreen',
        'lime': 'Colors.lime',
        'yellow': 'Colors.yellow',
        'amber': 'Colors.amber',
        'orange': 'Colors.orange',
        'deepOrange': 'Colors.deepOrange',
        'brown': 'Colors.brown',
        'grey': 'Colors.grey',
        'gray': 'Colors.grey',
        'blueGrey': 'Colors.blueGrey',
        'blueGray': 'Colors.blueGrey',
        'black': 'Colors.black',
        'white': 'Colors.white',
        'transparent': 'Colors.transparent',
    }

    # CSS color names to hex values
    CSS_COLORS = {
        'aliceblue': '#F0F8FF',
        'antiquewhite': '#FAEBD7',
        'aqua': '#00FFFF',
        'aquamarine': '#7FFFD4',
        'azure': '#F0FFFF',
        'beige': '#F5F5DC',
        'bisque': '#FFE4C4',
        'black': '#000000',
        'blanchedalmond': '#FFEBCD',
        'blue': '#0000FF',
        'blueviolet': '#8A2BE2',
        'brown': '#A52A2A',
        'burlywood': '#DEB887',
        'cadetblue': '#5F9EA0',
        'chartreuse': '#7FFF00',
        'chocolate': '#D2691E',
        'coral': '#FF7F50',
        'cornflowerblue': '#6495ED',
        'cornsilk': '#FFF8DC',
        'crimson': '#DC143C',
        'cyan': '#00FFFF',
        'darkblue': '#00008B',
        'darkcyan': '#008B8B',
        'darkgoldenrod': '#B8860B',
        'darkgray': '#A9A9A9',
        'darkgrey': '#A9A9A9',
        'darkgreen': '#006400',
        'darkkhaki': '#BDB76B',
        'darkmagenta': '#8B008B',
        'darkolivegreen': '#556B2F',
        'darkorange': '#FF8C00',
        'darkorchid': '#9932CC',
        'darkred': '#8B0000',
        'darksalmon': '#E9967A',
        'darkseagreen': '#8FBC8F',
        'darkslateblue': '#483D8B',
        'darkslategray': '#2F4F4F',
        'darkslategrey': '#2F4F4F',
        'darkturquoise': '#00CED1',
        'darkviolet': '#9400D3',
        'deeppink': '#FF1493',
        'deepskyblue': '#00BFFF',
        'dimgray': '#696969',
        'dimgrey': '#696969',
        'dodgerblue': '#1E90FF',
        'firebrick': '#B22222',
        'floralwhite': '#FFFAF0',
        'forestgreen': '#228B22',
        'fuchsia': '#FF00FF',
        'gainsboro': '#DCDCDC',
        'ghostwhite': '#F8F8FF',
        'gold': '#FFD700',
        'goldenrod': '#DAA520',
        'gray': '#808080',
        'grey': '#808080',
        'green': '#008000',
        'greenyellow': '#ADFF2F',
        'honeydew': '#F0FFF0',
        'hotpink': '#FF69B4',
        'indianred': '#CD5C5C',
        'indigo': '#4B0082',
        'ivory': '#FFFFF0',
        'khaki': '#F0E68C',
        'lavender': '#E6E6FA',
        'lavenderblush': '#FFF0F5',
        'lawngreen': '#7CFC00',
        'lemonchiffon': '#FFFACD',
        'lightblue': '#ADD8E6',
        'lightcoral': '#F08080',
        'lightcyan': '#E0FFFF',
        'lightgoldenrodyellow': '#FAFAD2',
        'lightgray': '#D3D3D3',
        'lightgrey': '#D3D3D3',
        'lightgreen': '#90EE90',
        'lightpink': '#FFB6C1',
        'lightsalmon': '#FFA07A',
        'lightseagreen': '#20B2AA',
        'lightskyblue': '#87CEFA',
        'lightslategray': '#778899',
        'lightslategrey': '#778899',
        'lightsteelblue': '#B0C4DE',
        'lightyellow': '#FFFFE0',
        'lime': '#00FF00',
        'limegreen': '#32CD32',
        'linen': '#FAF0E6',
        'magenta': '#FF00FF',
        'maroon': '#800000',
        'mediumaquamarine': '#66CDAA',
        'mediumblue': '#0000CD',
        'mediumorchid': '#BA55D3',
        'mediumpurple': '#9370DB',
        'mediumseagreen': '#3CB371',
        'mediumslateblue': '#7B68EE',
        'mediumspringgreen': '#00FA9A',
        'mediumturquoise': '#48D1CC',
        'mediumvioletred': '#C71585',
        'midnightblue': '#191970',
        'mintcream': '#F5FFFA',
        'mistyrose': '#FFE4E1',
        'moccasin': '#FFE4B5',
        'navajowhite': '#FFDEAD',
        'navy': '#000080',
        'oldlace': '#FDF5E6',
        'olive': '#808000',
        'olivedrab': '#6B8E23',
        'orange': '#FFA500',
        'orangered': '#FF4500',
        'orchid': '#DA70D6',
        'palegoldenrod': '#EEE8AA',
        'palegreen': '#98FB98',
        'paleturquoise': '#AFEEEE',
        'palevioletred': '#DB7093',
        'papayawhip': '#FFEFD5',
        'peachpuff': '#FFDAB9',
        'peru': '#CD853F',
        'pink': '#FFC0CB',
        'plum': '#DDA0DD',
        'powderblue': '#B0E0E6',
        'purple': '#800080',
        'red': '#FF0000',
        'rosybrown': '#BC8F8F',
        'royalblue': '#4169E1',
        'saddlebrown': '#8B4513',
        'salmon': '#FA8072',
        'sandybrown': '#F4A460',
        'seagreen': '#2E8B57',
        'seashell': '#FFF5EE',
        'sienna': '#A0522D',
        'silver': '#C0C0C0',
        'skyblue': '#87CEEB',
        'slateblue': '#6A5ACD',
        'slategray': '#708090',
        'slategrey': '#708090',
        'snow': '#FFFAFA',
        'springgreen': '#00FF7F',
        'steelblue': '#4682B4',
        'tan': '#D2B48C',
        'teal': '#008080',
        'thistle': '#D8BFD8',
        'tomato': '#FF6347',
        'turquoise': '#40E0D0',
        'violet': '#EE82EE',
        'wheat': '#F5DEB3',
        'white': '#FFFFFF',
        'whitesmoke': '#F5F5F5',
        'yellow': '#FFFF00',
        'yellowgreen': '#9ACD32',
    }

    def convert_color(self, color: str) -> str:
        """
        Convert color value to Flutter Color format

        Args:
            color: Color value (hex, rgb, rgba, or name)

        Returns:
            Flutter Color string
        """
        if not color:
            return 'Colors.transparent'

        color = color.strip().lower()

        # Check if it's already a Flutter color reference
        if color.startswith('colors.') or color.startswith('color('):
            return color

        # Check Material colors
        if color in self.MATERIAL_COLORS:
            return self.MATERIAL_COLORS[color]

        # Check CSS color names
        if color in self.CSS_COLORS:
            color = self.CSS_COLORS[color]

        # Handle hex colors
        if color.startswith('#'):
            return self._hex_to_flutter(color)

        # Handle rgb/rgba
        if color.startswith('rgb'):
            return self._rgb_to_flutter(color)

        # Handle hsl/hsla
        if color.startswith('hsl'):
            return self._hsl_to_flutter(color)

        # Try to parse as hex without #
        if len(color) in [3, 6, 8] and all(c in '0123456789abcdef' for c in color):
            return self._hex_to_flutter('#' + color)

        # Default to black if unable to parse
        return 'Colors.black'

    def _hex_to_flutter(self, hex_color: str) -> str:
        """Convert hex color to Flutter Color"""
        hex_color = hex_color.lstrip('#')

        # Handle 3-digit hex
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])

        # Add alpha if not present
        if len(hex_color) == 6:
            hex_color = 'FF' + hex_color
        elif len(hex_color) == 8:
            # Move alpha to front for Flutter
            hex_color = hex_color[6:8] + hex_color[0:6]

        try:
            # Validate hex
            int(hex_color, 16)
            return f"Color(0x{hex_color.upper()})"
        except ValueError:
            return 'Colors.black'

    def _rgb_to_flutter(self, rgb_color: str) -> str:
        """Convert rgb/rgba color to Flutter Color"""
        # Extract values from rgb(r, g, b) or rgba(r, g, b, a)
        match = re.match(r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\s*\)', rgb_color)

        if not match:
            return 'Colors.black'

        r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
        a = float(match.group(4)) if match.group(4) else 1.0

        # Clamp values
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        a = max(0.0, min(1.0, a))

        # Convert to Flutter format
        if a < 1.0:
            return f"Color.fromRGBO({r}, {g}, {b}, {a})"
        else:
            return f"Color.fromARGB(255, {r}, {g}, {b})"

    def _hsl_to_flutter(self, hsl_color: str) -> str:
        """Convert hsl/hsla color to Flutter Color"""
        # Extract values from hsl(h, s%, l%) or hsla(h, s%, l%, a)
        match = re.match(r'hsla?\s*\(\s*(\d+)\s*,\s*(\d+)%?\s*,\s*(\d+)%?\s*(?:,\s*([\d.]+))?\s*\)', hsl_color)

        if not match:
            return 'Colors.black'

        h = int(match.group(1)) / 360.0
        s = int(match.group(2)) / 100.0
        l = int(match.group(3)) / 100.0
        a = float(match.group(4)) if match.group(4) else 1.0

        # Convert HSL to RGB
        r, g, b = self._hsl_to_rgb(h, s, l)

        # Convert to Flutter format
        if a < 1.0:
            return f"Color.fromRGBO({int(r*255)}, {int(g*255)}, {int(b*255)}, {a})"
        else:
            return f"Color.fromARGB(255, {int(r*255)}, {int(g*255)}, {int(b*255)})"

    def _hsl_to_rgb(self, h: float, s: float, l: float) -> Tuple[float, float, float]:
        """Convert HSL to RGB values"""
        if s == 0:
            # Achromatic
            return l, l, l

        def hue_to_rgb(p, q, t):
            if t < 0:
                t += 1
            if t > 1:
                t -= 1
            if t < 1/6:
                return p + (q - p) * 6 * t
            if t < 1/2:
                return q
            if t < 2/3:
                return p + (q - p) * (2/3 - t) * 6
            return p

        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q

        r = hue_to_rgb(p, q, h + 1/3)
        g = hue_to_rgb(p, q, h)
        b = hue_to_rgb(p, q, h - 1/3)

        return r, g, b

    def get_material_shade(self, color: str, shade: int = 500) -> str:
        """
        Get a specific shade of a Material color

        Args:
            color: Base color name
            shade: Shade value (50, 100, 200, ..., 900)

        Returns:
            Flutter Color shade reference
        """
        base_colors = ['red', 'pink', 'purple', 'deepPurple', 'indigo', 'blue',
                       'lightBlue', 'cyan', 'teal', 'green', 'lightGreen', 'lime',
                       'yellow', 'amber', 'orange', 'deepOrange', 'brown', 'grey',
                       'blueGrey']

        if color in base_colors:
            if shade == 500:
                return f"Colors.{color}"
            else:
                return f"Colors.{color}[{shade}]"

        return self.convert_color(color)