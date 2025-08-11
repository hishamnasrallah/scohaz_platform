from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from builder.generators.widget_generator import WidgetGenerator
from simple_builder.models import WidgetMapping
from simple_project.models import Screen
# from .widget_generator import WidgetGenerator


class CodeFormat(Enum):
    COMPACT = 'compact'
    EXPANDED = 'expanded'


@dataclass
class CodeGeneratorOptions:
    includeImports: bool = True
    includeComments: bool = True
    indentSize: int = 2
    useConstConstructors: bool = True
    widgetName: str = 'MyWidget'
    isStateful: bool = False
    includeKeys: bool = False
    format: CodeFormat = CodeFormat.EXPANDED
    wrapInClass: bool = True


@dataclass
class GeneratedCode:
    code: str
    lineCount: int = 0
    widgetCount: int = 0
    depth: int = 0
    imports: list = None
    statistics: dict = None


def generate_flutter_code(
        widget_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
) -> GeneratedCode:
    """Generate Flutter code from widget data"""

    generator = WidgetGenerator()

    # Convert options dict to dataclass if needed
    if options:
        opts = CodeGeneratorOptions(**options)
    else:
        opts = CodeGeneratorOptions()

    # Generate widget code
    widget_code = generator.generate_widget(widget_data, indent=2 if opts.wrapInClass else 0)

    # Assemble complete code
    lines = []

    if opts.includeComments:
        lines.append("/// Generated Flutter widget")
        lines.append("")

    if opts.includeImports:
        imports = list(generator.imports)
        if not imports:
            imports = ["import 'package:flutter/material.dart';"]
        for import_stmt in sorted(imports):
            lines.append(import_stmt)
        lines.append("")

    if opts.wrapInClass:
        widget_type = 'StatefulWidget' if opts.isStateful else 'StatelessWidget'
        lines.append(f"class {opts.widgetName} extends {widget_type} {{")
        lines.append(f"  const {opts.widgetName}({{Key? key}}) : super(key: key);")
        lines.append("")

        if opts.isStateful:
            lines.append("  @override")
            lines.append(f"  State<{opts.widgetName}> createState() => _{opts.widgetName}State();")
            lines.append("}")
            lines.append("")
            lines.append(f"class _{opts.widgetName}State extends State<{opts.widgetName}> {{")
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

    full_code = '\n'.join(lines)

    # Calculate statistics
    widget_count = full_code.count('(')  # Simple widget count
    depth = max(line.count('  ') for line in full_code.split('\n'))

    return GeneratedCode(
        code=full_code,
        lineCount=len(lines),
        widgetCount=widget_count,
        depth=depth,
        imports=list(generator.imports),
        statistics={'widget_count': widget_count, 'max_depth': depth}
    )