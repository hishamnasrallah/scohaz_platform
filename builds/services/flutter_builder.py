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
            # First, ensure Flutter project is properly configured
            logger.info("Verifying Flutter project configuration...")

            # Check if pubspec.yaml exists
            pubspec_path = os.path.join(project_path, 'pubspec.yaml')
            if not os.path.exists(pubspec_path):
                return False, "pubspec.yaml not found in project", None

            # Check Android directory
            android_dir = os.path.join(project_path, 'android')
            if not os.path.exists(android_dir):
                logger.error("Android directory not found, creating Flutter project structure...")
                # Run flutter create to generate Android files
                create_result = self.command_runner.run_command(
                    [self.flutter_path, 'create', '.', '--platforms', 'android'],
                    cwd=project_path,
                    timeout=120
                )
                if create_result.returncode != 0:
                    return False, f"Failed to create Android project structure: {create_result.stderr}", None

            # Fix any Gradle issues first
            logger.info("Checking and fixing Gradle configuration...")
            if not self._fix_gradle_issues(project_path):
                logger.warning("Some Gradle issues could not be fixed")

            # Check Android licenses status (don't try to accept automatically as it requires interaction)
            logger.info("Checking Android licenses status...")
            doctor_result = self.command_runner.run_command(
                [self.flutter_path, 'doctor', '-v'],
                timeout=30,
                env=self.config.get_environment()
            )

            if doctor_result.returncode != 0 or "Android license status unknown" in doctor_result.stdout:
                logger.warning(
                    "Android licenses may not be accepted. If build fails, "
                    "run 'flutter doctor --android-licenses' manually to accept them."
                )

            # First, get dependencies
            logger.info("Running flutter pub get...")
            pub_result = self._run_pub_get(project_path)
            if not pub_result:
                return False, "Failed to get dependencies", None

            # Clean previous builds
            logger.info("Cleaning previous builds...")
            self._run_flutter_clean(project_path)

            # Check if local.properties exists and has SDK paths
            local_properties_path = os.path.join(project_path, 'android', 'local.properties')
            if not os.path.exists(local_properties_path):
                logger.warning("local.properties not found, creating it...")
                sdk_dir = self.config.android_sdk_path or os.environ.get('ANDROID_SDK_ROOT', '')
                flutter_sdk = self.config.flutter_sdk_path or os.environ.get('FLUTTER_ROOT', '')

                if sdk_dir:
                    with open(local_properties_path, 'w') as f:
                        f.write(f'sdk.dir={sdk_dir}\n')
                        f.write(f'flutter.sdk={flutter_sdk}\n')
                else:
                    logger.error("Android SDK path not found in environment")
                    return False, "Android SDK not configured. Set ANDROID_SDK_ROOT environment variable.", None

            # For debug builds, use simpler approach
            if build_mode == 'debug':
                logger.info("Building debug APK with simplified settings...")

                # First, let's try to run gradle directly to see the actual error
                gradle_wrapper = os.path.join(project_path, 'android', 'gradlew.bat' if os.name == 'nt' else 'gradlew')
                if os.path.exists(gradle_wrapper):
                    logger.info("Running Gradle assembleDebug directly for better error reporting...")
                    gradle_result = self.command_runner.run_command(
                        [gradle_wrapper, 'assembleDebug', '--stacktrace'],
                        cwd=os.path.join(project_path, 'android'),
                        timeout=300,
                        env=self.config.get_environment()
                    )

                    if gradle_result.returncode != 0:
                        logger.error(f"Gradle assembleDebug failed:\n{gradle_result.stdout}\n{gradle_result.stderr}")
                        # Continue with Flutter build anyway to get Flutter's error handling

                # Run Flutter build without the invalid --stacktrace flag
                build_result = self.command_runner.run_command(
                    [self.flutter_path, 'build', 'apk', '--debug', '--verbose'],
                    cwd=project_path,
                    timeout=600,  # 10 minutes
                    env=self.config.get_environment()
                )
            else:
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

                # Look for specific Gradle errors
                if "BUILD FAILED" in error_output:
                    # Extract more context around the failure
                    lines = error_output.split('\n')
                    error_context = []

                    # Find lines around "BUILD FAILED"
                    for i, line in enumerate(lines):
                        if "BUILD FAILED" in line:
                            # Get 10 lines before and after
                            start = max(0, i - 10)
                            end = min(len(lines), i + 5)
                            error_context = lines[start:end]
                            break

                    if error_context:
                        error_output = '\n'.join(error_context)

                # Check for common issues
                if "SDK location not found" in error_output:
                    error_output += "\n\nAndroid SDK not properly configured. Please check ANDROID_SDK_ROOT environment variable."
                elif "license agreements" in error_output.lower():
                    error_output += "\n\nAndroid licenses not accepted. Run 'flutter doctor --android-licenses' to accept."
                elif "compileSdkVersion" in error_output:
                    error_output += "\n\nGradle configuration issue. Check Android SDK version compatibility."

                logger.error(f"Build failed with output:\n{error_output}")
                return False, error_output, None

        except subprocess.TimeoutExpired:
            logger.error("Build timed out")
            return False, "Build process timed out after 10 minutes", None
        except Exception as e:
            logger.exception("Build failed with exception")
            import traceback
            detailed_error = f"Build failed: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            return False, detailed_error, None

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

                # Don't try to accept licenses automatically - just warn
            logger.info("Note: Android licenses must be accepted manually if not already done")
            logger.info("Run 'flutter doctor --android-licenses' if you encounter license issues")

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

        # Construct full path to gradle wrapper
        android_dir = os.path.join(project_path, 'android')
        gradlew_name = 'gradlew.bat' if os.name == 'nt' else 'gradlew'
        gradlew_path = os.path.join(android_dir, gradlew_name)

        # Check if gradle wrapper exists
        if os.path.exists(gradlew_path):
            # Make sure it's executable on Unix-like systems
            if os.name != 'nt':
                os.chmod(gradlew_path, 0o755)

            gradle_check = self.command_runner.run_command(
                [gradlew_path, 'tasks'],
                cwd=android_dir,
                timeout=60
            )

            if gradle_check.returncode != 0:
                logger.warning(f"Gradle check failed: {gradle_check.stderr}")
        else:
            logger.warning(f"Gradle wrapper not found at {gradlew_path}")

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