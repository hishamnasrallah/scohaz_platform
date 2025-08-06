# File: builds/services/flutter_builder.py

import os
import subprocess
import tempfile
import shutil
from typing import Tuple, Optional
from django.conf import settings


class FlutterBuilder:
    """Handles Flutter build operations"""

    def __init__(self):
        self.flutter_path = self._get_flutter_path()

    def _get_flutter_path(self) -> str:
        """Get Flutter executable path"""
        flutter_sdk = getattr(settings, 'FLUTTER_SDK_PATH', None)

        if flutter_sdk:
            if os.name == 'nt':  # Windows
                return os.path.join(flutter_sdk, 'bin', 'flutter.bat')
            else:  # Unix-like
                return os.path.join(flutter_sdk, 'bin', 'flutter')

        # Fallback to system flutter
        return 'flutter'

    def check_flutter_installation(self) -> Tuple[bool, str]:
        """Check if Flutter is properly installed"""
        try:
            result = subprocess.run(
                [self.flutter_path, '--version'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr

        except FileNotFoundError:
            return False, "Flutter not found. Please install Flutter SDK."
        except subprocess.TimeoutExpired:
            return False, "Flutter version check timed out"
        except Exception as e:
            return False, str(e)

    def create_flutter_project(self, project_path: str, name: str,
                               org: str, description: str) -> Tuple[bool, str]:
        """Create a new Flutter project"""
        try:
            # Ensure the parent directory exists
            os.makedirs(os.path.dirname(project_path), exist_ok=True)

            cmd = [
                self.flutter_path, 'create',
                '--org', org,
                '--description', description,
                '--no-pub',  # We'll run pub get separately
                project_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(project_path),
                timeout=60
            )

            if result.returncode == 0:
                return True, "Project created successfully"
            else:
                return False, result.stderr

        except subprocess.TimeoutExpired:
            return False, "Project creation timed out"
        except Exception as e:
            return False, str(e)

    def _run_pub_get(self, project_path: str) -> Tuple[bool, str]:
        """Run flutter pub get"""
        try:
            # First, run flutter clean for safety
            subprocess.run(
                [self.flutter_path, 'clean'],
                cwd=project_path,
                capture_output=True,
                timeout=60
            )

            # Run pub get
            result = subprocess.run(
                [self.flutter_path, 'pub', 'get'],
                capture_output=True,
                text=True,
                cwd=project_path,
                timeout=120
            )

            if result.returncode != 0:
                return False, f"pub get failed: {result.stderr}"

            # Run gen-l10n if l10n.yaml exists
            if os.path.exists(os.path.join(project_path, 'l10n.yaml')):
                result = subprocess.run(
                    [self.flutter_path, 'gen-l10n'],
                    capture_output=True,
                    text=True,
                    cwd=project_path,
                    timeout=60
                )

                if result.returncode != 0:
                    return False, f"gen-l10n failed: {result.stderr}"

            return True, "Dependencies resolved"

        except subprocess.TimeoutExpired:
            return False, "Dependency resolution timed out"
        except Exception as e:
            return False, str(e)

    def build_apk(self, project_path: str, build_mode: str = 'release') -> Tuple[bool, str, Optional[str]]:
        """Build APK file"""
        try:
            # Ensure dependencies are up to date
            success, message = self._run_pub_get(project_path)
            if not success:
                return False, message, None

            # Build APK
            cmd = [self.flutter_path, 'build', 'apk', f'--{build_mode}']

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_path,
                timeout=getattr(settings, 'BUILD_TIMEOUT', 600)
            )

            if result.returncode == 0:
                # Find the APK file
                apk_path = self._find_apk_file(project_path, build_mode)
                if apk_path and os.path.exists(apk_path):
                    return True, "Build successful", apk_path
                else:
                    return False, "APK file not found after build", None
            else:
                return False, result.stderr, None

        except subprocess.TimeoutExpired:
            return False, "Build timeout exceeded", None
        except Exception as e:
            return False, str(e), None

    def _find_apk_file(self, project_path: str, build_mode: str) -> Optional[str]:
        """Find the generated APK file"""
        apk_paths = [
            os.path.join(project_path, 'build', 'app', 'outputs', 'flutter-apk', f'app-{build_mode}.apk'),
            os.path.join(project_path, 'build', 'app', 'outputs', 'apk', build_mode, f'app-{build_mode}.apk'),
        ]

        for path in apk_paths:
            if os.path.exists(path):
                return path

        return None

    def _fix_gradle_issues(self, project_path: str):
        """Fix common Gradle issues"""
        try:
            # Make gradlew executable on Unix-like systems
            if os.name != 'nt':
                gradlew_path = os.path.join(project_path, 'android', 'gradlew')
                if os.path.exists(gradlew_path):
                    os.chmod(gradlew_path, 0o755)

            # Fix gradle-wrapper.jar permissions
            gradle_wrapper = os.path.join(project_path, 'android', 'gradle', 'wrapper', 'gradle-wrapper.jar')
            if os.path.exists(gradle_wrapper):
                os.chmod(gradle_wrapper, 0o644)

        except Exception as e:
            print(f"Error fixing gradle issues: {e}")