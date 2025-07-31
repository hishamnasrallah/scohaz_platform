"""
Main Flutter Code Generator
Orchestrates the conversion of UI JSON to Flutter project
"""

import json
import os
from typing import Dict, List, Any
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from utils.multilangual_helpers import read_translation
# from utils.multilingual_helpers import read_translation
from version.models import LocalVersion
from .widget_generator import WidgetGenerator
from .property_mapper import PropertyMapper


class FlutterGenerator:
    """Main class for generating Flutter code from UI JSON structure"""

    def __init__(self, project):
        """
        Initialize the Flutter generator

        Args:
            project: FlutterProject instance
        """
        from . import FlutterProjectBuilder

        self.project = project
        self.widget_generator = WidgetGenerator()
        self.property_mapper = PropertyMapper()
        self.project_builder = FlutterProjectBuilder(project)

        # Load translations for all supported languages
        self.translations = self._load_translations()

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent.parent / 'templates'
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """Load all translations for supported languages"""
        translations = {}

        # Load translations for each supported language
        for lang_version in self.project.supported_languages.all():
            try:
                translations[lang_version.lang] = read_translation(lang_version.lang)
            except Exception as e:
                print(f"Warning: Could not load translations for {lang_version.lang}: {e}")
                translations[lang_version.lang] = {}

        # Ensure default language is included
        if self.project.default_language not in translations:
            translations[self.project.default_language] = read_translation(
                self.project.default_language
            )

        return translations

    def generate_project(self) -> Dict[str, str]:
        """Alias for generate method for compatibility"""
        return self.generate()

    def generate_screen_code(self, screen_name: str, ui_structure: Dict, include_imports: bool = True) -> Dict:
        """Generate code for a single screen"""
        # Generate widget code
        widget_code = self.widget_generator.generate_widget(
            ui_structure,
            self.translations,
            indent_level=2
        )

        # Build screen file
        imports = self._collect_imports(ui_structure) if include_imports else []

        code = f'''import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
{chr(10).join(imports)}

class {screen_name} extends StatelessWidget {{
  const {screen_name}({{Key? key}}) : super(key: key);

  @override
  Widget build(BuildContext context) {{
    return {widget_code};
  }}
}}
'''

        return {
            'code': code,
            'imports': list(self.widget_generator.imports),
            'widget_tree': ui_structure,
            'translations_used': list(self.widget_generator.used_translation_keys)
        }
        files = {}

        try:
            # Parse UI structure
            ui_structure = self.project.ui_structure
            screens = ui_structure.get('screens', [])

            # Generate main.dart
            files['lib/main.dart'] = self._generate_main_dart(screens)

            # Generate screens
            for screen in screens:
                screen_name = screen.get('name', 'screen')
                file_path = f"lib/screens/{screen_name.lower()}.dart"
                files[file_path] = self._generate_screen(screen)

            # Generate localization files
            localization_files = self._generate_localization_files()
            files.update(localization_files)

            # Generate project files
            project_files = self.project_builder.generate_project_files()
            files.update(project_files)

            # Generate l10n.yaml for Flutter localization
            files['l10n.yaml'] = self._generate_l10n_yaml()

            return files

        except Exception as e:
            raise Exception(f"Failed to generate Flutter code: {str(e)}")

    def _generate_main_dart(self, screens: List[Dict]) -> str:
        """Generate main.dart file"""
        template = self.env.get_template('main_dart.jinja2')

        # Get home screen
        home_screen = next(
            (s for s in screens if s.get('is_home', False)),
            screens[0] if screens else None
        )

        return template.render(
            package_name=self.project.package_name,
            app_name=self.project.name,
            screens=screens,
            home_screen=home_screen,
            supported_languages=list(self.translations.keys()),
            default_language=self.project.default_language
        )

    def _generate_screen(self, screen: Dict) -> str:
        """Generate individual screen file"""
        screen_name = screen.get('name', 'Screen')
        root_widget = screen.get('root', {})

        # Generate widget code
        widget_code = self.widget_generator.generate_widget(
            root_widget,
            self.translations,
            indent_level=2
        )

        # Build screen file
        imports = self._collect_imports(root_widget)

        return f'''import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
{chr(10).join(imports)}

class {screen_name} extends StatelessWidget {{
  const {screen_name}({{Key? key}}) : super(key: key);

  @override
  Widget build(BuildContext context) {{
    return {widget_code};
  }}
}}
'''

    def _collect_imports(self, widget: Dict) -> List[str]:
        """Collect required imports based on widgets used"""
        imports = set()

        def _process_widget(w):
            widget_type = w.get('type', '')

            # Add widget-specific imports
            if widget_type == 'image':
                imports.add("import 'package:cached_network_image/cached_network_image.dart';")

            # Process children
            if 'children' in w:
                for child in w['children']:
                    _process_widget(child)
            elif 'body' in w:
                _process_widget(w['body'])
            elif 'child' in w:
                _process_widget(w['child'])

        _process_widget(widget)
        return sorted(list(imports))

    def _generate_localization_files(self) -> Dict[str, str]:
        """Generate ARB files for each language"""
        files = {}

        for lang, translations in self.translations.items():
            arb_content = {
                "@@locale": lang,
                **translations
            }

            # Format ARB file content
            content = json.dumps(arb_content, indent=2, ensure_ascii=False)
            files[f"lib/l10n/app_{lang}.arb"] = content

        return files

    def _generate_l10n_yaml(self) -> str:
        """Generate l10n.yaml configuration file"""
        return f'''arb-dir: lib/l10n
template-arb-file: app_{self.project.default_language}.arb
output-localization-file: app_localizations.dart
synthetic-package: false
output-dir: lib/l10n
output-class: AppLocalizations
'''

    def validate_structure(self, ui_structure: Dict) -> List[str]:
        """
        Validate UI structure before generation

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not ui_structure.get('screens'):
            errors.append("UI structure must contain at least one screen")

        for i, screen in enumerate(ui_structure.get('screens', [])):
            if not screen.get('name'):
                errors.append(f"Screen {i} must have a name")
            if not screen.get('root'):
                errors.append(f"Screen {screen.get('name', i)} must have a root widget")

        return errors