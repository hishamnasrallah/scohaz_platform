import os
import json
from typing import Dict, List, Set
from simple_project.models import FlutterProject, Screen
from simple_builder.generators.widget_generator import WidgetGenerator


class FlutterGenerator:
    """Simplified Flutter project code generator"""

    def __init__(self, project: FlutterProject):
        self.project = project
        self.widget_generator = WidgetGenerator()
        self.generated_files = {}

    def generate_project(self) -> Dict[str, str]:
        """Generate all project files"""
        self.generated_files = {}

        self._generate_main_dart()
        self._generate_screens()
        self._generate_theme()
        self._generate_pubspec()

        return self.generated_files

    def _generate_main_dart(self):
        """Generate main.dart file"""
        screens = Screen.objects.filter(project=self.project)
        home_screen = screens.filter(is_home=True).first()

        if not home_screen and screens.exists():
            home_screen = screens.first()

        imports = [
            "import 'package:flutter/material.dart';",
            "import 'theme/app_theme.dart';",
        ]

        for screen in screens:
            imports.append(f"import 'screens/{self._to_snake_case(screen.name)}.dart';")

        routes = []
        for screen in screens:
            screen_class = self._to_pascal_case(screen.name)
            routes.append(f"        '{screen.route}': (context) => {screen_class}(),")

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
      initialRoute: '{initial_route}',
      routes: {{
{chr(10).join(routes) if routes else "        '/': (context) => Container(),"}
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
            self.widget_generator = WidgetGenerator()  # Reset imports

            has_scaffold = False
            screen_body_code = ""

            if screen.ui_structure and isinstance(screen.ui_structure, dict):
                if screen.ui_structure.get('type', '').lower() == 'scaffold':
                    has_scaffold = True
                    screen_body_code = self.widget_generator.generate_widget(screen.ui_structure, indent=2)
                else:
                    screen_body_code = self.widget_generator.generate_widget(screen.ui_structure, indent=3)
            else:
                screen_body_code = "        Center(\n          child: Text('Screen: {}'),\n        )".format(
                    screen.name)

            imports = list(self.widget_generator.imports)
            if "import 'package:flutter/material.dart';" not in imports:
                imports.insert(0, "import 'package:flutter/material.dart';")

            screen_class = self._to_pascal_case(screen.name)

            if has_scaffold:
                screen_content = f"""
{chr(10).join(imports)}

class {screen_class} extends StatelessWidget {{
  const {screen_class}({{Key? key}}) : super(key: key);

  @override
  Widget build(BuildContext context) {{
    return {screen_body_code.strip()};
  }}
}}
"""
            else:
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
          child: {screen_body_code},
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

        if not primary_color.startswith('#'):
            primary_color = '#2196F3'
        if not secondary_color.startswith('#'):
            secondary_color = '#03DAC6'

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
    );
  }}
}}
"""
        self.generated_files['lib/theme/app_theme.dart'] = theme_content.strip()

    def _generate_pubspec(self):
        """Generate pubspec.yaml"""
        app_name = self.project.package_name.split('.')[-1]
        app_name = app_name.lower().replace('-', '_').replace(' ', '_')

        if app_name and app_name[0].isdigit():
            app_name = 'app_' + app_name

        pubspec_content = f"""
name: {app_name}
description: {self.project.description or 'A new Flutter project.'}
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: ">=2.19.0 <4.0.0"

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.2

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^2.0.0

flutter:
  uses-material-design: true
"""
        self.generated_files['pubspec.yaml'] = pubspec_content.strip()

    def _to_snake_case(self, text: str) -> str:
        """Convert to snake_case"""
        import re
        text = text.replace('&', '_and_')
        text = text.replace(' ', '_').replace('-', '_')
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
        result = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        result = re.sub('_+', '_', result)
        result = result.strip('_')
        return result

    def _to_pascal_case(self, text: str) -> str:
        """Convert to PascalCase"""
        text = text.replace('&', 'And')
        text = text.replace('-', ' ').replace('_', ' ')
        words = text.split()
        return ''.join(word.capitalize() for word in words)