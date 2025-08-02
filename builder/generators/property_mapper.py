# File: builder/generators/property_mapper.py

import re
from typing import Any, Dict, Optional


class PropertyMapper:
    """Maps UI properties to Flutter code"""

    @staticmethod
    def map_value(value: Any, property_type: str = None) -> str:
        """Convert a value to Flutter code representation"""
        if value is None or value == '':
            return None  # Return None instead of 'null' string

        if isinstance(value, bool):
            return 'true' if value else 'false'

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, str):
            if property_type == 'color':
                return PropertyMapper.map_color(value)
            elif property_type == 'alignment':
                return PropertyMapper.map_alignment(value)
            elif property_type == 'axis':
                return PropertyMapper.map_axis(value)
            elif property_type == 'enum':
                # For enum values, return without quotes
                return value
            else:
                # Escape special characters in string
                escaped = value.replace("\\", "\\\\")  # Escape backslashes first
                escaped = escaped.replace("'", "\\'")   # Escape single quotes
                escaped = escaped.replace("$", "\\$")   # Escape dollar signs
                escaped = escaped.replace("\n", "\\n")  # Escape newlines
                escaped = escaped.replace("\r", "\\r")  # Escape carriage returns
                escaped = escaped.replace("\t", "\\t")  # Escape tabs
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
        elif len(hex_color) == 3:
            # Convert 3-char hex to 6-char (e.g., #FFF to #FFFFFF)
            hex_color = 'FF' + ''.join([c*2 for c in hex_color])

        return f'Color(0x{hex_color})'

    @staticmethod
    def map_edge_insets(insets: Dict) -> str:
        """Convert padding/margin to EdgeInsets"""
        if not insets:
            return "EdgeInsets.zero"

        if 'all' in insets:
            value = insets['all']
            # Handle null or zero values
            if value is None or value == 0:
                return "EdgeInsets.zero"
            # Ensure it's a double
            if isinstance(value, int):
                value = f"{value}.0"
            return f"EdgeInsets.all({value})"
        elif all(k in insets for k in ['top', 'right', 'bottom', 'left']):
            # Ensure all values are doubles
            left = insets.get('left', 0)
            top = insets.get('top', 0)
            right = insets.get('right', 0)
            bottom = insets.get('bottom', 0)

            # Handle null values
            if all(v in (None, 0) for v in [left, top, right, bottom]):
                return "EdgeInsets.zero"

            if isinstance(left, int):
                left = f"{left}.0"
            if isinstance(top, int):
                top = f"{top}.0"
            if isinstance(right, int):
                right = f"{right}.0"
            if isinstance(bottom, int):
                bottom = f"{bottom}.0"

            return f"EdgeInsets.fromLTRB({left}, {top}, {right}, {bottom})"
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

    @staticmethod
    def map_text_align(alignment: str) -> str:
        """Convert to TextAlign"""
        alignment_map = {
            'left': 'TextAlign.left',
            'right': 'TextAlign.right',
            'center': 'TextAlign.center',
            'justify': 'TextAlign.justify',
            'start': 'TextAlign.start',
            'end': 'TextAlign.end',
        }
        return alignment_map.get(alignment, 'TextAlign.left')

    @staticmethod
    def map_font_weight(weight: str) -> str:
        """Convert to FontWeight"""
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
        return weight_map.get(weight, 'FontWeight.normal')

    @staticmethod
    def map_box_fit(fit: str) -> str:
        """Convert to BoxFit"""
        fit_map = {
            'fill': 'BoxFit.fill',
            'contain': 'BoxFit.contain',
            'cover': 'BoxFit.cover',
            'fitWidth': 'BoxFit.fitWidth',
            'fitHeight': 'BoxFit.fitHeight',
            'none': 'BoxFit.none',
            'scaleDown': 'BoxFit.scaleDown',
        }
        return fit_map.get(fit, 'BoxFit.contain')

    @staticmethod
    def map_axis(axis: str) -> str:
        """Convert to Axis enum"""
        if axis == 'horizontal':
            return 'Axis.horizontal'
        elif axis == 'vertical':
            return 'Axis.vertical'
        return 'Axis.vertical'  # default