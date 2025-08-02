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

            # Build flutter create command with Java to avoid Kotlin issues
            cmd = [
                flutter_path, 'create',
                '--project-name', name,
                '--org', org,
                '--platforms', 'android',  # Only Android for now
                '--android-language', 'java',  # Use Java instead of Kotlin to avoid compilation issues
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

                # Trust Flutter's default configuration
                logger.info("Flutter project created with default configurations")

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

        # CRITICAL: Ensure we're in the project root, not android subdirectory
        if project_path.endswith('android'):
            logger.error(f"ERROR: build_apk called with android subdirectory: {project_path}")
            project_path = os.path.dirname(project_path)
            logger.info(f"Corrected to project root: {project_path}")

        # Verify we're in the correct directory
        if not os.path.exists(os.path.join(project_path, 'pubspec.yaml')):
            logger.error(f"ERROR: pubspec.yaml not found in {project_path}")
            logger.error(f"Directory contents: {os.listdir(project_path) if os.path.exists(project_path) else 'Directory does not exist'}")
            return False, "Working directory is not a Flutter project root", None

        try:
            # First, ensure Flutter project is properly configured
            logger.info(f"Verifying Flutter project configuration in: {project_path}")
            logger.info(f"Current working directory: {os.getcwd()}")

            # Check if pubspec.yaml exists
            pubspec_path = os.path.join(project_path, 'pubspec.yaml')
            if not os.path.exists(pubspec_path):
                logger.error(f"pubspec.yaml not found at: {pubspec_path}")
                logger.error(f"Directory contents: {os.listdir(project_path) if os.path.exists(project_path) else 'Directory does not exist'}")
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

            # Let Flutter handle local.properties creation
            # Just ensure we have the right environment variables set
            env = self.config.get_environment()
            if not env.get('ANDROID_SDK_ROOT') and not env.get('ANDROID_HOME'):
                logger.warning("Android SDK environment variables not set. Flutter will try to auto-detect.")

            # For debug builds, use simpler approach
            if build_mode == 'debug':
                logger.info("Building debug APK with simplified settings...")

                # First, let's try to run gradle directly to see the actual error
                gradle_wrapper = os.path.join(project_path, 'android', 'gradlew.bat' if os.name == 'nt' else 'gradlew')
                if os.path.exists(gradle_wrapper):
                    logger.info("Running Gradle assembleDebug directly for better error reporting...")
                    gradle_result = self.command_runner.run_command(
                        [gradle_wrapper, 'assembleDebug', '--stacktrace', '--debug'],
                        cwd=os.path.join(project_path, 'android'),
                        timeout=300,
                        env=self.config.get_environment()
                    )

                    if gradle_result.returncode != 0:
                        logger.error(f"Gradle assembleDebug failed:\n{gradle_result.stdout}\n{gradle_result.stderr}")
                        # Try to extract Kotlin-specific errors
                        if "compileDebugKotlin" in gradle_result.stdout:
                            logger.error("Kotlin compilation error detected")
                        # Continue with Flutter build anyway to get Flutter's error handling

                # Run Flutter build with extra verbosity
                build_result = self.command_runner.run_command(
                    # [self.flutter_path, 'build', 'apk', '--debug', '--verbose'],
                    [self.flutter_path, 'build', 'apk'],
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

                    # Look for Kotlin compilation errors specifically
                    for i, line in enumerate(lines):
                        if "compileDebugKotlin" in line or "Compilation error" in line:
                            # Get more context around Kotlin errors
                            start = max(0, i - 20)
                            end = min(len(lines), i + 10)
                            error_context = lines[start:end]
                            break
                        elif "BUILD FAILED" in line:
                            # Get 10 lines before and after
                            start = max(0, i - 10)
                            end = min(len(lines), i + 5)
                            error_context = lines[start:end]
                            break

                    if error_context:
                        error_output = '\n'.join(error_context)

                # Add specific Kotlin error checks
                if "compileDebugKotlin" in error_output:
                    error_output += "\n\nKotlin compilation failed. This might be due to version incompatibility."

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
        logger.info(f"Running flutter pub get in {project_path}")
        logger.debug(f"Current working directory: {os.getcwd()}")
        logger.debug(f"Project path exists: {os.path.exists(project_path)}")
        logger.debug(f"Project path contents: {os.listdir(project_path) if os.path.exists(project_path) else 'Directory does not exist'}")

        # Add flutter clean before pub get to ensure fresh state
        logger.info("Running flutter clean to ensure fresh state...")
        clean_command = [self.flutter_path, 'clean']
        logger.debug(f"Clean command: {' '.join(clean_command)}")
        logger.debug(f"Clean cwd: {project_path}")

        clean_result = self.command_runner.run_command(
            clean_command,
            cwd=project_path,
            timeout=60
        )

        if clean_result.returncode != 0:
            logger.warning(f"flutter clean failed (non-critical): {clean_result.stderr}")
            logger.warning(f"flutter clean stdout: {clean_result.stdout}")
        else:
            logger.info("flutter clean completed successfully")

        # Run flutter pub get
        pub_get_command = [self.flutter_path, 'pub', 'get']
        logger.debug(f"Pub get command: {' '.join(pub_get_command)}")
        logger.debug(f"Pub get cwd: {project_path}")

        result = self.command_runner.run_command(
            pub_get_command,
            cwd=project_path,
            timeout=120  # 2 minutes timeout
        )

        # Always log full output for debugging
        logger.info(f"flutter pub get return code: {result.returncode}")
        if result.stdout:
            logger.info(f"flutter pub get stdout:\n{result.stdout}")
        if result.stderr:
            logger.error(f"flutter pub get stderr:\n{result.stderr}")

        if result.returncode != 0:
            logger.error(f"Failed to fetch dependencies with return code: {result.returncode}")
            logger.error(f"Full command was: {' '.join(pub_get_command)}")
            logger.error(f"Working directory was: {project_path}")
            return False

        logger.info("Dependencies fetched successfully")

        # Check if l10n.yaml exists and run flutter gen-l10n
        l10n_yaml_path = os.path.join(project_path, 'l10n.yaml')
        if os.path.exists(l10n_yaml_path):
            # Debug: log l10n.yaml contents
            with open(l10n_yaml_path, 'r') as f:
                l10n_content = f.read()
                logger.debug(f"l10n.yaml contents:\n{l10n_content}")

            logger.info("Running flutter gen-l10n to generate localization files")
            logger.info(f"Working directory for gen-l10n: {project_path}")

            # Ensure we're in the right directory
            if not os.path.exists(os.path.join(project_path, 'pubspec.yaml')):
                logger.error(f"ERROR: No pubspec.yaml in {project_path}, cannot run gen-l10n")
                return False

            gen_result = self.command_runner.run_command(
                [self.flutter_path, 'gen-l10n'],
                cwd=project_path,
                timeout=60
            )

            if gen_result.stdout:
                logger.info(f"flutter gen-l10n output: {gen_result.stdout}")
            if gen_result.stderr:
                logger.warning(f"flutter gen-l10n stderr: {gen_result.stderr}")

            if gen_result.returncode != 0:
                logger.error(f"Failed to generate localization files: {gen_result.stderr}")
                return False

            logger.info("Localization files generated successfully")

            # Verify app_localizations.dart was actually generated
            # Check both possible locations
            app_localizations_paths = [
                os.path.join(project_path, '.dart_tool', 'flutter_gen', 'gen_l10n', 'app_localizations.dart'),
                os.path.join(project_path, 'lib', 'l10n', 'app_localizations.dart')
            ]

            app_localizations_found = False
            for path in app_localizations_paths:
                if os.path.exists(path):
                    logger.info(f"Found app_localizations.dart at: {path}")
                    app_localizations_found = True
                    break

            if not app_localizations_found:
                logger.error("app_localizations.dart not found after gen-l10n")
                logger.error("Checked paths:")
                for path in app_localizations_paths:
                    logger.error(f"  - {path}")

                # Additional debugging: list .dart_tool contents
                dart_tool_path = os.path.join(project_path, '.dart_tool')
                if os.path.exists(dart_tool_path):
                    logger.error(f"Contents of .dart_tool: {os.listdir(dart_tool_path)}")
                    flutter_gen_path = os.path.join(dart_tool_path, 'flutter_gen')
                    if os.path.exists(flutter_gen_path):
                        logger.error(f"Contents of .dart_tool/flutter_gen: {os.listdir(flutter_gen_path)}")
                        gen_l10n_path = os.path.join(flutter_gen_path, 'gen_l10n')
                        if os.path.exists(gen_l10n_path):
                            logger.error(f"Contents of .dart_tool/flutter_gen/gen_l10n: {os.listdir(gen_l10n_path)}")

                return False

            # Verify package_config.json was created
            package_config_path = os.path.join(project_path, '.dart_tool', 'package_config.json')
            if not os.path.exists(package_config_path):
                logger.error(f"package_config.json not found at {package_config_path} after pub get")
                return False

            return True

    def _fix_gradle_issues(self, project_path: str) -> bool:
        """Ensure gradle wrapper is executable"""
        try:
            gradlew_path = os.path.join(project_path, 'android', 'gradlew')

            # Make gradlew executable on Unix-like systems
            if os.path.exists(gradlew_path) and os.name != 'nt':
                os.chmod(gradlew_path, 0o755)

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
        # CRITICAL: Log and verify working directory
        logger.info(f"_run_build_apk called with project_path: {project_path}")
        logger.info(f"Current working directory: {os.getcwd()}")

        # Ensure we have pubspec.yaml in the project path
        pubspec_path = os.path.join(project_path, 'pubspec.yaml')
        if not os.path.exists(pubspec_path):
            logger.error(f"CRITICAL: pubspec.yaml not found at {pubspec_path}")
            logger.error("This indicates flutter build apk is being run from wrong directory!")
            # Try to find pubspec.yaml in parent directory
            parent_pubspec = os.path.join(os.path.dirname(project_path), 'pubspec.yaml')
            if os.path.exists(parent_pubspec):
                logger.warning(f"Found pubspec.yaml in parent directory, correcting path")
                project_path = os.path.dirname(project_path)

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