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
        self.project = project
        self.widget_generator = WidgetGenerator()
        self.property_mapper = PropertyMapper()

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
        """Generate complete Flutter project files"""
        return self.generate()

    def generate(self) -> Dict[str, str]:
        """Generate complete Flutter project files"""
        files = {}

        try:
            # Get screens from the database
            screens = list(self.project.screens.all())

            if not screens:
                # Create a default home screen if none exists
                from projects.models import Screen
                default_screen = Screen.objects.create(
                    project=self.project,
                    name="Home",
                    route="/",
                    is_home=True,
                    ui_structure={
                        "type": "scaffold",
                        "properties": {
                            "appBar": {
                                "title": self.project.name,
                                "backgroundColor": "#2196F3"
                            }
                        },
                        "body": {
                            "type": "center",
                            "child": {
                                "type": "text",
                                "properties": {
                                    "content": f"Welcome to {self.project.name}",
                                    "style": {
                                        "fontSize": 24,
                                        "fontWeight": "bold"
                                    }
                                }
                            }
                        }
                    }
                )
                screens = [default_screen]

            # Generate main.dart
            files['lib/main.dart'] = self._generate_main_dart_new(screens)

            # Generate screens
            for screen in screens:
                screen_name = self._sanitize_screen_name(screen.name)
                file_path = f"lib/screens/{screen_name.lower()}_screen.dart"
                files[file_path] = self._generate_screen_new(screen)

            # Generate localization files
            localization_files = self._generate_localization_files()
            files.update(localization_files)

            # Generate project files
            project_files = self._generate_project_files()
            files.update(project_files)

            # Generate l10n.yaml for Flutter localization
            files['l10n.yaml'] = self._generate_l10n_yaml()

            # Generate pubspec.yaml
            files['pubspec.yaml'] = self._generate_pubspec_yaml()

            return files

        except Exception as e:
            raise Exception(f"Failed to generate Flutter code: {str(e)}")

    def _sanitize_screen_name(self, name: str) -> str:
        """Convert screen name to valid Dart class name"""
        # Remove special characters and spaces
        name = ''.join(c if c.isalnum() else ' ' for c in name)
        # Convert to PascalCase
        return ''.join(word.capitalize() for word in name.split())

    def _generate_main_dart_new(self, screens) -> str:
        """Generate main.dart file"""
        # Find home screen
        home_screen = None
        for screen in screens:
            if screen.is_home:
                home_screen = screen
                break

        if not home_screen and screens:
            home_screen = screens[0]

        # Build imports
        imports = []
        for screen in screens:
            screen_name = self._sanitize_screen_name(screen.name)
            imports.append(f"import 'screens/{screen_name.lower()}_screen.dart';")

        # Generate main.dart content
        content = f'''import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'theme/app_theme.dart';
{chr(10).join(imports)}

void main() {{
  runApp(const MyApp());
}}

class MyApp extends StatelessWidget {{
  const MyApp({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return MaterialApp(
      title: '{self.project.name}',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      debugShowCheckedModeBanner: false,
      
      // Localization
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [
        {', '.join([f"Locale('{lang}')" for lang in self.translations.keys()])}
      ],
      
      home: const {self._sanitize_screen_name(home_screen.name)}Screen(),
      
      routes: {{
        {self._generate_routes(screens)}
      }},
    );
  }}
}}
'''
        return content

    def _generate_routes(self, screens) -> str:
        """Generate route definitions"""
        routes = []
        for screen in screens:
            if not screen.is_home:  # Home is already set
                screen_name = self._sanitize_screen_name(screen.name)
                route = screen.route or f'/{screen_name.lower()}'
                routes.append(f"'{route}': (context) => const {screen_name}Screen(),")
        return '\n        '.join(routes)

# In flutter_generator.py, update the _generate_screen_new method:

    def _generate_screen_new(self, screen) -> str:
        """Generate individual screen file"""
        screen_name = self._sanitize_screen_name(screen.name)

        # Get UI structure from the screen model
        ui_structure = screen.ui_structure
        if not ui_structure or not isinstance(ui_structure, dict):
            # Create a more complete default structure
            ui_structure = {
                'type': 'scaffold',
                'properties': {
                    'appBar': {
                        'title': screen.name,
                        'backgroundColor': '#2196F3',
                        'elevation': 4,
                        'centerTitle': True
                    },
                    'backgroundColor': '#FFFFFF'
                },
                'body': {
                    'type': 'center',
                    'child': {
                        'type': 'column',
                        'properties': {
                            'mainAxisAlignment': 'center',
                            'crossAxisAlignment': 'center'
                        },
                        'children': [
                            {
                                'type': 'icon',
                                'properties': {
                                    'icon': 'home',
                                    'size': 64,
                                    'color': '#2196F3'
                                }
                            },
                            {
                                'type': 'sizedbox',
                                'properties': {
                                    'height': 20
                                }
                            },
                            {
                                'type': 'text',
                                'properties': {
                                    'content': f'Welcome to {screen.name}',
                                    'style': {
                                        'fontSize': 24,
                                        'fontWeight': 'bold'
                                    }
                                }
                            }
                        ]
                    }
                }
            }

        # Generate widget code - pass translations as context
        widget_code = self.widget_generator.generate_widget(
            ui_structure,
            {'translations': self.translations}
        )

        # Build screen file
        imports = self._collect_imports(ui_structure)

        return f'''import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
{chr(10).join(imports)}

class {screen_name}Screen extends StatelessWidget {{
  const {screen_name}Screen({{Key? key}}) : super(key: key);

  @override
  Widget build(BuildContext context) {{
    {widget_code}
  }}
}}
'''

    # Also update the generate_screen_code method:


    def generate_screen_code(self, screen_name: str, ui_structure: Dict, include_imports: bool = True) -> Dict:
        """Generate code for a single screen"""
        # Generate widget code
        widget_code = self.widget_generator.generate_widget(
            ui_structure,
            {'translations': self.translations}  # Pass as context
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
    {widget_code}
  }}
}}
'''

        return {
            'code': code,
            'imports': list(self.widget_generator.imports),
            'widget_tree': ui_structure,
            'translations_used': list(self.widget_generator.used_translation_keys)
        }