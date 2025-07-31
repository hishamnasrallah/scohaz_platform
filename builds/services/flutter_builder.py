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
                logger.error(f"Build failed: {build_result.stderr}")
                return False, f"{build_result.stdout}\n{build_result.stderr}", None

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
            '--no-sound-null-safety',  # For compatibility
            '--verbose'  # Detailed output
        ])

        # Run build command
        return self.command_runner.run_command(
            cmd,
            cwd=project_path,
            timeout=self.config.get_build_timeout()
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