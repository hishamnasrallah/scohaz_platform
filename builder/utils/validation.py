"""
Validation Utilities for Flutter Code Generation
Validates UI structure and widget properties
"""

from typing import Dict, List, Any, Optional, Set


class WidgetValidator:
    """Validates widget structures and properties"""

    # Valid widget types
    VALID_WIDGET_TYPES = {
        'scaffold', 'appbar', 'container', 'text', 'button', 'elevated_button',
        'text_button', 'outlined_button', 'column', 'row', 'stack', 'positioned',
        'expanded', 'flexible', 'sizedbox', 'padding', 'center', 'align',
        'image', 'icon', 'textfield', 'checkbox', 'radio', 'switch',
        'listview', 'gridview', 'card', 'listtile', 'drawer', 'bottomnavigationbar',
        'tabbar', 'tabbarview', 'pageview', 'form', 'gesturedetector', 'inkwell',
        'hero', 'animatedcontainer', 'animatedopacity', 'fadeintransition'
    }

    # Required properties for each widget type
    REQUIRED_PROPERTIES = {
        'text': ['content'],  # Unless useTranslation is true
        'button': ['text', 'onPressed'],
        'elevated_button': ['text', 'onPressed'],
        'text_button': ['text', 'onPressed'],
        'outlined_button': ['text', 'onPressed'],
        'image': ['source'],
        'positioned': ['child'],
        'expanded': ['child'],
        'flexible': ['child'],
        'padding': ['padding', 'child'],
        'center': ['child'],
        'align': ['alignment', 'child'],
    }

    # Properties that must be specific types
    PROPERTY_TYPES = {
        'width': (int, float),
        'height': (int, float),
        'padding': (int, float, dict, list),
        'margin': (int, float, dict, list),
        'elevation': (int, float),
        'fontSize': (int, float),
        'flex': int,
        'maxLines': int,
        'minLines': int,
        'borderRadius': (int, float, dict),
        'opacity': float,
    }

    # Properties that must be from specific values
    PROPERTY_VALUES = {
        'mainAxisAlignment': ['start', 'end', 'center', 'spaceBetween', 'spaceAround', 'spaceEvenly'],
        'crossAxisAlignment': ['start', 'end', 'center', 'stretch', 'baseline'],
        'mainAxisSize': ['min', 'max'],
        'alignment': ['topLeft', 'topCenter', 'topRight', 'centerLeft', 'center',
                      'centerRight', 'bottomLeft', 'bottomCenter', 'bottomRight'],
        'textAlign': ['left', 'right', 'center', 'justify', 'start', 'end'],
        'overflow': ['clip', 'fade', 'ellipsis', 'visible'],
        'fontWeight': ['normal', 'bold', 'w100', 'w200', 'w300', 'w400', 'w500',
                       'w600', 'w700', 'w800', 'w900'],
        'fontStyle': ['normal', 'italic'],
        'fit': ['contain', 'cover', 'fill', 'fitWidth', 'fitHeight', 'none', 'scaleDown'],
        'imageType': ['network', 'asset', 'file', 'memory'],
        'keyboardType': ['text', 'number', 'email', 'phone', 'multiline', 'url', 'datetime'],
    }

    def validate_widget(self, widget_data: Dict) -> List[str]:
        """
        Validate a widget structure

        Args:
            widget_data: Widget JSON structure

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Validate widget type
        widget_type = widget_data.get('type', '').lower()
        if not widget_type:
            errors.append("Widget must have a 'type' property")
            return errors

        if widget_type not in self.VALID_WIDGET_TYPES:
            errors.append(f"Invalid widget type: '{widget_type}'")

        # Validate required properties
        errors.extend(self._validate_required_properties(widget_type, widget_data))

        # Validate property types
        properties = widget_data.get('properties', {})
        errors.extend(self._validate_property_types(properties))

        # Validate property values
        errors.extend(self._validate_property_values(properties))

        # Validate children structure
        errors.extend(self._validate_children(widget_data))

        # Widget-specific validation
        errors.extend(self._validate_specific_widget(widget_type, widget_data))

        return errors

    def _validate_required_properties(self, widget_type: str, widget_data: Dict) -> List[str]:
        """Validate required properties for widget type"""
        errors = []
        properties = widget_data.get('properties', {})

        required = self.REQUIRED_PROPERTIES.get(widget_type, [])
        for prop in required:
            # Special handling for text widget
            if widget_type == 'text' and prop == 'content':
                if properties.get('useTranslation') and properties.get('translationKey'):
                    continue  # Translation key replaces content

            if prop not in properties and prop not in widget_data:
                errors.append(f"{widget_type} widget requires '{prop}' property")

        return errors

    def _validate_property_types(self, properties: Dict) -> List[str]:
        """Validate property data types"""
        errors = []

        for prop, expected_types in self.PROPERTY_TYPES.items():
            if prop in properties:
                value = properties[prop]
                if not isinstance(value, expected_types):
                    if isinstance(expected_types, tuple):
                        type_names = ' or '.join(t.__name__ for t in expected_types)
                    else:
                        type_names = expected_types.__name__
                    errors.append(f"Property '{prop}' must be {type_names}, got {type(value).__name__}")

        return errors

    def _validate_property_values(self, properties: Dict) -> List[str]:
        """Validate property values against allowed values"""
        errors = []

        for prop, allowed_values in self.PROPERTY_VALUES.items():
            if prop in properties:
                value = properties[prop]
                if isinstance(value, str) and value not in allowed_values:
                    errors.append(f"Property '{prop}' must be one of: {', '.join(allowed_values)}")

        return errors

    def _validate_children(self, widget_data: Dict) -> List[str]:
        """Validate children structure"""
        errors = []

        # Check for mutually exclusive child properties
        child_props = ['child', 'children', 'body']
        found_props = [p for p in child_props if p in widget_data]

        if len(found_props) > 1:
            errors.append(f"Widget cannot have multiple child properties: {', '.join(found_props)}")

        # Validate children array
        if 'children' in widget_data:
            children = widget_data['children']
            if not isinstance(children, list):
                errors.append("'children' property must be an array")
            else:
                for i, child in enumerate(children):
                    if not isinstance(child, dict):
                        errors.append(f"Child {i} must be an object")
                    else:
                        child_errors = self.validate_widget(child)
                        for error in child_errors:
                            errors.append(f"Child {i}: {error}")

        # Validate single child
        for prop in ['child', 'body']:
            if prop in widget_data:
                child = widget_data[prop]
                if not isinstance(child, dict):
                    errors.append(f"'{prop}' property must be an object")
                else:
                    child_errors = self.validate_widget(child)
                    for error in child_errors:
                        errors.append(f"{prop}: {error}")

        return errors

    def _validate_specific_widget(self, widget_type: str, widget_data: Dict) -> List[str]:
        """Widget-specific validation rules"""
        errors = []
        properties = widget_data.get('properties', {})

        if widget_type == 'scaffold':
            # Scaffold-specific validation
            if 'appBar' in properties and not isinstance(properties['appBar'], dict):
                errors.append("Scaffold 'appBar' must be an object")

            if 'body' not in widget_data:
                errors.append("Scaffold requires a 'body' widget")

        elif widget_type in ['column', 'row']:
            # Layout widgets must have children
            if 'children' not in widget_data:
                errors.append(f"{widget_type} widget requires 'children' array")

        elif widget_type == 'stack':
            # Stack validation
            if 'children' not in widget_data:
                errors.append("Stack widget requires 'children' array")

            # Check for positioned children
            children = widget_data.get('children', [])
            for child in children:
                if isinstance(child, dict) and child.get('type') == 'positioned':
                    pos_props = child.get('properties', {})
                    # Positioned must have at least one position property
                    position_props = ['top', 'right', 'bottom', 'left']
                    if not any(p in pos_props for p in position_props):
                        errors.append("Positioned widget must have at least one position property")

        elif widget_type == 'listview':
            # ListView validation
            if 'children' not in widget_data and 'itemBuilder' not in properties:
                errors.append("ListView requires either 'children' or 'itemBuilder'")

        elif widget_type == 'image':
            # Image validation
            source = properties.get('source', '')
            image_type = properties.get('imageType', 'network')

            if image_type == 'network' and not source.startswith(('http://', 'https://')):
                errors.append("Network image source must be a valid URL")
            elif image_type == 'asset' and source.startswith(('http://', 'https://')):
                errors.append("Asset image source should not be a URL")

        elif widget_type == 'textfield':
            # TextField validation
            if 'keyboardType' in properties:
                kb_type = properties['keyboardType']
                if kb_type == 'number' and 'inputFormatters' not in properties:
                    # Just a warning, not an error
                    pass

        return errors

    def validate_project_structure(self, project_data: Dict) -> List[str]:
        """
        Validate entire project structure

        Args:
            project_data: Complete project JSON structure

        Returns:
            List of validation errors
        """
        errors = []

        # Validate project metadata
        if 'project' not in project_data:
            errors.append("Project structure must contain 'project' metadata")
        else:
            project = project_data['project']
            if not project.get('name'):
                errors.append("Project must have a name")
            if not project.get('package'):
                errors.append("Project must have a package name")
            elif not self._validate_package_name(project['package']):
                errors.append("Invalid package name format")

        # Validate screens
        if 'screens' not in project_data:
            errors.append("Project must contain at least one screen")
        else:
            screens = project_data['screens']
            if not isinstance(screens, list) or len(screens) == 0:
                errors.append("Screens must be a non-empty array")
            else:
                screen_names = set()
                has_home = False

                for i, screen in enumerate(screens):
                    if not isinstance(screen, dict):
                        errors.append(f"Screen {i} must be an object")
                        continue

                    # Check screen properties
                    if not screen.get('name'):
                        errors.append(f"Screen {i} must have a name")
                    else:
                        name = screen['name']
                        if name in screen_names:
                            errors.append(f"Duplicate screen name: {name}")
                        screen_names.add(name)

                    if not screen.get('root'):
                        errors.append(f"Screen '{screen.get('name', i)}' must have a root widget")
                    else:
                        # Validate root widget
                        root_errors = self.validate_widget(screen['root'])
                        for error in root_errors:
                            errors.append(f"Screen '{screen.get('name', i)}' root: {error}")

                    if screen.get('is_home'):
                        if has_home:
                            errors.append("Multiple screens marked as home")
                        has_home = True

                if not has_home and screens:
                    # Not an error, just use first screen as home
                    pass

        return errors

    def _validate_package_name(self, package_name: str) -> bool:
        """Validate Android package name format"""
        import re
        # Android package name pattern
        pattern = r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$'
        return bool(re.match(pattern, package_name))

    def suggest_fixes(self, errors: List[str]) -> Dict[str, str]:
        """
        Suggest fixes for common validation errors

        Args:
            errors: List of validation errors

        Returns:
            Dictionary of error patterns to suggested fixes
        """
        suggestions = {}

        for error in errors:
            if "Invalid widget type" in error:
                widget_type = error.split("'")[1]
                similar = self._find_similar_widget(widget_type)
                if similar:
                    suggestions[error] = f"Did you mean '{similar}'?"

            elif "must be one of" in error:
                suggestions[error] = "Check the documentation for allowed values"

            elif "requires" in error and "property" in error:
                suggestions[error] = "Add the missing required property to the widget"

            elif "Invalid package name" in error:
                suggestions[error] = "Use lowercase letters and dots (e.g., com.example.app)"

        return suggestions

    def _find_similar_widget(self, widget_type: str) -> Optional[str]:
        """Find similar widget type name"""
        widget_type = widget_type.lower()

        # Check exact match with different case
        for valid in self.VALID_WIDGET_TYPES:
            if valid.lower() == widget_type:
                return valid

        # Check if it's a partial match
        for valid in self.VALID_WIDGET_TYPES:
            if widget_type in valid or valid in widget_type:
                return valid

        # Simple edit distance check
        min_distance = float('inf')
        closest = None

        for valid in self.VALID_WIDGET_TYPES:
            distance = self._edit_distance(widget_type, valid)
            if distance < min_distance and distance <= 3:  # Max 3 character difference
                min_distance = distance
                closest = valid

        return closest

    def _edit_distance(self, s1: str, s2: str) -> int:
        """Calculate simple edit distance between strings"""
        if len(s1) < len(s2):
            s1, s2 = s2, s1

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]