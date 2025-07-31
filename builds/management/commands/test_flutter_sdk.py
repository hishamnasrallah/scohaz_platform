"""
Management command to test Flutter SDK installation and configuration.
"""

import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from builds.services.flutter_builder import FlutterBuilder
from builds.utils.command_runner import CommandRunner
from builds.utils.file_manager import FileManager


class Command(BaseCommand):
    help = 'Test Flutter SDK installation and configuration'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flutter_builder = FlutterBuilder()
        self.command_runner = CommandRunner()
        self.file_manager = FileManager()

    def add_arguments(self, parser):
        parser.add_argument(
            '--build-test',
            action='store_true',
            help='Run a test build with a simple Flutter project'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )

    def handle(self, *args, **options):
        self.verbose = options.get('verbose', False)
        self.stdout.write(self.style.SUCCESS('Testing Flutter SDK configuration...\n'))

        # Test 1: Check Flutter SDK
        self.test_flutter_sdk()

        # Test 2: Check Flutter version
        self.test_flutter_version()

        # Test 3: Check Android SDK
        self.test_android_sdk()

        # Test 4: Check environment variables
        self.test_environment()

        # Test 5: Check disk space
        self.test_disk_space()

        # Optional: Run test build
        if options.get('build_test'):
            self.test_build()

        self.stdout.write(self.style.SUCCESS('\nAll tests completed!'))

    def test_flutter_sdk(self):
        """Test if Flutter SDK is available."""
        self.stdout.write('Checking Flutter SDK... ', ending='')

        if self.flutter_builder.check_flutter_sdk():
            self.stdout.write(self.style.SUCCESS('OK'))

            if self.verbose:
                # Run flutter doctor for detailed info
                result = self.command_runner.run_command(
                    ['flutter', 'doctor', '-v'],
                    timeout=30
                )
                self.stdout.write('\nFlutter Doctor Output:')
                self.stdout.write(result.stdout)
        else:
            self.stdout.write(self.style.ERROR('FAILED'))
            self.stdout.write(
                self.style.ERROR(
                    '\nFlutter SDK not found. Please install Flutter and ensure it\'s in PATH.'
                )
            )
            raise CommandError('Flutter SDK not found')

    def test_flutter_version(self):
        """Test Flutter version."""
        self.stdout.write('Checking Flutter version... ', ending='')

        version = self.flutter_builder.get_flutter_version()
        if version:
            self.stdout.write(self.style.SUCCESS(f'OK ({version})'))
        else:
            self.stdout.write(self.style.WARNING('Could not determine version'))

    def test_android_sdk(self):
        """Test Android SDK configuration."""
        self.stdout.write('Checking Android SDK... ', ending='')

        if self.flutter_builder.check_android_sdk():
            self.stdout.write(self.style.SUCCESS('OK'))
        else:
            self.stdout.write(self.style.WARNING('NOT CONFIGURED'))
            self.stdout.write(
                self.style.WARNING(
                    '\nAndroid SDK or licenses not properly configured. '
                    'Run "flutter doctor --android-licenses" to accept licenses.'
                )
            )

    def test_environment(self):
        """Test environment variables."""
        self.stdout.write('\nChecking environment variables:')

        env_vars = {
            'FLUTTER_SDK_PATH': getattr(settings, 'FLUTTER_SDK_PATH', None),
            'ANDROID_SDK_ROOT': os.environ.get('ANDROID_SDK_ROOT'),
            'ANDROID_HOME': os.environ.get('ANDROID_HOME'),
            'JAVA_HOME': os.environ.get('JAVA_HOME'),
            'PATH contains flutter': 'flutter' in os.environ.get('PATH', '').lower()
        }

        for var, value in env_vars.items():
            if value:
                self.stdout.write(f'  {var}: {self.style.SUCCESS(str(value))}')
            else:
                self.stdout.write(f'  {var}: {self.style.WARNING("Not set")}')

    def test_disk_space(self):
        """Test available disk space."""
        self.stdout.write('\nChecking disk space... ', ending='')

        temp_dir = getattr(settings, 'BUILD_TEMP_DIR', '/tmp')
        available_space = self.file_manager.get_available_space(temp_dir)

        if available_space > 0:
            space_gb = available_space / (1024 ** 3)
            if space_gb > 5:
                self.stdout.write(self.style.SUCCESS(f'OK ({space_gb:.1f} GB available)'))
            else:
                self.stdout.write(
                    self.style.WARNING(f'LOW ({space_gb:.1f} GB available)')
                )
        else:
            self.stdout.write(self.style.WARNING('Could not determine'))

    def test_build(self):
        """Run a test build with a simple Flutter project."""
        self.stdout.write('\n' + self.style.SUCCESS('Running test build...'))

        # Create temporary directory
        temp_dir = self.file_manager.create_temp_directory('flutter_test_')

        try:
            # Create a minimal Flutter project
            self.stdout.write(f'Creating test project in {temp_dir}...')

            # Create project structure
            test_files = {
                'pubspec.yaml': '''name: test_app
description: Test Flutter application
version: 1.0.0+1

environment:
  sdk: ">=2.12.0 <3.0.0"

dependencies:
  flutter:
    sdk: flutter

dev_dependencies:
  flutter_test:
    sdk: flutter

flutter:
  uses-material-design: true
''',
                'lib/main.dart': '''import 'package:flutter/material.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Test App',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: Scaffold(
        appBar: AppBar(
          title: Text('Test App'),
        ),
        body: Center(
          child: Text(
            'Hello from Flutter Visual Builder!',
            style: TextStyle(fontSize: 24),
          ),
        ),
      ),
    );
  }
}
''',
                'android/app/src/main/AndroidManifest.xml': '''<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.test_app">
    <application
        android:label="test_app"
        android:icon="@mipmap/ic_launcher">
        <activity
            android:name=".MainActivity"
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
''',
            }

            # Write test files
            self.file_manager.write_project_files(temp_dir, test_files)

            # Create Flutter project structure
            self.stdout.write('Initializing Flutter project...')
            result = self.command_runner.run_command(
                ['flutter', 'create', '.', '--org', 'com.example', '--project-name', 'test_app'],
                cwd=temp_dir,
                timeout=60
            )

            if result.returncode != 0:
                self.stdout.write(self.style.ERROR(f'Failed to create project: {result.stderr}'))
                return

            # Build APK
            self.stdout.write('Building APK (this may take a few minutes)...')
            success, output, apk_path = self.flutter_builder.build_apk(temp_dir, 'debug')

            if success:
                self.stdout.write(self.style.SUCCESS(f'\nTest build successful!'))
                self.stdout.write(f'APK created at: {apk_path}')

                # Check APK size
                if apk_path and os.path.exists(apk_path):
                    size_mb = os.path.getsize(apk_path) / (1024 * 1024)
                    self.stdout.write(f'APK size: {size_mb:.1f} MB')
            else:
                self.stdout.write(self.style.ERROR('\nTest build failed!'))
                if self.verbose:
                    self.stdout.write('Build output:')
                    self.stdout.write(output)

        finally:
            # Clean up
            self.stdout.write(f'\nCleaning up {temp_dir}...')
            self.file_manager.cleanup_directory(temp_dir)