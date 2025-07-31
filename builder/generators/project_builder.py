"""Flutter project builder that generates complete Flutter projects"""

import os
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from django.conf import settings
from version.models import LocalVersion
from utils.multilangual_helpers import read_translation

from .widget_generator import WidgetGenerator
from .property_mapper import PropertyMapper
from .flutter_generator import FlutterGenerator


class FlutterProjectBuilder:
    """Builds complete Flutter projects from UI structure"""

    def __init__(self, project):
        self.project = project
        self.widget_generator = WidgetGenerator()
        self.property_mapper = PropertyMapper()
        self.flutter_generator = FlutterGenerator(project)
        self.output_dir = None
        self.build_errors = []
        self.build_warnings = []

    def build_project(self, output_path: Optional[str] = None) -> Tuple[bool, str, List[str]]:
        """
        Build the complete Flutter project

        Returns:
            Tuple of (success: bool, output_path: str, errors: List[str])
        """
        try:
            # Set output directory
            if output_path:
                self.output_dir = Path(output_path)
            else:
                self.output_dir = Path(settings.MEDIA_ROOT) / 'flutter_projects' / f'{self.project.package_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Generate all project files
            print(f"Generating Flutter project for: {self.project.name}")
            files = self.flutter_generator.generate_project()

            # Write files to disk
            for file_path, content in files.items():
                self._write_file(file_path, content)

            # Generate additional files
            self._generate_readme()
            self._generate_gitignore()
            self._generate_analysis_options()
            self._generate_android_files()
            self._generate_ios_files()

            # Copy assets if any
            self._copy_assets()

            # Run Flutter commands if Flutter SDK is available
            if self._is_flutter_available():
                self._run_flutter_commands()

            print(f"Project generated successfully at: {self.output_dir}")
            return True, str(self.output_dir), self.build_errors

        except Exception as e:
            error_msg = f"Failed to build project: {str(e)}"
            self.build_errors.append(error_msg)
            print(error_msg)
            return False, "", self.build_errors

    def build_apk(self, build_config: Optional[Dict] = None) -> Tuple[bool, str, List[str]]:
        """
        Build APK from the Flutter project

        Returns:
            Tuple of (success: bool, apk_path: str, errors: List[str])
        """
        if not self.output_dir or not self.output_dir.exists():
            # First build the project
            success, project_path, errors = self.build_project()
            if not success:
                return False, "", errors

        if not self._is_flutter_available():
            self.build_errors.append("Flutter SDK not found. Please install Flutter to build APK.")
            return False, "", self.build_errors

        try:
            # Change to project directory
            os.chdir(self.output_dir)

            # Get dependencies
            print("Getting Flutter dependencies...")
            result = subprocess.run(
                ['flutter', 'pub', 'get'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.build_errors.append(f"Failed to get dependencies: {result.stderr}")
                return False, "", self.build_errors

            # Build APK
            print("Building APK...")
            build_mode = build_config.get('build_mode', 'release') if build_config else 'release'

            build_command = ['flutter', 'build', 'apk', f'--{build_mode}']

            # Add additional build flags
            if build_config:
                if build_config.get('split_per_abi'):
                    build_command.append('--split-per-abi')

                if build_config.get('target_platform'):
                    build_command.extend(['--target-platform', build_config['target_platform']])

            result = subprocess.run(
                build_command,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.build_errors.append(f"Failed to build APK: {result.stderr}")
                return False, "", self.build_errors

            # Find the APK file
            apk_path = self._find_apk_file(build_mode)
            if not apk_path:
                self.build_errors.append("APK file not found after build")
                return False, "", self.build_errors

            print(f"APK built successfully: {apk_path}")
            return True, apk_path, self.build_errors

        except Exception as e:
            error_msg = f"Failed to build APK: {str(e)}"
            self.build_errors.append(error_msg)
            print(error_msg)
            return False, "", self.build_errors

    def _write_file(self, file_path: str, content: str):
        """Write file to disk"""
        full_path = self.output_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _generate_readme(self):
        """Generate README.md file"""
        readme_content = f"""# {self.project.name}

{self.project.description or 'A Flutter application built with Flutter Visual Builder'}

## Getting Started

This project was generated using Flutter Visual Builder.

### Prerequisites

- Flutter SDK (3.0.0 or higher)
- Android Studio or VS Code with Flutter extensions
- Android SDK for building Android apps

### Installation

1. Get Flutter dependencies:
   ```bash
   flutter pub get
   ```

2. Run the app:
   ```bash
   flutter run
   ```

### Building

To build a release APK:
```bash
flutter build apk --release
```

To build for specific architectures:
```bash
flutter build apk --split-per-abi
```

## Supported Languages

This app supports the following languages:
{self._generate_language_list()}

## Project Structure

```
lib/
├── main.dart              # App entry point
├── screens/              # Screen widgets
├── l10n/                 # Localization files
├── theme/                # App theme
└── constants/            # App constants
```

## Features

{self._generate_features_list()}

## License

This project is generated code and can be used freely.
"""
        self._write_file('README.md', readme_content)

    def _generate_language_list(self) -> str:
        """Generate list of supported languages"""
        languages = []
        for lang in self.project.supported_languages.all():
            languages.append(f"- {lang.get_lang_display()} ({lang.lang})")
        return '\n'.join(languages) if languages else "- English (en)"

    def _generate_features_list(self) -> str:
        """Generate list of app features based on screens"""
        features = []
        for screen in self.project.screen_set.all():
            features.append(f"- {screen.name} screen")

        if self.project.supported_languages.count() > 1:
            features.append("- Multi-language support")

        return '\n'.join(features) if features else "- Basic Flutter app"

    def _generate_gitignore(self):
        """Generate .gitignore file"""
        gitignore_content = """# Miscellaneous
*.class
*.log
*.pyc
*.swp
.DS_Store
.atom/
.buildlog/
.history
.svn/
migrate_working_dir/

# IntelliJ related
*.iml
*.ipr
*.iws
.idea/

# VS Code related
.vscode/

# Flutter/Dart/Pub related
**/doc/api/
**/ios/Flutter/.last_build_id
.dart_tool/
.flutter-plugins
.flutter-plugins-dependencies
.packages
.pub-cache/
.pub/
/build/

# Symbolication related
app.*.symbols

# Obfuscation related
app.*.map.json

# Android Studio will place build artifacts here
/android/app/debug
/android/app/profile
/android/app/release
"""
        self._write_file('.gitignore', gitignore_content)

    def _generate_analysis_options(self):
        """Generate analysis_options.yaml"""
        analysis_options = """include: package:flutter_lints/flutter.yaml

linter:
  rules:
    - prefer_const_constructors
    - prefer_const_declarations
    - prefer_const_literals_to_create_immutables
    - prefer_final_fields
    - use_key_in_widget_constructors
    - avoid_print
"""
        self._write_file('analysis_options.yaml', analysis_options)

    def _generate_android_files(self):
        """Generate Android-specific files"""
        # AndroidManifest.xml
        manifest_content = f"""<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application
        android:label="{self.project.name}"
        android:name="${{applicationName}}"
        android:icon="@mipmap/ic_launcher">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:theme="@style/LaunchTheme"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|smallestScreenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode"
            android:hardwareAccelerated="true"
            android:windowSoftInputMode="adjustResize">
            <meta-data
              android:name="io.flutter.embedding.android.NormalTheme"
              android:resource="@style/NormalTheme"
              />
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
        <meta-data
            android:name="flutterEmbedding"
            android:value="2" />
    </application>
</manifest>
"""
        self._write_file('android/app/src/main/AndroidManifest.xml', manifest_content)

        # build.gradle (app level)
        build_gradle = f"""def localProperties = new Properties()
def localPropertiesFile = rootProject.file('local.properties')
if (localPropertiesFile.exists()) {{
    localPropertiesFile.withReader('UTF-8') {{ reader ->
        localProperties.load(reader)
    }}
}}

def flutterRoot = localProperties.getProperty('flutter.sdk')
if (flutterRoot == null) {{
    throw new GradleException("Flutter SDK not found. Define location with flutter.sdk in the local.properties file.")
}}

def flutterVersionCode = localProperties.getProperty('flutter.versionCode')
if (flutterVersionCode == null) {{
    flutterVersionCode = '1'
}}

def flutterVersionName = localProperties.getProperty('flutter.versionName')
if (flutterVersionName == null) {{
    flutterVersionName = '1.0'
}}

apply plugin: 'com.android.application'
apply plugin: 'kotlin-android'
apply from: "$flutterRoot/packages/flutter_tools/gradle/flutter.gradle"

android {{
    compileSdkVersion flutter.compileSdkVersion
    ndkVersion flutter.ndkVersion

    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }}

    kotlinOptions {{
        jvmTarget = '1.8'
    }}

    sourceSets {{
        main.java.srcDirs += 'src/main/kotlin'
    }}

    defaultConfig {{
        applicationId "{self.project.package_name}"
        minSdkVersion flutter.minSdkVersion
        targetSdkVersion flutter.targetSdkVersion
        versionCode flutterVersionCode.toInteger()
        versionName flutterVersionName
    }}

    buildTypes {{
        release {{
            signingConfig signingConfigs.debug
        }}
    }}
}}

flutter {{
    source '../..'
}}

dependencies {{
    implementation "org.jetbrains.kotlin:kotlin-stdlib-jdk7:$kotlin_version"
}}
"""
        self._write_file('android/app/build.gradle', build_gradle)

    def _generate_ios_files(self):
        """Generate iOS-specific files (Info.plist)"""
        info_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>$(DEVELOPMENT_LANGUAGE)</string>
    <key>CFBundleDisplayName</key>
    <string>{self.project.name}</string>
    <key>CFBundleExecutable</key>
    <string>$(EXECUTABLE_NAME)</string>
    <key>CFBundleIdentifier</key>
    <string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>{self.project.package_name.split('.')[-1]}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>$(FLUTTER_BUILD_NAME)</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleVersion</key>
    <string>$(FLUTTER_BUILD_NUMBER)</string>
    <key>LSRequiresIPhoneOS</key>
    <true/>
    <key>UILaunchStoryboardName</key>
    <string>LaunchScreen</string>
    <key>UIMainStoryboardFile</key>
    <string>Main</string>
    <key>UISupportedInterfaceOrientations</key>
    <array>
        <string>UIInterfaceOrientationPortrait</string>
        <string>UIInterfaceOrientationLandscapeLeft</string>
        <string>UIInterfaceOrientationLandscapeRight</string>
    </array>
    <key>UISupportedInterfaceOrientations~ipad</key>
    <array>
        <string>UIInterfaceOrientationPortrait</string>
        <string>UIInterfaceOrientationPortraitUpsideDown</string>
        <string>UIInterfaceOrientationLandscapeLeft</string>
        <string>UIInterfaceOrientationLandscapeRight</string>
    </array>
    <key>UIViewControllerBasedStatusBarAppearance</key>
    <false/>
    <key>CADisableMinimumFrameDurationOnPhone</key>
    <true/>
    <key>UIApplicationSupportsIndirectInputEvents</key>
    <true/>
</dict>
</plist>
"""
        self._write_file('ios/Runner/Info.plist', info_plist)

    def _copy_assets(self):
        """Copy project assets if any"""
        # This would copy any uploaded assets to the Flutter project
        # For now, we'll just create the assets directory
        assets_dir = self.output_dir / 'assets' / 'images'
        assets_dir.mkdir(parents=True, exist_ok=True)

        # Create a placeholder .gitkeep file
        (assets_dir / '.gitkeep').touch()

    def _run_flutter_commands(self):
        """Run Flutter commands to set up the project"""
        try:
            os.chdir(self.output_dir)

            # Create Flutter project structure
            print("Creating Flutter project structure...")
            result = subprocess.run(
                ['flutter', 'create', '--project-name', self.project.package_name.split('.')[-1],
                 '--org', '.'.join(self.project.package_name.split('.')[:-1]), '.'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.build_warnings.append(f"Flutter create warning: {result.stderr}")

            # Get packages
            print("Getting Flutter packages...")
            result = subprocess.run(
                ['flutter', 'pub', 'get'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.build_warnings.append(f"Flutter pub get warning: {result.stderr}")

        except Exception as e:
            self.build_warnings.append(f"Flutter command warning: {str(e)}")

    def _is_flutter_available(self) -> bool:
        """Check if Flutter SDK is available"""
        try:
            result = subprocess.run(
                ['flutter', '--version'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _find_apk_file(self, build_mode: str) -> Optional[str]:
        """Find the generated APK file"""
        apk_dir = self.output_dir / 'build' / 'app' / 'outputs' / 'flutter-apk'

        # Look for APK files
        apk_patterns = [
            f'app-{build_mode}.apk',
            'app.apk',
            f'app-arm64-v8a-{build_mode}.apk',
            f'app-armeabi-v7a-{build_mode}.apk',
            f'app-x86_64-{build_mode}.apk'
        ]

        for pattern in apk_patterns:
            apk_path = apk_dir / pattern
            if apk_path.exists():
                return str(apk_path)

        # Search for any APK file
        for apk_file in apk_dir.glob('*.apk'):
            return str(apk_file)

        return None

    def clean_output(self):
        """Clean up the output directory"""
        if self.output_dir and self.output_dir.exists():
            shutil.rmtree(self.output_dir)

    def get_project_structure(self) -> Dict[str, List[str]]:
        """Get the project file structure"""
        structure = {}

        if not self.output_dir or not self.output_dir.exists():
            return structure

        for root, dirs, files in os.walk(self.output_dir):
            # Skip hidden directories and build outputs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['build', 'android/.gradle']]

            rel_root = os.path.relpath(root, self.output_dir)
            if rel_root == '.':
                rel_root = ''

            if files:
                structure[rel_root] = files

        return structure