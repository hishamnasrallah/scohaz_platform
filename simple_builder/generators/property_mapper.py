# Simplified property mapper for Flutter code generation
class PropertyMapper:
    """Maps UI properties to Flutter code"""

    @staticmethod
    def map_value(value, property_type=None):
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
                # Escape special characters
                escaped = value.replace("'", "\\'")
                return f"'{escaped}'"

        return 'null'

    @staticmethod
    def map_color(color):
        """Convert hex color to Flutter Color"""
        if not color or color == 'null':
            return 'null'

        hex_color = color.replace('#', '')
        if len(hex_color) == 6:
            hex_color = 'FF' + hex_color

        return f'Color(0x{hex_color})'

    @staticmethod
    def map_edge_insets(insets):
        """Convert padding/margin to EdgeInsets"""
        if not insets or insets is None:
            return "EdgeInsets.zero"

        if isinstance(insets, dict):
            if 'all' in insets:
                value = insets['all']
                if value is None or value == 0:
                    return "EdgeInsets.zero"
                if isinstance(value, int):
                    value = float(value)
                return f"EdgeInsets.all({value})"

            top = insets.get('top', 0)
            right = insets.get('right', 0)
            bottom = insets.get('bottom', 0)
            left = insets.get('left', 0)

            # Convert to float
            if isinstance(top, int):
                top = float(top)
            if isinstance(right, int):
                right = float(right)
            if isinstance(bottom, int):
                bottom = float(bottom)
            if isinstance(left, int):
                left = float(left)

            if top == right == bottom == left:
                if top == 0:
                    return "EdgeInsets.zero"
                return f"EdgeInsets.all({top})"

            return f"EdgeInsets.fromLTRB({left}, {top}, {right}, {bottom})"

        return "EdgeInsets.zero"

    @staticmethod
    def map_alignment(alignment):
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
    def map_main_axis_alignment(alignment):
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
    def map_cross_axis_alignment(alignment):
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
    def map_text_align(alignment):
        """Convert to TextAlign"""
        alignment_map = {
            'left': 'TextAlign.left',
            'right': 'TextAlign.right',
            'center': 'TextAlign.center',
            'justify': 'TextAlign.justify',
        }
        return alignment_map.get(alignment, 'TextAlign.left')

    @staticmethod
    def map_font_weight(weight):
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
    def map_box_fit(fit):
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
    def map_axis(axis):
        """Convert to Axis enum"""
        if axis == 'horizontal':
            return 'Axis.horizontal'
        elif axis == 'vertical':
            return 'Axis.vertical'
        return 'Axis.vertical'