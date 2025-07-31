"""
Flutter code generation package for the Visual Builder system

This package contains all the components needed to generate Flutter/Dart code
from UI structure JSON definitions.

Main Components:
- FlutterCodeGenerator: Main generator that orchestrates the code generation
- PropertyMapper: Maps UI properties to Flutter widget properties
- WidgetGenerator: Generates individual Flutter widgets from JSON definitions
- FlutterProjectBuilder: Builds complete Flutter projects and APKs
"""

from .flutter_generator import FlutterGenerator
from .property_mapper import PropertyMapper
from .widget_generator import WidgetGenerator
from .project_builder import FlutterProjectBuilder

__version__ = '1.0.0'

__all__ = [
    'FlutterGenerator',
    'PropertyMapper',
    'WidgetGenerator',
    'FlutterProjectBuilder',
]

# Convenience function to get a project builder
def create_project_builder(project):
    """
    Create a FlutterProjectBuilder instance for a project

    Args:
        project: FlutterProject model instance

    Returns:
        FlutterProjectBuilder instance
    """
    return FlutterProjectBuilder(project)