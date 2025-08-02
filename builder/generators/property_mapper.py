# File: builder/generators/property_mapper.py

import re
from typing import Any, Dict, Optional


class PropertyMapper:
    """Maps UI properties to Flutter code"""

    @staticmethod
    def map_value(value: Any, property_type: str = None) -> str:
        """Convert a value to Flutter code representation"""
        if value is None or value == '':
            return 'null'

        if isinstance(value, bool):
            return 'true' if value else 'false'

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, str):
            if property_type == 'color':
                return PropertyMapper.map_color(value)
            elif property_type == 'alignment':
                return PropertyMapper.map_alignment(value)
            else:
                # Escape quotes in string
                escaped = value.replace("'", "\\'")
                return f"'{escaped}'"

        if isinstance(value, dict):
            if 'all' in value:  # Padding/Margin
                return PropertyMapper.map_edge_insets(value)

        return 'null'

    @staticmethod
    def map_color(color: str) -> str:
        """Convert hex color to Flutter Color"""
        if not color or color == 'null':
            return 'null'

        # Remove # if present
        hex_color = color.replace('#', '')

        # Ensure 6 or 8 characters (with alpha)
        if len(hex_color) == 6:
            hex_color = 'FF' + hex_color  # Add full opacity

        return f'Color(0x{hex_color})'

    @staticmethod
    def map_edge_insets(insets: Dict) -> str:
        """Convert padding/margin to EdgeInsets"""
        if 'all' in insets:
            return f"EdgeInsets.all({insets['all']})"
        elif all(k in insets for k in ['top', 'right', 'bottom', 'left']):
            return f"EdgeInsets.fromLTRB({insets['left']}, {insets['top']}, {insets['right']}, {insets['bottom']})"
        else:
            return "EdgeInsets.zero"

    @staticmethod
    def map_alignment(alignment: str) -> str:
        """Convert alignment string to Flutter Alignment"""
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
        }
        return alignment_map.get(alignment, 'Alignment.center')

    @staticmethod
    def map_main_axis_alignment(alignment: str) -> str:
        """Convert to MainAxisAlignment"""
        alignment_map = {
            'start': 'MainAxisAlignment.start',
            'end': 'MainAxisAlignment.end',
            'center': 'MainAxisAlignment.center',
            'spaceBetween': 'MainAxisAlignment.spaceBetween',
            'spaceAround': 'MainAxisAlignment.spaceAround',
            'spaceEvenly': 'MainAxisAlignment.spaceEvenly',
        }
        return alignment_map.get(alignment, 'MainAxisAlignment.start')

    @staticmethod
    def map_cross_axis_alignment(alignment: str) -> str:
        """Convert to CrossAxisAlignment"""
        alignment_map = {
            'start': 'CrossAxisAlignment.start',
            'end': 'CrossAxisAlignment.end',
            'center': 'CrossAxisAlignment.center',
            'stretch': 'CrossAxisAlignment.stretch',
            'baseline': 'CrossAxisAlignment.baseline',
        }
        return alignment_map.get(alignment, 'CrossAxisAlignment.center')