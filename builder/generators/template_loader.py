"""Template loader for Flutter code generation"""

from typing import Dict, Optional
from pathlib import Path
from django.template import Template, Context
from django.template.loader import get_template


class TemplateLoader:
    """Loads and renders Flutter code templates"""

    # Default Flutter templates
    TEMPLATES = {
        'main_dart': '''import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'theme/app_theme.dart';
{{ imports }}

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '{{ app_name }}',
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
        {{ supported_locales }}
      ],
      locale: const Locale('{{ default_locale }}'),
      
      // Routes
      home: const {{ home_screen }}(),
      routes: {
{{ routes }}
      },
    );
  }
}
''',

        'screen_template': '''{{ imports }}

class {{ screen_name }}Screen extends StatelessWidget {
  const {{ screen_name }}Screen({super.key});

  @override
  Widget build(BuildContext context) {
    return {{ body_code }};
  }
}
''',

        'stateful_screen_template': '''{{ imports }}

class {{ screen_name }}Screen extends StatefulWidget {
  const {{ screen_name }}Screen({super.key});

  @override
  State<{{ screen_name }}Screen> createState() => _{{ screen_name }}ScreenState();
}

class _{{ screen_name }}ScreenState extends State<{{ screen_name }}Screen> {
  {{ state_variables }}

  @override
  void initState() {
    super.initState();
    {{ init_code }}
  }

  @override
  void dispose() {
    {{ dispose_code }}
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return {{ body_code }};
  }
  
  {{ methods }}
}
''',

        'custom_widget_template': '''import 'package:flutter/material.dart';
{{ imports }}

class {{ widget_name }} extends StatelessWidget {
  {{ properties }}
  
  const {{ widget_name }}({
    super.key,
    {{ constructor_params }}
  });

  @override
  Widget build(BuildContext context) {
    return {{ body_code }};
  }
}
''',
    }

    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize template loader

        Args:
            template_dir: Optional directory containing custom templates
        """
        self.template_dir = template_dir
        self.custom_templates = {}

        if template_dir and template_dir.exists():
            self._load_custom_templates()

    def _load_custom_templates(self):
        """Load custom templates from directory"""
        if not self.template_dir:
            return

        for template_file in self.template_dir.glob('*.dart.template'):
            template_name = template_file.stem  # Remove .dart.template
            with open(template_file, 'r', encoding='utf-8') as f:
                self.custom_templates[template_name] = f.read()

    def get_template(self, template_name: str) -> Optional[str]:
        """
        Get template content by name

        Args:
            template_name: Name of the template

        Returns:
            Template content or None if not found
        """
        # Check custom templates first
        if template_name in self.custom_templates:
            return self.custom_templates[template_name]

        # Fall back to default templates
        return self.TEMPLATES.get(template_name)

    def render_template(self, template_name: str, context: Dict) -> str:
        """
        Render a template with context

        Args:
            template_name: Name of the template
            context: Context dictionary for rendering

        Returns:
            Rendered template string
        """
        template_content = self.get_template(template_name)
        if not template_content:
            raise ValueError(f"Template '{template_name}' not found")

        # Use Django's template engine for rendering
        template = Template(template_content)
        rendered = template.render(Context(context))

        return rendered

    def render_django_template(self, template_path: str, context: Dict) -> str:
        """
        Render a Django template

        Args:
            template_path: Path to Django template
            context: Context dictionary

        Returns:
            Rendered template string
        """
        template = get_template(template_path)
        return template.render(context)


# Widget-specific templates
WIDGET_TEMPLATES = {
    'custom_button': '''
ElevatedButton.icon(
  onPressed: {{ on_pressed }},
  icon: Icon({{ icon }}),
  label: Text('{{ label }}'),
  style: ElevatedButton.styleFrom(
    backgroundColor: {{ background_color }},
    foregroundColor: {{ text_color }},
    padding: {{ padding }},
    shape: RoundedRectangleBorder(
      borderRadius: {{ border_radius }},
    ),
  ),
)
''',

    'custom_card': '''
Card(
  elevation: {{ elevation }},
  color: {{ color }},
  shape: RoundedRectangleBorder(
    borderRadius: {{ border_radius }},
  ),
  child: InkWell(
    onTap: {{ on_tap }},
    borderRadius: {{ border_radius }},
    child: Padding(
      padding: {{ padding }},
      child: {{ child }},
    ),
  ),
)
''',

    'custom_input': '''
TextFormField(
  controller: {{ controller }},
  decoration: InputDecoration(
    labelText: '{{ label }}',
    hintText: '{{ hint }}',
    prefixIcon: {{ prefix_icon }},
    suffixIcon: {{ suffix_icon }},
    border: {{ border }},
    filled: {{ filled }},
    fillColor: {{ fill_color }},
  ),
  validator: {{ validator }},
  onChanged: {{ on_changed }},
  obscureText: {{ obscure_text }},
  keyboardType: {{ keyboard_type }},
  maxLines: {{ max_lines }},
)
''',
}


def get_widget_template(widget_type: str) -> Optional[str]:
    """Get template for a specific widget type"""
    return WIDGET_TEMPLATES.get(widget_type)