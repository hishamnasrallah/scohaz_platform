"""
Flutter SDK integration for building APK files.
"""

import os
import logging
import subprocess
from typing import Tuple, Optional, List

from django.conf import settings

from builds.utils.command_runner import CommandRunner
from builds.config import BuildConfig

logger = logging.getLogger(__name__)


class FlutterBuilder:
    """Handles Flutter SDK operations for building APK files."""

    def __init__(self):
        self.command_runner = CommandRunner()
        self.config = BuildConfig()
        self.flutter_path = self._get_flutter_path()

    @staticmethod
    def create_flutter_project(project_path: str, name: str, org: str, description: str = None) -> Tuple[bool, str]:
        """
        Create a new Flutter project using flutter create.

        Args:
            project_path: Path where the project should be created
            name: Project name
            org: Organization identifier (e.g., com.example)
            description: Project description

        Returns:
            Tuple of (success, error_message)
        """
        logger.info(f"Creating Flutter project: {name} at {project_path}")

        try:
            # Get flutter path
            flutter_path = 'flutter'
            if hasattr(settings, 'FLUTTER_SDK_PATH') and settings.FLUTTER_SDK_PATH:
                if os.name == 'nt':  # Windows
                    flutter_path = os.path.join(settings.FLUTTER_SDK_PATH, 'bin', 'flutter.bat')
                else:
                    flutter_path = os.path.join(settings.FLUTTER_SDK_PATH, 'bin', 'flutter')

            # Build flutter create command
            cmd = [
                flutter_path, 'create',
                '--project-name', name,
                '--org', org,
                '--platforms', 'android',  # Only Android for now
                '.'  # Create in current directory
            ]

            if description:
                cmd.extend(['--description', description])

            # Run flutter create using subprocess directly
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes timeout
            )

            if result.returncode == 0:
                logger.info("Flutter project created successfully")
                return True, None
            else:
                logger.error(f"Failed to create Flutter project: {result.stderr}")
                return False, result.stderr

        except subprocess.TimeoutExpired:
            return False, "Flutter create timed out"
        except Exception as e:
            logger.error(f"Exception creating Flutter project: {str(e)}")
            return False, str(e)

    def check_flutter_sdk(self) -> bool:
        """
        Check if Flutter SDK is properly installed and configured.

        Returns:
            True if Flutter SDK is available
        """
        try:
            # Run flutter doctor
            result = self.command_runner.run_command(
                [self.flutter_path, 'doctor', '-v'],
                timeout=30
            )

            if result.returncode == 0:
                logger.info("Flutter SDK check passed")
                return True
            else:
                logger.error(f"Flutter SDK check failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to check Flutter SDK: {e}")
            return False

    def build_apk(self, project_path: str, build_mode: str = 'release') -> Tuple[bool, str, Optional[str]]:
        """
        Build APK from Flutter project.

        Args:
            project_path: Path to Flutter project
            build_mode: Build mode (debug, profile, release)

        Returns:
            Tuple of (success, output, apk_path)
        """
        logger.info(f"Building APK for project at {project_path}")

        try:
            # Fix any Gradle issues first
            logger.info("Checking and fixing Gradle configuration...")
            if not self._fix_gradle_issues(project_path):
                logger.warning("Some Gradle issues could not be fixed")

            # First, get dependencies
            logger.info("Running flutter pub get...")
            pub_result = self._run_pub_get(project_path)
            if not pub_result:
                return False, "Failed to get dependencies", None

            # Clean previous builds
            logger.info("Cleaning previous builds...")
            self._run_flutter_clean(project_path)

            # Build APK
            logger.info(f"Building APK in {build_mode} mode...")
            build_result = self._run_build_apk(project_path, build_mode)

            if build_result.returncode == 0:
                # Find APK file
                apk_path = self._find_apk_file(project_path, build_mode)
                if apk_path:
                    logger.info(f"APK built successfully: {apk_path}")
                    return True, build_result.stdout, apk_path
                else:
                    logger.error("APK file not found after successful build")
                    return False, "APK file not found", None
            else:
                # Extract meaningful error from output
                error_output = f"{build_result.stdout}\n{build_result.stderr}"

                # Look for common Gradle errors
                if "FAILURE: Build failed with an exception" in error_output:
                    # Extract the actual error message
                    lines = error_output.split('\n')
                    error_start = False
                    error_lines = []
                    for line in lines:
                        if "FAILURE: Build failed" in line:
                            error_start = True
                        if error_start:
                            error_lines.append(line)
                        if "BUILD FAILED" in line:
                            break
                    error_output = '\n'.join(error_lines[-20:])  # Last 20 lines of error

                logger.error(f"Build failed with output:\n{error_output}")
                return False, error_output, None

        except subprocess.TimeoutExpired:
            logger.error("Build timed out")
            return False, "Build process timed out", None
        except Exception as e:
            logger.exception("Build failed with exception")
            return False, f"Build failed: {str(e)}", None

    def _get_flutter_path(self) -> str:
        """Get Flutter executable path."""
        # Check settings first
        flutter_path = getattr(settings, 'FLUTTER_SDK_PATH', None)
        if flutter_path:
            # On Windows, use flutter.bat
            if os.name == 'nt':  # Windows
                flutter_exe = os.path.join(flutter_path, 'bin', 'flutter.bat')
            else:  # Unix-like systems
                flutter_exe = os.path.join(flutter_path, 'bin', 'flutter')

            if os.path.exists(flutter_exe):
                return flutter_exe

        # Try to find flutter in PATH
        return 'flutter'

    def _run_pub_get(self, project_path: str) -> bool:
        """Run flutter pub get to fetch dependencies."""
        result = self.command_runner.run_command(
            [self.flutter_path, 'pub', 'get'],
            cwd=project_path,
            timeout=120  # 2 minutes timeout
        )

        if result.returncode == 0:
            logger.info("Dependencies fetched successfully")
            return True
        else:
            logger.error(f"Failed to fetch dependencies: {result.stderr}")
            return False

    def _fix_gradle_issues(self, project_path: str) -> bool:
        """Fix common Gradle issues before building."""
        try:
            # Check if gradle wrapper exists
            gradlew_path = os.path.join(project_path, 'android', 'gradlew')
            if not os.path.exists(gradlew_path):
                logger.warning("Gradle wrapper not found, regenerating...")
                # Run flutter create to regenerate Android files
                result = self.command_runner.run_command(
                    [self.flutter_path, 'create', '.', '--platforms', 'android'],
                    cwd=project_path,
                    timeout=60
                )
                if result.returncode != 0:
                    logger.error(f"Failed to regenerate Android files: {result.stderr}")
                    return False

            # Make gradlew executable on Unix-like systems
            if os.name != 'nt':
                os.chmod(gradlew_path, 0o755)

            # Accept Android licenses
            logger.info("Checking Android licenses...")
            license_result = self.command_runner.run_command(
                [self.flutter_path, 'doctor', '--android-licenses', '-v'],
                timeout=30
            )

            return True
        except Exception as e:
            logger.error(f"Failed to fix Gradle issues: {e}")
            return False

    def _run_flutter_clean(self, project_path: str) -> bool:
        """Run flutter clean to remove previous build artifacts."""
        result = self.command_runner.run_command(
            [self.flutter_path, 'clean'],
            cwd=project_path,
            timeout=60
        )

        if result.returncode == 0:
            logger.info("Clean completed successfully")
            return True
        else:
            logger.warning(f"Clean failed (non-critical): {result.stderr}")
            return False

    def _run_build_apk(self, project_path: str, build_mode: str) -> subprocess.CompletedProcess:
        """Run flutter build apk command."""
        # First, let's try to get more detailed error info by running gradle directly
        logger.info("Running gradle wrapper to check for issues...")
        gradlew_cmd = 'gradlew.bat' if os.name == 'nt' else './gradlew'
        gradle_check = self.command_runner.run_command(
            [gradlew_cmd, 'tasks'],
            cwd=os.path.join(project_path, 'android'),
            timeout=60
        )

        if gradle_check.returncode != 0:
            logger.warning(f"Gradle check failed: {gradle_check.stderr}")

        cmd = [self.flutter_path, 'build', 'apk']

        # Add build mode flag
        if build_mode == 'debug':
            cmd.append('--debug')
        elif build_mode == 'profile':
            cmd.append('--profile')
        else:  # release
            cmd.append('--release')

        # Add additional flags
        cmd.extend([
            '--verbose'  # Detailed output
        ])

        # Set up environment with proper Android SDK
        env = os.environ.copy()
        if self.config.android_sdk_path:
            env['ANDROID_SDK_ROOT'] = self.config.android_sdk_path
            env['ANDROID_HOME'] = self.config.android_sdk_path

        # Run build command
        return self.command_runner.run_command(
            cmd,
            cwd=project_path,
            timeout=self.config.get_build_timeout(),
            env=env
        )

    def _find_apk_file(self, project_path: str, build_mode: str) -> Optional[str]:
        """Find the generated APK file."""
        # APK locations based on build mode
        apk_paths = {
            'debug': 'build/app/outputs/flutter-apk/app-debug.apk',
            'profile': 'build/app/outputs/flutter-apk/app-profile.apk',
            'release': 'build/app/outputs/flutter-apk/app-release.apk'
        }

        apk_relative_path = apk_paths.get(build_mode)
        if not apk_relative_path:
            return None

        apk_path = os.path.join(project_path, apk_relative_path)

        if os.path.exists(apk_path):
            return apk_path

        # Try alternative path (older Flutter versions)
        alt_path = os.path.join(project_path, 'build/app/outputs/apk', f'app-{build_mode}.apk')
        if os.path.exists(alt_path):
            return alt_path

        return None

    def get_flutter_version(self) -> Optional[str]:
        """Get Flutter SDK version."""
        try:
            result = self.command_runner.run_command(
                [self.flutter_path, '--version'],
                timeout=10
            )

            if result.returncode == 0:
                # Parse version from output
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Flutter' in line:
                        return line.strip()

            return None

        except Exception as e:
            logger.error(f"Failed to get Flutter version: {e}")
            return None

    def check_android_sdk(self) -> bool:
        """Check if Android SDK is properly configured."""
        try:
            result = self.command_runner.run_command(
                [self.flutter_path, 'doctor', '--android-licenses'],
                timeout=30
            )

            return result.returncode == 0

        except Exception:
            return False