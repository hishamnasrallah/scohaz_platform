# File: builder/generators/code_generator_service.py
# NEW FILE - Add this comprehensive code generator service

import re
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from builder.models import WidgetMapping
from projects.models import Screen, FlutterProject


class CodeFormat(Enum):
    COMPACT = 'compact'
    EXPANDED = 'expanded'


@dataclass
class CodeGeneratorOptions:
    """Options for code generation matching Angular implementation"""
    includeImports: bool = True
    includeComments: bool = True
    indentSize: int = 2
    useConstConstructors: bool = True
    widgetName: str = 'MyWidget'
    isStateful: bool = False
    includeKeys: bool = False
    format: CodeFormat = CodeFormat.EXPANDED
    includeStatistics: bool = True
    wrapInClass: bool = True


@dataclass
class GeneratedCode:
    """Generated code with statistics"""
    code: str
    lineCount: int = 0
    widgetCount: int = 0
    depth: int = 0
    imports: List[str] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)


class EnhancedCodeGenerator:
    """Enhanced Flutter code generator with full feature parity"""

    def __init__(self):
        self.imports: Set[str] = set()
        self.widget_count = 0
        self.max_depth = 0
        self.current_depth = 0
        self.const_eligible_widgets: Set[str] = set()

    def generate_code(
            self,
            widget_data: Dict[str, Any],
            options: Optional[CodeGeneratorOptions] = None
    ) -> GeneratedCode:
        """Generate Flutter code with options and statistics"""

        # Reset state
        self.imports = {'package:flutter/material.dart'}
        self.widget_count = 0
        self.max_depth = 0
        self.current_depth = 0
        self.const_eligible_widgets = set()

        # Use default options if not provided
        if options is None:
            options = CodeGeneratorOptions()

        # Generate widget tree
        widget_code = self._generate_widget_tree(widget_data, 0, options)

        # Generate complete code
        full_code = self._assemble_code(widget_code, options)

        # Calculate statistics
        lines = full_code.split('\n')
        statistics = self._calculate_statistics(widget_data)

        return GeneratedCode(
            code=full_code,
            lineCount=len(lines),
            widgetCount=self.widget_count,
            depth=self.max_depth,
            imports=list(self.imports),
            statistics=statistics
        )

    def _generate_widget_tree(
            self,
            widget: Dict[str, Any],
            indent: int,
            options: CodeGeneratorOptions
    ) -> str:
        """Generate widget tree recursively"""

        if not widget:
            return self._generate_empty_container(indent, options)

        # Track depth
        self.current_depth = indent
        if self.current_depth > self.max_depth:
            self.max_depth = self.current_depth

        # Count widgets
        self.widget_count += 1

        widget_type = widget.get('type', 'Container')
        widget_id = widget.get('id', '')
        properties = widget.get('properties', {})
        children = widget.get('children', [])

        # Check if widget can be const
        can_be_const = self._can_use_const(widget, options)

        # Generate based on widget type
        generator_method = f'_generate_{widget_type.lower()}'
        if hasattr(self, generator_method):
            return getattr(self, generator_method)(
                widget_id, properties, children, indent, options, can_be_const
            )
        else:
            return self._generate_generic_widget(
                widget_type, widget_id, properties, children, indent, options, can_be_const
            )

    def _can_use_const(self, widget: Dict[str, Any], options: CodeGeneratorOptions) -> bool:
        """Check if widget can use const constructor"""

        if not options.useConstConstructors:
            return False

        # Check if all properties are compile-time constants
        properties = widget.get('properties', {})
        children = widget.get('children', [])

        # Dynamic properties that prevent const
        dynamic_props = ['onPressed', 'onChanged', 'onTap', 'controller']
        for prop in dynamic_props:
            if prop in properties and properties[prop] != 'null':
                return False

        # Check children recursively
        for child in children:
            if not self._can_use_const(child, options):
                return False

        return True

    def _generate_container(
            self,
            widget_id: str,
            properties: Dict,
            children: List,
            indent: int,
            options: CodeGeneratorOptions,
            can_be_const: bool
    ) -> str:
        """Generate Container widget with all properties"""

        spacing = self._get_spacing(indent, options)
        next_spacing = self._get_spacing(indent + 1, options)

        props = []

        # Add key if requested
        if options.includeKeys and widget_id:
            props.append(f"key: const Key('{widget_id}')")

        # Width & Height
        if properties.get('width') is not None:
            props.append(f"width: {self._format_double(properties['width'])}")
        if properties.get('height') is not None:
            props.append(f"height: {self._format_double(properties['height'])}")

        # Color (only if no decoration)
        if properties.get('color') and not properties.get('decoration'):
            props.append(f"color: {self._format_color(properties['color'])}")

        # Padding
        if properties.get('padding'):
            props.append(f"padding: {self._format_edge_insets(properties['padding'])}")

        # Margin
        if properties.get('margin'):
            props.append(f"margin: {self._format_edge_insets(properties['margin'])}")

        # Alignment
        if properties.get('alignment'):
            props.append(f"alignment: {self._format_alignment(properties['alignment'])}")

        # Decoration
        if properties.get('decoration'):
            props.append(f"decoration: {self._format_decoration(properties['decoration'], indent + 1, options)}")

        # Constraints
        if properties.get('constraints'):
            props.append(f"constraints: {self._format_constraints(properties['constraints'])}")

        # Transform
        if properties.get('transform'):
            props.append(f"transform: {self._format_transform(properties['transform'])}")

        # Child
        if children and len(children) > 0:
            child_code = self._generate_widget_tree(children[0], indent + 1, options)
            if options.format == CodeFormat.COMPACT:
                props.append(f"child: {child_code.strip()}")
            else:
                props.append(f"child:\n{child_code}")

        # Build widget
        const_prefix = 'const ' if can_be_const and options.useConstConstructors else ''

        if options.format == CodeFormat.COMPACT and len(props) <= 2:
            props_str = ', '.join(props)
            return f"{spacing}{const_prefix}Container({props_str})"
        else:
            props_str = f",\n{next_spacing}".join(props)
            return f"{spacing}{const_prefix}Container(\n{next_spacing}{props_str},\n{spacing})"

    def _generate_text(
            self,
            widget_id: str,
            properties: Dict,
            children: List,
            indent: int,
            options: CodeGeneratorOptions,
            can_be_const: bool
    ) -> str:
        """Generate Text widget with full TextStyle support"""

        spacing = self._get_spacing(indent, options)
        next_spacing = self._get_spacing(indent + 1, options)

        text = properties.get('text', 'Text')
        text_str = self._format_string(text)

        # Build TextStyle if needed
        style = self._build_text_style(properties, indent + 1, options)

        # Other text properties
        props = []

        if options.includeKeys and widget_id:
            props.append(f"key: const Key('{widget_id}')")

        if style:
            props.append(f"style: {style}")

        if properties.get('textAlign'):
            props.append(f"textAlign: {self._format_text_align(properties['textAlign'])}")

        if properties.get('overflow'):
            props.append(f"overflow: {self._format_text_overflow(properties['overflow'])}")

        if properties.get('maxLines'):
            props.append(f"maxLines: {properties['maxLines']}")

        if properties.get('softWrap') is not None:
            props.append(f"softWrap: {str(properties['softWrap']).lower()}")

        # Build widget
        const_prefix = 'const ' if can_be_const and options.useConstConstructors else ''

        if not props:
            return f"{spacing}{const_prefix}Text({text_str})"
        elif options.format == CodeFormat.COMPACT:
            props_str = ', '.join(props)
            return f"{spacing}{const_prefix}Text({text_str}, {props_str})"
        else:
            props_str = f",\n{next_spacing}".join(props)
            return f"{spacing}{const_prefix}Text(\n{next_spacing}{text_str},\n{next_spacing}{props_str},\n{spacing})"

    def _generate_scaffold(
            self,
            widget_id: str,
            properties: Dict,
            children: List,
            indent: int,
            options: CodeGeneratorOptions,
            can_be_const: bool
    ) -> str:
        """Generate Scaffold widget properly"""

        spacing = self._get_spacing(indent, options)
        next_spacing = self._get_spacing(indent + 1, options)

        props = []

        if options.includeKeys and widget_id:
            props.append(f"key: const Key('{widget_id}')")

        # Background color
        if properties.get('backgroundColor'):
            props.append(f"backgroundColor: {self._format_color(properties['backgroundColor'])}")

        # Find AppBar child if exists
        app_bar = None
        body_children = []
        for child in children:
            if child.get('type') == 'AppBar':
                app_bar = child
            else:
                body_children.append(child)

        # Add AppBar
        if app_bar:
            app_bar_code = self._generate_appbar(
                app_bar.get('id', ''),
                app_bar.get('properties', {}),
                app_bar.get('children', []),
                indent + 1,
                options,
                can_be_const
            )
            props.append(f"appBar: {app_bar_code.strip()}")

        # Add body
        if body_children:
            if len(body_children) == 1:
                body_code = self._generate_widget_tree(body_children[0], indent + 1, options)
                props.append(f"body:\n{body_code}")
            else:
                # Wrap multiple children in Column
                column_widget = {
                    'type': 'Column',
                    'properties': {},
                    'children': body_children
                }
                body_code = self._generate_widget_tree(column_widget, indent + 1, options)
                props.append(f"body:\n{body_code}")

        # Additional Scaffold properties
        if properties.get('drawer'):
            props.append(f"drawer: {self._generate_widget_tree(properties['drawer'], indent + 1, options)}")

        if properties.get('bottomNavigationBar'):
            props.append(
                f"bottomNavigationBar: {self._generate_widget_tree(properties['bottomNavigationBar'], indent + 1, options)}")

        if properties.get('floatingActionButton'):
            props.append(
                f"floatingActionButton: {self._generate_widget_tree(properties['floatingActionButton'], indent + 1, options)}")

        # Build widget
        props_str = f",\n{next_spacing}".join(props)
        return f"{spacing}Scaffold(\n{next_spacing}{props_str},\n{spacing})"

    def _generate_appbar(
            self,
            widget_id: str,
            properties: Dict,
            children: List,
            indent: int,
            options: CodeGeneratorOptions,
            can_be_const: bool
    ) -> str:
        """Generate AppBar widget with full support"""

        spacing = self._get_spacing(indent, options)
        next_spacing = self._get_spacing(indent + 1, options)

        props = []

        # Title
        if properties.get('title'):
            if isinstance(properties['title'], str):
                props.append(f"title: const Text('{properties['title']}')")
            else:
                props.append(f"title: {self._generate_widget_tree(properties['title'], indent + 1, options)}")

        # Background color
        if properties.get('backgroundColor'):
            props.append(f"backgroundColor: {self._format_color(properties['backgroundColor'])}")

        # Elevation
        if properties.get('elevation') is not None:
            props.append(f"elevation: {self._format_double(properties['elevation'])}")

        # Center title
        if properties.get('centerTitle') is not None:
            props.append(f"centerTitle: {str(properties['centerTitle']).lower()}")

        # Leading
        if properties.get('leading'):
            props.append(f"leading: {self._generate_widget_tree(properties['leading'], indent + 1, options)}")

        # Actions
        if properties.get('actions'):
            actions_code = []
            for action in properties['actions']:
                actions_code.append(self._generate_widget_tree(action, indent + 2, options))
            actions_str = ',\n'.join(actions_code)
            props.append(f"actions: [\n{actions_str},\n{next_spacing}]")

        # Build widget
        if options.format == CodeFormat.COMPACT and len(props) <= 2:
            props_str = ', '.join(props)
            return f"{spacing}AppBar({props_str})"
        else:
            props_str = f",\n{next_spacing}".join(props)
            return f"{spacing}AppBar(\n{next_spacing}{props_str},\n{spacing})"

    def _generate_column(
            self,
            widget_id: str,
            properties: Dict,
            children: List,
            indent: int,
            options: CodeGeneratorOptions,
            can_be_const: bool
    ) -> str:
        """Generate Column with all alignment options"""

        spacing = self._get_spacing(indent, options)
        next_spacing = self._get_spacing(indent + 1, options)

        props = []

        if options.includeKeys and widget_id:
            props.append(f"key: const Key('{widget_id}')")

        # Alignments
        if properties.get('mainAxisAlignment'):
            props.append(f"mainAxisAlignment: {self._format_main_axis_alignment(properties['mainAxisAlignment'])}")

        if properties.get('crossAxisAlignment'):
            props.append(f"crossAxisAlignment: {self._format_cross_axis_alignment(properties['crossAxisAlignment'])}")

        if properties.get('mainAxisSize'):
            props.append(f"mainAxisSize: MainAxisSize.{properties['mainAxisSize']}")

        # Children
        if children:
            children_code = []
            for child in children:
                children_code.append(self._generate_widget_tree(child, indent + 2, options))
            children_str = ',\n'.join(children_code)
            props.append(f"children: [\n{children_str},\n{next_spacing}]")
        else:
            props.append("children: const <Widget>[]")

        # Build widget
        const_prefix = 'const ' if can_be_const and options.useConstConstructors else ''
        props_str = f",\n{next_spacing}".join(props)
        return f"{spacing}{const_prefix}Column(\n{next_spacing}{props_str},\n{spacing})"

    def _generate_row(
            self,
            widget_id: str,
            properties: Dict,
            children: List,
            indent: int,
            options: CodeGeneratorOptions,
            can_be_const: bool
    ) -> str:
        """Generate Row with all alignment options"""

        spacing = self._get_spacing(indent, options)
        next_spacing = self._get_spacing(indent + 1, options)

        props = []

        if options.includeKeys and widget_id:
            props.append(f"key: const Key('{widget_id}')")

        # Alignments
        if properties.get('mainAxisAlignment'):
            props.append(f"mainAxisAlignment: {self._format_main_axis_alignment(properties['mainAxisAlignment'])}")

        if properties.get('crossAxisAlignment'):
            props.append(f"crossAxisAlignment: {self._format_cross_axis_alignment(properties['crossAxisAlignment'])}")

        if properties.get('mainAxisSize'):
            props.append(f"mainAxisSize: MainAxisSize.{properties['mainAxisSize']}")

        # Children
        if children:
            children_code = []
            for child in children:
                children_code.append(self._generate_widget_tree(child, indent + 2, options))
            children_str = ',\n'.join(children_code)
            props.append(f"children: [\n{children_str},\n{next_spacing}]")
        else:
            props.append("children: const <Widget>[]")

        # Build widget
        const_prefix = 'const ' if can_be_const and options.useConstConstructors else ''
        props_str = f",\n{next_spacing}".join(props)
        return f"{spacing}{const_prefix}Row(\n{next_spacing}{props_str},\n{spacing})"

    def _generate_stack(
            self,
            widget_id: str,
            properties: Dict,
            children: List,
            indent: int,
            options: CodeGeneratorOptions,
            can_be_const: bool
    ) -> str:
        """Generate Stack widget"""

        spacing = self._get_spacing(indent, options)
        next_spacing = self._get_spacing(indent + 1, options)

        props = []

        if options.includeKeys and widget_id:
            props.append(f"key: const Key('{widget_id}')")

        # Alignment
        if properties.get('alignment'):
            props.append(f"alignment: {self._format_alignment(properties['alignment'])}")

        # Fit
        if properties.get('fit'):
            props.append(f"fit: StackFit.{properties['fit']}")

        # Children (may include Positioned widgets)
        if children:
            children_code = []
            for child in children:
                children_code.append(self._generate_widget_tree(child, indent + 2, options))
            children_str = ',\n'.join(children_code)
            props.append(f"children: [\n{children_str},\n{next_spacing}]")
        else:
            props.append("children: const <Widget>[]")

        # Build widget
        const_prefix = 'const ' if can_be_const and options.useConstConstructors else ''
        props_str = f",\n{next_spacing}".join(props)
        return f"{spacing}{const_prefix}Stack(\n{next_spacing}{props_str},\n{spacing})"

    def _generate_sizedbox(
            self,
            widget_id: str,
            properties: Dict,
            children: List,
            indent: int,
            options: CodeGeneratorOptions,
            can_be_const: bool
    ) -> str:
        """Generate SizedBox widget"""

        spacing = self._get_spacing(indent, options)
        next_spacing = self._get_spacing(indent + 1, options)

        props = []

        if options.includeKeys and widget_id:
            props.append(f"key: const Key('{widget_id}')")

        # Width
        if properties.get('width') is not None:
            props.append(f"width: {self._format_double(properties['width'])}")

        # Height
        if properties.get('height') is not None:
            props.append(f"height: {self._format_double(properties['height'])}")

        # Child
        if children and len(children) > 0:
            child_code = self._generate_widget_tree(children[0], indent + 1, options)
            props.append(f"child:\n{child_code}")

        # Build widget
        const_prefix = 'const ' if can_be_const and options.useConstConstructors else ''

        if not props:
            return f"{spacing}{const_prefix}SizedBox()"
        else:
            props_str = f",\n{next_spacing}".join(props)
            return f"{spacing}{const_prefix}SizedBox(\n{next_spacing}{props_str},\n{spacing})"

    def _generate_padding(
            self,
            widget_id: str,
            properties: Dict,
            children: List,
            indent: int,
            options: CodeGeneratorOptions,
            can_be_const: bool
    ) -> str:
        """Generate Padding widget"""

        spacing = self._get_spacing(indent, options)
        next_spacing = self._get_spacing(indent + 1, options)

        props = []

        if options.includeKeys and widget_id:
            props.append(f"key: const Key('{widget_id}')")

        # Padding value
        if properties.get('padding'):
            props.append(f"padding: {self._format_edge_insets(properties['padding'])}")
        else:
            props.append("padding: const EdgeInsets.all(8.0)")

        # Child
        if children and len(children) > 0:
            child_code = self._generate_widget_tree(children[0], indent + 1, options)
            props.append(f"child:\n{child_code}")

        # Build widget
        const_prefix = 'const ' if can_be_const and options.useConstConstructors else ''
        props_str = f",\n{next_spacing}".join(props)
        return f"{spacing}{const_prefix}Padding(\n{next_spacing}{props_str},\n{spacing})"

    def _generate_center(
            self,
            widget_id: str,
            properties: Dict,
            children: List,
            indent: int,
            options: CodeGeneratorOptions,
            can_be_const: bool
    ) -> str:
        """Generate Center widget"""

        spacing = self._get_spacing(indent, options)
        next_spacing = self._get_spacing(indent + 1, options)

        props = []

        if options.includeKeys and widget_id:
            props.append(f"key: const Key('{widget_id}')")

        # Width/Height factors
        if properties.get('widthFactor'):
            props.append(f"widthFactor: {properties['widthFactor']}")

        if properties.get('heightFactor'):
            props.append(f"heightFactor: {properties['heightFactor']}")

        # Child
        if children and len(children) > 0:
            child_code = self._generate_widget_tree(children[0], indent + 1, options)
            props.append(f"child:\n{child_code}")

        # Build widget
        const_prefix = 'const ' if can_be_const and options.useConstConstructors else ''

        if not props or (len(props) == 1 and 'child' in props[0]):
            if children:
                return f"{spacing}{const_prefix}Center(\n{next_spacing}child:\n{child_code},\n{spacing})"
            else:
                return f"{spacing}{const_prefix}Center()"
        else:
            props_str = f",\n{next_spacing}".join(props)
            return f"{spacing}{const_prefix}Center(\n{next_spacing}{props_str},\n{spacing})"

    def _generate_generic_widget(
            self,
            widget_type: str,
            widget_id: str,
            properties: Dict,
            children: List,
            indent: int,
            options: CodeGeneratorOptions,
            can_be_const: bool
    ) -> str:
        """Generate any widget using mapping"""

        spacing = self._get_spacing(indent, options)
        next_spacing = self._get_spacing(indent + 1, options)

        # Try to get mapping from database
        try:
            mapping = WidgetMapping.objects.get(ui_type=widget_type.lower(), is_active=True)
            flutter_widget = mapping.flutter_widget
        except WidgetMapping.DoesNotExist:
            flutter_widget = widget_type

        props = []

        if options.includeKeys and widget_id:
            props.append(f"key: const Key('{widget_id}')")

        # Add properties
        for key, value in properties.items():
            formatted_value = self._format_property_value(key, value)
            if formatted_value:
                props.append(f"{key}: {formatted_value}")

        # Add children
        if children:
            if len(children) == 1:
                child_code = self._generate_widget_tree(children[0], indent + 1, options)
                props.append(f"child:\n{child_code}")
            else:
                children_code = []
                for child in children:
                    children_code.append(self._generate_widget_tree(child, indent + 2, options))
                children_str = ',\n'.join(children_code)
                props.append(f"children: [\n{children_str},\n{next_spacing}]")

        # Build widget
        const_prefix = 'const ' if can_be_const and options.useConstConstructors else ''

        if not props:
            return f"{spacing}{const_prefix}{flutter_widget}()"
        else:
            props_str = f",\n{next_spacing}".join(props)
            return f"{spacing}{const_prefix}{flutter_widget}(\n{next_spacing}{props_str},\n{spacing})"

    def _generate_empty_container(self, indent: int, options: CodeGeneratorOptions) -> str:
        """Generate empty container as fallback"""
        spacing = self._get_spacing(indent, options)
        const_prefix = 'const ' if options.useConstConstructors else ''
        return f"{spacing}{const_prefix}Container()"

    # === Formatting Methods ===

    def _format_color(self, color: str) -> str:
        """Format color value"""
        if not color or color == 'null':
            return 'null'

        if color.startswith('#'):
            hex_color = color.replace('#', '')
            if len(hex_color) == 3:
                hex_color = ''.join([c * 2 for c in hex_color])
            if len(hex_color) == 6:
                hex_color = 'FF' + hex_color
            return f"const Color(0x{hex_color.upper()})"

        # Named colors
        color_map = {
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

        return color_map.get(color.lower(), f"const Color(0xFF000000)")

    def _format_edge_insets(self, insets: Any) -> str:
        """Format EdgeInsets"""
        if isinstance(insets, dict):
            if 'all' in insets:
                value = insets['all']
                if value == 0:
                    return "EdgeInsets.zero"
                return f"const EdgeInsets.all({self._format_double(value)})"

            top = insets.get('top', 0)
            right = insets.get('right', 0)
            bottom = insets.get('bottom', 0)
            left = insets.get('left', 0)

            if top == right == bottom == left:
                if top == 0:
                    return "EdgeInsets.zero"
                return f"const EdgeInsets.all({self._format_double(top)})"

            if left == right and top == bottom:
                return f"const EdgeInsets.symmetric(horizontal: {self._format_double(left)}, vertical: {self._format_double(top)})"

            return f"const EdgeInsets.fromLTRB({self._format_double(left)}, {self._format_double(top)}, {self._format_double(right)}, {self._format_double(bottom)})"

        return "EdgeInsets.zero"

    def _format_alignment(self, alignment: str) -> str:
        """Format Alignment"""
        alignment_map = {
            'topLeft': 'Alignment.topLeft',
            'topCenter': 'Alignment.topCenter',
            'topRight': 'Alignment.topRight',
            'centerLeft': 'Alignment.centerLeft',
            'center': 'Alignment.center',
            'centerRight': 'Alignment.centerRight',
            'bottomLeft': 'Alignment.bottomLeft',
            'bottomCenter': 'Alignment.bottomCenter',
            'bottomRight': 'Alignment.bottomRight',
        }
        return alignment_map.get(alignment, 'Alignment.center')

    def _format_main_axis_alignment(self, alignment: str) -> str:
        """Format MainAxisAlignment"""
        alignment_map = {
            'start': 'MainAxisAlignment.start',
            'end': 'MainAxisAlignment.end',
            'center': 'MainAxisAlignment.center',
            'spaceBetween': 'MainAxisAlignment.spaceBetween',
            'spaceAround': 'MainAxisAlignment.spaceAround',
            'spaceEvenly': 'MainAxisAlignment.spaceEvenly',
        }
        return alignment_map.get(alignment, 'MainAxisAlignment.start')

    def _format_cross_axis_alignment(self, alignment: str) -> str:
        """Format CrossAxisAlignment"""
        alignment_map = {
            'start': 'CrossAxisAlignment.start',
            'end': 'CrossAxisAlignment.end',
            'center': 'CrossAxisAlignment.center',
            'stretch': 'CrossAxisAlignment.stretch',
            'baseline': 'CrossAxisAlignment.baseline',
        }
        return alignment_map.get(alignment, 'CrossAxisAlignment.center')

    def _format_text_align(self, align: str) -> str:
        """Format TextAlign"""
        align_map = {
            'left': 'TextAlign.left',
            'right': 'TextAlign.right',
            'center': 'TextAlign.center',
            'justify': 'TextAlign.justify',
            'start': 'TextAlign.start',
            'end': 'TextAlign.end',
        }
        return align_map.get(align, 'TextAlign.left')

    def _format_text_overflow(self, overflow: str) -> str:
        """Format TextOverflow"""
        overflow_map = {
            'clip': 'TextOverflow.clip',
            'fade': 'TextOverflow.fade',
            'ellipsis': 'TextOverflow.ellipsis',
            'visible': 'TextOverflow.visible',
        }
        return overflow_map.get(overflow, 'TextOverflow.ellipsis')

    def _format_font_weight(self, weight: str) -> str:
        """Format FontWeight"""
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
        return weight_map.get(weight, weight)

    def _format_font_style(self, style: str) -> str:
        """Format FontStyle"""
        if style == 'italic':
            return 'FontStyle.italic'
        return 'FontStyle.normal'

    def _format_decoration(self, decoration: Dict, indent: int, options: CodeGeneratorOptions) -> str:
        """Format BoxDecoration"""
        spacing = self._get_spacing(indent, options)
        next_spacing = self._get_spacing(indent + 1, options)

        props = []

        # Color
        if decoration.get('color'):
            props.append(f"color: {self._format_color(decoration['color'])}")

        # Border
        if decoration.get('border'):
            props.append(f"border: {self._format_border(decoration['border'])}")

        # BorderRadius
        if decoration.get('borderRadius'):
            props.append(f"borderRadius: {self._format_border_radius(decoration['borderRadius'])}")

        # BoxShadow
        if decoration.get('boxShadow'):
            props.append(f"boxShadow: {self._format_box_shadow(decoration['boxShadow'], indent + 1, options)}")

        # Gradient
        if decoration.get('gradient'):
            props.append(f"gradient: {self._format_gradient(decoration['gradient'], indent + 1, options)}")

        props_str = f",\n{next_spacing}".join(props)
        return f"BoxDecoration(\n{next_spacing}{props_str},\n{spacing})"

    def _format_border(self, border: Any) -> str:
        """Format Border"""
        if isinstance(border, dict):
            color = self._format_color(border.get('color', '#000000'))
            width = self._format_double(border.get('width', 1.0))
            return f"Border.all(color: {color}, width: {width})"
        return "Border.all()"

    def _format_border_radius(self, radius: Any) -> str:
        """Format BorderRadius"""
        if isinstance(radius, (int, float)):
            return f"BorderRadius.circular({self._format_double(radius)})"
        elif isinstance(radius, dict):
            if 'all' in radius:
                return f"BorderRadius.circular({self._format_double(radius['all'])})"
            # Handle individual corners
            tl = radius.get('topLeft', 0)
            tr = radius.get('topRight', 0)
            bl = radius.get('bottomLeft', 0)
            br = radius.get('bottomRight', 0)
            return f"BorderRadius.only(topLeft: Radius.circular({tl}), topRight: Radius.circular({tr}), bottomLeft: Radius.circular({bl}), bottomRight: Radius.circular({br}))"
        return "BorderRadius.zero"

    def _format_box_shadow(self, shadows: List, indent: int, options: CodeGeneratorOptions) -> str:
        """Format BoxShadow list"""
        if not shadows:
            return "const <BoxShadow>[]"

        spacing = self._get_spacing(indent, options)
        next_spacing = self._get_spacing(indent + 1, options)

        shadow_list = []
        for shadow in shadows:
            color = self._format_color(shadow.get('color', '#000000'))
            offset_x = shadow.get('offsetX', 0)
            offset_y = shadow.get('offsetY', 0)
            blur_radius = shadow.get('blurRadius', 0)
            spread_radius = shadow.get('spreadRadius', 0)

            shadow_str = f"BoxShadow(color: {color}, offset: Offset({offset_x}, {offset_y}), blurRadius: {blur_radius}, spreadRadius: {spread_radius})"
            shadow_list.append(f"{next_spacing}{shadow_str}")

        return f"[\n{','.join(shadow_list)},\n{spacing}]"

    def _format_gradient(self, gradient: Dict, indent: int, options: CodeGeneratorOptions) -> str:
        """Format Gradient"""
        gradient_type = gradient.get('type', 'linear')
        colors = gradient.get('colors', ['#FFFFFF', '#000000'])

        color_list = ', '.join([self._format_color(c) for c in colors])

        if gradient_type == 'linear':
            begin = self._format_alignment(gradient.get('begin', 'topLeft'))
            end = self._format_alignment(gradient.get('end', 'bottomRight'))
            return f"LinearGradient(begin: {begin}, end: {end}, colors: [{color_list}])"
        elif gradient_type == 'radial':
            return f"RadialGradient(colors: [{color_list}])"
        else:
            return f"LinearGradient(colors: [{color_list}])"

    def _format_constraints(self, constraints: Dict) -> str:
        """Format BoxConstraints"""
        props = []

        if 'minWidth' in constraints:
            props.append(f"minWidth: {self._format_double(constraints['minWidth'])}")
        if 'maxWidth' in constraints:
            props.append(f"maxWidth: {self._format_double(constraints['maxWidth'])}")
        if 'minHeight' in constraints:
            props.append(f"minHeight: {self._format_double(constraints['minHeight'])}")
        if 'maxHeight' in constraints:
            props.append(f"maxHeight: {self._format_double(constraints['maxHeight'])}")

        if props:
            return f"BoxConstraints({', '.join(props)})"
        return "BoxConstraints()"

    def _format_transform(self, transform: Any) -> str:
        """Format Matrix4 transform"""
        if isinstance(transform, dict):
            if 'rotate' in transform:
                angle = transform['rotate']
                return f"Matrix4.rotationZ({angle})"
            elif 'scale' in transform:
                scale = transform['scale']
                return f"Matrix4.diagonal3Values({scale}, {scale}, 1.0)"
            elif 'translate' in transform:
                x = transform['translate'].get('x', 0)
                y = transform['translate'].get('y', 0)
                return f"Matrix4.translationValues({x}, {y}, 0.0)"
        return "Matrix4.identity()"

    def _build_text_style(self, properties: Dict, indent: int, options: CodeGeneratorOptions) -> Optional[str]:
        """Build comprehensive TextStyle"""
        style_props = []

        if properties.get('fontSize'):
            style_props.append(f"fontSize: {self._format_double(properties['fontSize'])}")

        if properties.get('color') or properties.get('textColor'):
            color = properties.get('textColor') or properties.get('color')
            style_props.append(f"color: {self._format_color(color)}")

        if properties.get('fontWeight'):
            style_props.append(f"fontWeight: {self._format_font_weight(properties['fontWeight'])}")

        if properties.get('fontStyle'):
            style_props.append(f"fontStyle: {self._format_font_style(properties['fontStyle'])}")

        if properties.get('letterSpacing'):
            style_props.append(f"letterSpacing: {self._format_double(properties['letterSpacing'])}")

        if properties.get('wordSpacing'):
            style_props.append(f"wordSpacing: {self._format_double(properties['wordSpacing'])}")

        if properties.get('height'):
            style_props.append(f"height: {self._format_double(properties['height'])}")

        if properties.get('decoration'):
            style_props.append(f"decoration: TextDecoration.{properties['decoration']}")

        if properties.get('decorationColor'):
            style_props.append(f"decorationColor: {self._format_color(properties['decorationColor'])}")

        if properties.get('fontFamily'):
            style_props.append(f"fontFamily: '{properties['fontFamily']}'")

        if style_props:
            if options.format == CodeFormat.COMPACT:
                return f"TextStyle({', '.join(style_props)})"
            else:
                spacing = self._get_spacing(indent, options)
                next_spacing = self._get_spacing(indent + 1, options)
                props_str = f",\n{next_spacing}".join(style_props)
                return f"TextStyle(\n{next_spacing}{props_str},\n{spacing})"
        return None

    def _format_double(self, value: Any) -> str:
        """Format numeric value as double"""
        if isinstance(value, int):
            return f"{value}.0"
        return str(value)

    def _format_string(self, value: str) -> str:
        """Format string value with proper escaping"""
        if not value:
            return "''"
        # Escape special characters
        escaped = value.replace("\\", "\\\\")
        escaped = escaped.replace("'", "\\'")
        escaped = escaped.replace("$", "\\$")
        escaped = escaped.replace("\n", "\\n")
        escaped = escaped.replace("\r", "\\r")
        escaped = escaped.replace("\t", "\\t")
        return f"'{escaped}'"

    def _format_property_value(self, key: str, value: Any) -> Optional[str]:
        """Format any property value"""
        if value is None:
            return None

        if isinstance(value, bool):
            return str(value).lower()

        if isinstance(value, (int, float)):
            return self._format_double(value)

        if isinstance(value, str):
            if key in ['color', 'backgroundColor', 'foregroundColor']:
                return self._format_color(value)
            elif key == 'alignment':
                return self._format_alignment(value)
            elif key == 'mainAxisAlignment':
                return self._format_main_axis_alignment(value)
            elif key == 'crossAxisAlignment':
                return self._format_cross_axis_alignment(value)
            elif key == 'textAlign':
                return self._format_text_align(value)
            else:
                return self._format_string(value)

        return None

    def _get_spacing(self, indent: int, options: CodeGeneratorOptions) -> str:
        """Get indentation spacing"""
        return ' ' * (indent * options.indentSize)

    def _assemble_code(self, widget_code: str, options: CodeGeneratorOptions) -> str:
        """Assemble complete code with imports and class wrapper"""
        lines = []

        # Add comments if requested
        if options.includeComments:
            lines.append("/// Generated Flutter widget")
            lines.append("/// Created with Django Flutter Builder")
            lines.append("")

        # Add imports if requested
        if options.includeImports:
            for import_stmt in sorted(self.imports):
                lines.append(f"import '{import_stmt}';")
            lines.append("")

        # Wrap in class if requested
        if options.wrapInClass:
            lines.append(
                f"class {options.widgetName} extends {'StatefulWidget' if options.isStateful else 'StatelessWidget'} {{")
            lines.append(f"  const {options.widgetName}({{Key? key}}) : super(key: key);")
            lines.append("")

            if options.isStateful:
                lines.append("  @override")
                lines.append(f"  State<{options.widgetName}> createState() => _{options.widgetName}State();")
                lines.append("}")
                lines.append("")
                lines.append(f"class _{options.widgetName}State extends State<{options.widgetName}> {{")
                lines.append("  @override")
                lines.append("  Widget build(BuildContext context) {")
                lines.append(f"    return{widget_code.lstrip()};")
                lines.append("  }")
                lines.append("}")
            else:
                lines.append("  @override")
                lines.append("  Widget build(BuildContext context) {")
                lines.append(f"    return{widget_code.lstrip()};")
                lines.append("  }")
                lines.append("}")
        else:
            lines.append(widget_code)

        return '\n'.join(lines)

    def _calculate_statistics(self, widget_data: Dict) -> Dict[str, Any]:
        """Calculate comprehensive statistics about the widget tree"""
        stats = {
            'total_widgets': self.widget_count,
            'max_depth': self.max_depth,
            'widget_types': {},
            'property_usage': {},
            'const_eligible': len(self.const_eligible_widgets),
            'has_navigation': False,
            'has_forms': False,
            'has_animations': False,
        }

        def analyze_widget(widget: Dict):
            widget_type = widget.get('type', 'unknown')

            # Count widget types
            if widget_type not in stats['widget_types']:
                stats['widget_types'][widget_type] = 0
            stats['widget_types'][widget_type] += 1

            # Analyze properties
            properties = widget.get('properties', {})
            for prop_key in properties:
                if prop_key not in stats['property_usage']:
                    stats['property_usage'][prop_key] = 0
                stats['property_usage'][prop_key] += 1

            # Check for special features
            if widget_type in ['Button', 'IconButton', 'GestureDetector', 'InkWell']:
                stats['has_navigation'] = True
            if widget_type in ['TextField', 'TextFormField', 'Form']:
                stats['has_forms'] = True
            if widget_type.startswith('Animated'):
                stats['has_animations'] = True

            # Analyze children
            for child in widget.get('children', []):
                analyze_widget(child)

        analyze_widget(widget_data)
        return stats


# Utility functions for external use
def generate_flutter_code(
        widget_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
) -> GeneratedCode:
    """Convenience function to generate Flutter code"""
    generator = EnhancedCodeGenerator()

    # Convert dict options to dataclass
    if options:
        opts = CodeGeneratorOptions(**options)
    else:
        opts = CodeGeneratorOptions()

    return generator.generate_code(widget_data, opts)


def copy_to_clipboard(code: str) -> bool:
    """Copy code to clipboard (server-side implementation)"""
    # Note: This would need frontend implementation
    # Server can only prepare the code for copying
    return True


def download_as_file(code: str, filename: str = 'widget.dart') -> bytes:
    """Prepare code for download as file"""
    return code.encode('utf-8')