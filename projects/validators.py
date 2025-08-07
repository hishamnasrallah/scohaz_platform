# File: projects/validators.py

from typing import Dict, List, Tuple, Optional
from projects.models import ComponentTemplate


class WidgetValidator:
    """Validates widget operations and structures"""

    # Widget compatibility rules
    WIDGET_RULES = {
        'Container': {
            'max_children': 1,
            'allowed_children': None,  # All allowed
            'forbidden_children': ['Scaffold', 'AppBar']
        },
        'Column': {
            'max_children': None,  # Unlimited
            'allowed_children': None,
            'forbidden_children': ['Scaffold', 'AppBar']
        },
        'Row': {
            'max_children': None,
            'allowed_children': None,
            'forbidden_children': ['Scaffold', 'AppBar']
        },
        'Stack': {
            'max_children': None,
            'allowed_children': None,
            'forbidden_children': ['Scaffold', 'AppBar']
        },
        'Padding': {
            'max_children': 1,
            'allowed_children': None,
            'forbidden_children': ['Scaffold', 'AppBar']
        },
        'Center': {
            'max_children': 1,
            'allowed_children': None,
            'forbidden_children': ['Scaffold', 'AppBar']
        },
        'Text': {
            'max_children': 0,
            'allowed_children': [],
            'forbidden_children': None
        },
        'Scaffold': {
            'max_children': None,
            'allowed_children': None,
            'forbidden_children': ['Scaffold']  # No nested Scaffolds
        },
        'AppBar': {
            'max_children': 0,
            'allowed_children': [],
            'forbidden_children': None
        }
    }

    # Required properties for each widget
    REQUIRED_PROPERTIES = {
        'Text': ['text'],
        'Image': ['source'],
        'Icon': ['icon'],
        'Container': [],
        'Column': [],
        'Row': [],
        'Button': ['text']
    }

    @classmethod
    def can_add_child(cls, parent_type: str, child_type: str) -> Tuple[bool, Optional[str]]:
        """Check if a child widget can be added to a parent"""

        # Get parent rules
        parent_rules = cls.WIDGET_RULES.get(parent_type, {})

        # Check if parent can have children
        max_children = parent_rules.get('max_children')
        if max_children == 0:
            return False, f"{parent_type} cannot have children"

        # Check forbidden children
        forbidden = parent_rules.get('forbidden_children', [])
        if forbidden and child_type in forbidden:
            return False, f"{child_type} cannot be added to {parent_type}"

        # Check allowed children
        allowed = parent_rules.get('allowed_children')
        if allowed is not None and child_type not in allowed:
            return False, f"{parent_type} only accepts: {', '.join(allowed)}"

        # Special rules
        if child_type == 'AppBar' and parent_type != 'Scaffold':
            return False, "AppBar can only be added to Scaffold"

        return True, None

    @classmethod
    def validate_properties(cls, widget_type: str, properties: Dict) -> Tuple[bool, List[str]]:
        """Validate widget properties"""
        errors = []

        # Check required properties
        required = cls.REQUIRED_PROPERTIES.get(widget_type, [])
        for prop in required:
            if prop not in properties or properties[prop] is None:
                errors.append(f"Missing required property: {prop}")

        # Type-specific validation
        if widget_type == 'Container':
            if 'width' in properties and properties['width'] < 0:
                errors.append("Width must be positive")
            if 'height' in properties and properties['height'] < 0:
                errors.append("Height must be positive")

        elif widget_type == 'Text':
            if 'fontSize' in properties:
                size = properties['fontSize']
                if not isinstance(size, (int, float)) or size <= 0:
                    errors.append("Font size must be a positive number")

        elif widget_type == 'Image':
            if 'source' in properties:
                source = properties['source']
                if not source or not isinstance(source, str):
                    errors.append("Image source must be a valid URL or path")

        return len(errors) == 0, errors

    @classmethod
    def validate_tree_structure(cls, root: Dict) -> Tuple[bool, List[str]]:
        """Validate entire widget tree structure"""
        errors = []

        def validate_node(node: Dict, path: str = "root"):
            if not isinstance(node, dict):
                errors.append(f"{path}: Invalid node structure")
                return

            # Check required fields
            if 'type' not in node:
                errors.append(f"{path}: Missing 'type' field")
                return

            if 'id' not in node:
                errors.append(f"{path}: Missing 'id' field")

            widget_type = node.get('type')
            properties = node.get('properties', {})

            # Validate properties
            valid, prop_errors = cls.validate_properties(widget_type, properties)
            for error in prop_errors:
                errors.append(f"{path}.{widget_type}: {error}")

            # Validate children
            children = node.get('children', [])
            rules = cls.WIDGET_RULES.get(widget_type, {})
            max_children = rules.get('max_children')

            if max_children is not None and len(children) > max_children:
                errors.append(f"{path}.{widget_type}: Too many children (max: {max_children})")

            # Recursively validate children
            for i, child in enumerate(children):
                # Check parent-child compatibility
                child_type = child.get('type')
                if child_type:
                    can_add, error = cls.can_add_child(widget_type, child_type)
                    if not can_add:
                        errors.append(f"{path}.{widget_type}: {error}")

                validate_node(child, f"{path}.{widget_type}.children[{i}]")

        validate_node(root)
        return len(errors) == 0, errors