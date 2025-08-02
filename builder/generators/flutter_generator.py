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

        # Generate localization files ONLY if languages are configured
        if self.project.supported_languages.exists() and self.project.supported_languages.count() > 0:
            self._generate_localization()

        return self.generated_files

    def _generate_main_dart(self):
        """Generate main.dart file"""
        screens = Screen.objects.filter(project=self.project)
        home_screen = screens.filter(is_home=True).first()

        # If no home screen, use the first screen
        if not home_screen and screens.exists():
            home_screen = screens.first()

        # Check if we have localizations
        has_localizations = self.project.supported_languages.exists() and self.project.supported_languages.count() > 0

        imports = [
            "import 'package:flutter/material.dart';",
            "import 'theme/app_theme.dart';",
        ]

        # Add screen imports
        for screen in screens:
            imports.append(f"import 'screens/{self._to_snake_case(screen.name)}.dart';")

        # Add localization imports ONLY if needed
        if has_localizations:
            imports.extend([
                "import 'package:flutter_localizations/flutter_localizations.dart';",
                "import 'package:flutter_gen/gen_l10n/app_localizations.dart';",
            ])

        # Build routes
        routes = []
        for screen in screens:
            screen_class = self._to_pascal_case(screen.name)
            routes.append(f"        '{screen.route}': (context) => {screen_class}(),")

        # Build MaterialApp with conditional localization
        localization_props = ""
        if has_localizations:
            localization_props = """      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
"""

        # Determine initial route
        initial_route = home_screen.route if home_screen else '/'

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
{localization_props}      initialRoute: '{initial_route}',
      routes: {{
{chr(10).join(routes) if routes else "        '/': (context) => Container(),"}
      }},
      onUnknownRoute: (settings) {{
        return MaterialPageRoute(
          builder: (context) => Scaffold(
            body: Center(
              child: Text('Route ${{settings.name}} not found'),
            ),
          ),
        );
      }},
    );
  }}
}}
"""
        self.generated_files['lib/main.dart'] = main_content.strip()

    def _generate_screens(self):
        """Generate screen files"""
        screens = Screen.objects.filter(project=self.project)
        has_localizations = self.project.supported_languages.exists() and self.project.supported_languages.count() > 0

        for screen in screens:
            self.widget_generator = WidgetGenerator()  # Reset imports for each screen

            # Generate body widget
            if screen.ui_structure and isinstance(screen.ui_structure, dict) and 'type' in screen.ui_structure:
                body_code = self.widget_generator.generate_widget(screen.ui_structure, indent=3)
            else:
                # Fallback for invalid structure
                body_code = "        Center(\n          child: Text('Invalid screen structure'),\n        )"

            # Get imports
            imports = list(self.widget_generator.imports)
            if "import 'package:flutter/material.dart';" not in imports:
                imports.insert(0, "import 'package:flutter/material.dart';")

            # Only add localization import if actually needed
            if has_localizations:
                imports.append("import 'package:flutter_gen/gen_l10n/app_localizations.dart';")

            screen_class = self._to_pascal_case(screen.name)

            screen_content = f"""
{chr(10).join(imports)}

class {screen_class} extends StatelessWidget {{
  const {screen_class}({{Key? key}}) : super(key: key);

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: SingleChildScrollView(
          child: {body_code},
        ),
      ),
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

        # Ensure colors are in correct format
        if not primary_color.startswith('#'):
            primary_color = '#2196F3'  # Default blue
        if not secondary_color.startswith('#'):
            secondary_color = '#03DAC6'  # Default teal

