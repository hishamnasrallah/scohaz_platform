# File: builder/generators/flutter_generator.py

import os
import json
from typing import Dict, List, Set
from projects.models import FlutterProject, Screen
from builder.generators.widget_generator import WidgetGenerator
from utils.multilingual_helpers import read_translation


class FlutterGenerator:
    """Generates complete Flutter project code"""

    def __init__(self, project: FlutterProject):
        self.project = project
        self.widget_generator = WidgetGenerator()
        self.generated_files = {}

    def generate_project(self) -> Dict[str, str]:
        """Generate all project files"""
        self.generated_files = {}

        # Generate main.dart
        self._generate_main_dart()

        # Generate screens
        self._generate_screens()

        # Generate theme
        self._generate_theme()

        # Generate constants
        self._generate_constants()

        # Generate pubspec.yaml
        self._generate_pubspec()

        # Generate localization files
        if self.project.supported_languages.exists():
            self._generate_localization()

        return self.generated_files

    def _generate_main_dart(self):
        """Generate main.dart file"""
        screens = Screen.objects.filter(project=self.project)
        home_screen = screens.filter(is_home=True).first()

        imports = [
            "import 'package:flutter/material.dart';",
            "import 'theme/app_theme.dart';",
        ]

        # Add screen imports
        for screen in screens:
            imports.append(f"import 'screens/{self._to_snake_case(screen.name)}.dart';")

        # Add localization imports if needed
        if self.project.supported_languages.exists():
            imports.extend([
                "import 'package:flutter_localizations/flutter_localizations.dart';",
                "import 'package:flutter_gen/gen_l10n/app_localizations.dart';",
            ])

        # Build routes
        routes = []
        for screen in screens:
            screen_class = self._to_pascal_case(screen.name)
            routes.append(f"      '{screen.route}': (context) => {screen_class}(),")

        main_content = f"""
{chr(10).join(imports)}

void main() {{
  runApp(MyApp());
}}

class MyApp extends StatelessWidget {{
  @override
  Widget build(BuildContext context) {{
    return MaterialApp(
      title: '{self.project.name}',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      debugShowCheckedModeBanner: false,
      {'localizationsDelegates: AppLocalizations.localizationsDelegates,' if self.project.supported_languages.exists() else ''}
      {'supportedLocales: AppLocalizations.supportedLocales,' if self.project.supported_languages.exists() else ''}
      initialRoute: '{home_screen.route if home_screen else "/"}',
      routes: {{
{chr(10).join(routes)}
      }},
    );
  }}
}}
"""
        self.generated_files['lib/main.dart'] = main_content.strip()

    def _generate_screens(self):
        """Generate screen files"""
        screens = Screen.objects.filter(project=self.project)

        for screen in screens:
            self.widget_generator = WidgetGenerator()  # Reset imports for each screen

            # Generate body widget
            body_code = self.widget_generator.generate_widget(screen.ui_structure, indent=3)

            # Get imports
            imports = list(self.widget_generator.imports)
            if "import 'package:flutter/material.dart';" not in imports:
                imports.insert(0, "import 'package:flutter/material.dart';")

            if self.project.supported_languages.exists():
                imports.append("import 'package:flutter_gen/gen_l10n/app_localizations.dart';")

            screen_class = self._to_pascal_case(screen.name)

            screen_content = f"""
{chr(10).join(imports)}

class {screen_class} extends StatelessWidget {{
  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      body: 
{body_code},
    );
  }}
}}
"""

            filename = f"lib/screens/{self._to_snake_case(screen.name)}.dart"
            self.generated_files[filename] = screen_content.strip()

    def _generate_theme(self):
        """Generate theme file"""
        primary_color = self.project.primary_color
        secondary_color = self.project.secondary_color

        theme_content = f"""
import 'package:flutter/material.dart';

class AppTheme {{
  static ThemeData get lightTheme {{
    return ThemeData(
      primarySwatch: MaterialColor(
        0x{primary_color.replace('#', 'FF')},
        <int, Color>{{}},
      ),
      primaryColor: Color(0x{primary_color.replace('#', 'FF')}),
      colorScheme: ColorScheme.light(
        primary: Color(0x{primary_color.replace('#', 'FF')}),
        secondary: Color(0x{secondary_color.replace('#', 'FF')}),
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: Color(0x{primary_color.replace('#', 'FF')}),
        foregroundColor: Colors.white,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: Color(0x{primary_color.replace('#', 'FF')}),
        ),
      ),
    );
  }}
  
  static ThemeData get darkTheme {{
    return ThemeData(
      brightness: Brightness.dark,
      primaryColor: Color(0x{primary_color.replace('#', 'FF')}),
      colorScheme: ColorScheme.dark(
        primary: Color(0x{primary_color.replace('#', 'FF')}),
        secondary: Color(0x{secondary_color.replace('#', 'FF')}),
      ),
    );
  }}
}}
"""
        self.generated_files['lib/theme/app_theme.dart'] = theme_content.strip()

    def _generate_constants(self):
        """Generate constants file"""
        constants_content = """
class AppConstants {
  static const String appName = '%s';
  static const String packageName = '%s';
  static const String defaultLanguage = '%s';
}
""" % (self.project.name, self.project.package_name, self.project.default_language)

        self.generated_files['lib/constants/app_constants.dart'] = constants_content.strip()

    def _generate_pubspec(self):
        """Generate pubspec.yaml"""
        dependencies = {
            'flutter': {'sdk': 'flutter'},
            'cupertino_icons': '^1.0.2',
        }

        if self.project.supported_languages.exists():
            dependencies['flutter_localizations'] = {'sdk': 'flutter'}
            dependencies['intl'] = '^0.18.0'

        pubspec_content = f"""
name: {self.project.package_name.split('.')[-1]}
description: {self.project.description or 'A new Flutter project.'}
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: ">=2.19.0 <3.0.0"

dependencies:
{self._format_yaml_dict(dependencies, indent=2)}

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^2.0.0

flutter:
  uses-material-design: true
  generate: true
"""
        self.generated_files['pubspec.yaml'] = pubspec_content.strip()

    def _generate_localization(self):
        """Generate localization files"""
        # Generate l10n.yaml
        l10n_content = """
arb-dir: lib/l10n
template-arb-file: app_en.arb
output-localization-file: app_localizations.dart
"""
        self.generated_files['l10n.yaml'] = l10n_content.strip()

        # Generate ARB files for each language
        for lang_version in self.project.supported_languages.all():
            lang_code = lang_version.lang

            # Try to read translations, handle if function doesn't exist
            try:
                translations = read_translation(lang_code)
            except:
                translations = {}

            arb_content = {
                '@@locale': lang_code,
            }

            # Add translations
            if translations:
                for key, value in translations.items():
                    # Convert key to camelCase for Flutter
                    flutter_key = self._to_camel_case(key)
                    arb_content[flutter_key] = value

            # Add default keys if not present
            if 'appTitle' not in arb_content:
                arb_content['appTitle'] = self.project.name

            filename = f"lib/l10n/app_{lang_code}.arb"
            self.generated_files[filename] = json.dumps(arb_content, ensure_ascii=False, indent=2)

    def _to_snake_case(self, text: str) -> str:
        """Convert to snake_case"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower().replace(' ', '_')

    def _to_pascal_case(self, text: str) -> str:
        """Convert to PascalCase"""
        return ''.join(word.capitalize() for word in text.split())

    def _to_camel_case(self, text: str) -> str:
        """Convert to camelCase"""
        words = text.split('_')
        return words[0] + ''.join(word.capitalize() for word in words[1:])

    def _format_yaml_dict(self, d: Dict, indent: int = 0) -> str:
        """Format dictionary as YAML"""
        lines = []
        spaces = '  ' * indent
        for key, value in d.items():
            if isinstance(value, dict):
                lines.append(f"{spaces}{key}:")
                if 'sdk' in value:
                    lines.append(f"{spaces}  sdk: {value['sdk']}")
                else:
                    lines.append(self._format_yaml_dict(value, indent + 1))
            else:
                lines.append(f"{spaces}{key}: {value}")
        return '\n'.join(lines)