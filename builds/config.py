"""
Configuration settings for the build system.
"""

import os
from django.conf import settings


class BuildConfig:
    """Configuration class for build system settings."""

    def __init__(self):
        # Load settings with defaults
        self.flutter_sdk_path = getattr(
            settings,
            'FLUTTER_SDK_PATH',
            os.environ.get('FLUTTER_ROOT', '')
        )

        self.android_sdk_path = getattr(
            settings,
            'ANDROID_SDK_PATH',
            os.environ.get('ANDROID_SDK_ROOT',
                           os.environ.get('ANDROID_HOME', ''))
        )

        self.java_home = getattr(
            settings,
            'JAVA_HOME',
            os.environ.get('JAVA_HOME', '')
        )

        # Build settings
        self.build_timeout = getattr(settings, 'BUILD_TIMEOUT', 300)  # 5 minutes
        self.max_concurrent_builds = getattr(settings, 'MAX_CONCURRENT_BUILDS', 3)
        self.build_retention_days = getattr(settings, 'BUILD_RETENTION_DAYS', 30)

        # Paths
        self.temp_build_dir = getattr(
            settings,
            'BUILD_TEMP_DIR',
            os.path.join(settings.BASE_DIR, 'temp', 'builds')
        )

        self.build_output_dir = getattr(
            settings,
            'BUILD_OUTPUT_DIR',
            os.path.join(settings.MEDIA_ROOT, 'builds')
        )

        # APK signing
        self.keystore_path = getattr(settings, 'ANDROID_KEYSTORE_PATH', None)
        self.keystore_password = getattr(settings, 'ANDROID_KEYSTORE_PASSWORD', None)
        self.key_alias = getattr(settings, 'ANDROID_KEY_ALIAS', None)
        self.key_password = getattr(settings, 'ANDROID_KEY_PASSWORD', None)

        # Features
        self.enable_apk_signing = getattr(settings, 'ENABLE_APK_SIGNING', False)
        self.enable_build_notifications = getattr(settings, 'SEND_BUILD_NOTIFICATIONS', False)
        self.enable_build_analytics = getattr(settings, 'ENABLE_BUILD_ANALYTICS', True)

        # Celery settings
        self.use_celery = getattr(settings, 'USE_CELERY_FOR_BUILDS', True)
        self.celery_queue = getattr(settings, 'BUILD_CELERY_QUEUE', 'builds')

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        directories = [
            self.temp_build_dir,
            self.build_output_dir,
        ]

        for directory in directories:
            if directory:
                os.makedirs(directory, exist_ok=True)


    def get_flutter_executable(self):
        """Get full path to Flutter executable."""
        if self.flutter_sdk_path:
            # On Windows, use flutter.bat
            if os.name == 'nt':  # Windows
                flutter_bin = os.path.join(self.flutter_sdk_path, 'bin', 'flutter.bat')
            else:  # Unix-like systems
                flutter_bin = os.path.join(self.flutter_sdk_path, 'bin', 'flutter')

            if os.path.exists(flutter_bin):
                return flutter_bin

        # Fall back to PATH
        return 'flutter'

    def get_build_timeout(self):
        """Get build timeout in seconds."""
        return self.build_timeout

    def get_temp_build_dir(self):
        """Get temporary build directory path."""
        return self.temp_build_dir

    def get_environment(self):
        """Get environment variables for build process."""
        env = os.environ.copy()

        # Add custom paths if configured
        if self.flutter_sdk_path:
            env['FLUTTER_ROOT'] = self.flutter_sdk_path

            # Add to PATH
            flutter_bin = os.path.join(self.flutter_sdk_path, 'bin')
            if 'PATH' in env:
                env['PATH'] = f"{flutter_bin}{os.pathsep}{env['PATH']}"
            else:
                env['PATH'] = flutter_bin

        if self.android_sdk_path:
            env['ANDROID_SDK_ROOT'] = self.android_sdk_path
            env['ANDROID_HOME'] = self.android_sdk_path

        if self.java_home:
            env['JAVA_HOME'] = self.java_home

            # Add to PATH
            java_bin = os.path.join(self.java_home, 'bin')
            if 'PATH' in env:
                env['PATH'] = f"{java_bin}{os.pathsep}{env['PATH']}"
            else:
                env['PATH'] = java_bin

        return env

    def validate_configuration(self):
        """
        Validate build system configuration.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check Flutter SDK
        flutter_exe = self.get_flutter_executable()
        if not os.path.exists(flutter_exe) and flutter_exe != 'flutter':
            errors.append(f"Flutter SDK not found at: {flutter_exe}")

        # Check Android SDK
        if self.android_sdk_path and not os.path.exists(self.android_sdk_path):
            errors.append(f"Android SDK not found at: {self.android_sdk_path}")

        # Check Java
        if self.java_home and not os.path.exists(self.java_home):
            errors.append(f"Java not found at: {self.java_home}")

        # Check APK signing if enabled
        if self.enable_apk_signing:
            if not self.keystore_path:
                errors.append("APK signing enabled but keystore path not configured")
            elif not os.path.exists(self.keystore_path):
                errors.append(f"Keystore not found at: {self.keystore_path}")

            if not self.keystore_password:
                errors.append("APK signing enabled but keystore password not configured")

            if not self.key_alias:
                errors.append("APK signing enabled but key alias not configured")

        # Check directories
        if not os.access(self.temp_build_dir, os.W_OK):
            errors.append(f"Cannot write to temp build directory: {self.temp_build_dir}")

        if not os.access(self.build_output_dir, os.W_OK):
            errors.append(f"Cannot write to output directory: {self.build_output_dir}")

        return len(errors) == 0, errors

    def get_config_dict(self):
        """Get configuration as dictionary."""
        return {
            'flutter_sdk_path': self.flutter_sdk_path,
            'android_sdk_path': self.android_sdk_path,
            'java_home': self.java_home,
            'build_timeout': self.build_timeout,
            'max_concurrent_builds': self.max_concurrent_builds,
            'build_retention_days': self.build_retention_days,
            'temp_build_dir': self.temp_build_dir,
            'build_output_dir': self.build_output_dir,
            'enable_apk_signing': self.enable_apk_signing,
            'enable_build_notifications': self.enable_build_notifications,
            'enable_build_analytics': self.enable_build_analytics,
            'use_celery': self.use_celery,
        }