        theme_content = f"""
import 'package:flutter/material.dart';

class AppTheme {{
  static ThemeData get lightTheme {{
    final primaryColor = Color(0x{primary_color.replace('#', 'FF')});
    final secondaryColor = Color(0x{secondary_color.replace('#', 'FF')});
    
    return ThemeData(
      primarySwatch: MaterialColor(
        primaryColor.value,
        <int, Color>{{
          50: primaryColor.withOpacity(0.1),
          100: primaryColor.withOpacity(0.2),
          200: primaryColor.withOpacity(0.3),
          300: primaryColor.withOpacity(0.4),
          400: primaryColor.withOpacity(0.5),
          500: primaryColor.withOpacity(0.6),
          600: primaryColor.withOpacity(0.7),
          700: primaryColor.withOpacity(0.8),
          800: primaryColor.withOpacity(0.9),
          900: primaryColor.withOpacity(1.0),
        }},
      ),
      primaryColor: primaryColor,
      colorScheme: ColorScheme.light(
        primary: primaryColor,
        secondary: secondaryColor,
      ),
      scaffoldBackgroundColor: Colors.grey[50],
      appBarTheme: AppBarTheme(
        backgroundColor: primaryColor,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryColor,
          foregroundColor: Colors.white,
          padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
    );
  }}
  
  static ThemeData get darkTheme {{
    final primaryColor = Color(0x{primary_color.replace('#', 'FF')});
    final secondaryColor = Color(0x{secondary_color.replace('#', 'FF')});
    
    return ThemeData(
      brightness: Brightness.dark,
      primaryColor: primaryColor,
      colorScheme: ColorScheme.dark(
        primary: primaryColor,
        secondary: secondaryColor,
      ),
      scaffoldBackgroundColor: Colors.grey[900],
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.grey[900],
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryColor,
          foregroundColor: Colors.white,
          padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
    );
  }}
}}
"""
        self.generated_files['lib/theme/app_theme.dart'] = theme_content.strip()

    def _generate_constants(self):
        """Generate constants file"""
        constants_content = f"""
class AppConstants {{
  static const String appName = '{self.project.name}';
  static const String packageName = '{self.project.package_name}';
  static const String defaultLanguage = '{self.project.default_language}';
}}
"""
        self.generated_files['lib/constants/app_constants.dart'] = constants_content.strip()

    def _generate_pubspec(self):
        """Generate pubspec.yaml"""
        dependencies = {
            'flutter': {'sdk': 'flutter'},
            'cupertino_icons': '^1.0.2',
        }

        # Only add localization dependencies if languages are configured
        has_localizations = self.project.supported_languages.exists() and self.project.supported_languages.count() > 0
        if has_localizations:
            dependencies['flutter_localizations'] = {'sdk': 'flutter'}
            dependencies['intl'] = 'any'  # Let Flutter resolve the version

        # Clean package name for pubspec
        app_name = self.project.package_name.split('.')[-1]
        # Ensure it's a valid Dart package name
        app_name = app_name.lower().replace('-', '_').replace(' ', '_')

        pubspec_content = f"""
name: {app_name}
description: {self.project.description or 'A new Flutter project.'}
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: ">=2.19.0 <4.0.0"

dependencies:
{self._format_yaml_dict(dependencies, indent=2)}

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^2.0.0

flutter:
  uses-material-design: true{chr(10) + '  generate: true' if has_localizations else ''}
"""
        self.generated_files['pubspec.yaml'] = pubspec_content.strip()

    def _generate_localization(self):
        """Generate localization files"""
        # Double-check we actually have languages
        if not self.project.supported_languages.exists() or self.project.supported_languages.count() == 0:
            return

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
        # First, handle spaces and special characters
        text = text.replace('&', '_and_')
        text = text.replace(' ', '_').replace('-', '_')
        # Then handle camelCase
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
        result = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        # Remove duplicate underscores
        result = re.sub('_+', '_', result)
        return result

    def _to_pascal_case(self, text: str) -> str:
        """Convert to PascalCase"""
        # Handle various separators and special characters
        # Replace special characters with spaces
        text = text.replace('&', 'And')
        text = text.replace('-', ' ').replace('_', ' ')
        words = text.split()
        return ''.join(word.capitalize() for word in words)

    def _to_camel_case(self, text: str) -> str:
        """Convert to camelCase"""
        words = text.split('_')
        return words[0].lower() + ''.join(word.capitalize() for word in words[1:])

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