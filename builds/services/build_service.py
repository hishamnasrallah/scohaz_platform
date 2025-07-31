"""
Main build service for orchestrating Flutter app builds.
"""

import os
import logging
import uuid
from datetime import datetime
from typing import Optional, Tuple

from django.conf import settings
from django.core.files import File
from django.utils import timezone

from builds.models import Build, BuildLog
from builds.services.flutter_builder import FlutterBuilder
from builds.services.build_monitor import BuildMonitor
from builds.utils.file_manager import FileManager
from builds.config import BuildConfig
from builder.generators.flutter_generator import FlutterGenerator

logger = logging.getLogger(__name__)


class BuildService:
    """Main service for managing Flutter app builds."""

    def __init__(self):
        self.flutter_builder = FlutterBuilder()
        self.build_monitor = BuildMonitor()
        self.file_manager = FileManager()
        self.config = BuildConfig()

    def start_build(self, build: Build) -> Build:
        """
        Start the build process for a Flutter project.

        Args:
            build: Build model instance

        Returns:
            Updated Build instance
        """
        logger.info(f"Starting build {build.id} for project {build.project.name}")

        try:
            # Update build status
            build.status = 'building'
            build.started_at = timezone.now()
            build.save()

            # Create build log
            build_log = BuildLog.objects.create(
                build=build,
                level='INFO',
                message='Build process started'
            )

            # Check Flutter SDK
            if not self.flutter_builder.check_flutter_sdk():
                raise RuntimeError("Flutter SDK not found or not properly configured")

            # Generate Flutter code
            logger.info("Generating Flutter code...")
            self._log_build_progress(build, "Generating Flutter code", level='INFO')

            generator = FlutterGenerator(build.project)
            generated_files = generator.generate_project()

            # Create temporary build directory
            build_dir = self._create_build_directory(build)

            try:
                # Write generated files
                logger.info(f"Writing files to {build_dir}")
                self._log_build_progress(build, f"Writing project files to {build_dir}", level='INFO')

                self.file_manager.write_project_files(build_dir, generated_files)

                # Build APK
                logger.info("Building APK...")
                self._log_build_progress(build, "Running Flutter build", level='INFO')

                success, output, apk_path = self.flutter_builder.build_apk(build_dir)

                if success:
                    # Store APK file
                    logger.info(f"Build successful, APK at: {apk_path}")
                    self._log_build_progress(build, f"Build successful: {apk_path}", level='INFO')

                    self._store_apk(build, apk_path)

                    # Update build status
                    build.status = 'success'
                    build.completed_at = timezone.now()
                    build.build_output = output
                    build.save()

                    self._log_build_progress(build, "Build completed successfully", level='SUCCESS')
                else:
                    # Build failed
                    logger.error(f"Build failed: {output}")
                    self._handle_build_failure(build, output)

            finally:
                # Clean up temporary directory
                logger.info(f"Cleaning up build directory: {build_dir}")
                self.file_manager.cleanup_directory(build_dir)

            return build

        except Exception as e:
            logger.exception(f"Build {build.id} failed with exception")
            self._handle_build_exception(build, e)
            return build

    def cancel_build(self, build: Build) -> bool:
        """
        Cancel an ongoing build.

        Args:
            build: Build model instance

        Returns:
            True if cancelled successfully
        """
        if build.status != 'building':
            return False

        # TODO: Implement build cancellation
        # This would need to track subprocess PIDs

        build.status = 'cancelled'
        build.completed_at = timezone.now()
        build.save()

        self._log_build_progress(build, "Build cancelled by user", level='WARNING')

        return True

    def retry_build(self, failed_build: Build) -> Build:
        """
        Retry a failed build.

        Args:
            failed_build: Failed Build instance

        Returns:
            New Build instance
        """
        if failed_build.status not in ['failed', 'cancelled']:
            raise ValueError("Can only retry failed or cancelled builds")

        # Create new build instance
        new_build = Build.objects.create(
            project=failed_build.project,
            version=failed_build.version,
            status='pending',
            build_type=failed_build.build_type,
            configuration=failed_build.configuration
        )

        self._log_build_progress(
            new_build,
            f"Retrying build (original: {failed_build.id})",
            level='INFO'
        )

        # Start the new build
        return self.start_build(new_build)

    def get_build_status(self, build: Build) -> dict:
        """
        Get detailed build status.

        Args:
            build: Build model instance

        Returns:
            Dictionary with build status details
        """
        return self.build_monitor.get_build_status(build)

    def _create_build_directory(self, build: Build) -> str:
        """Create temporary directory for build."""
        base_dir = self.config.get_temp_build_dir()
        build_dir = os.path.join(
            base_dir,
            f"build_{build.id}_{uuid.uuid4().hex[:8]}"
        )
        os.makedirs(build_dir, exist_ok=True)
        return build_dir

    def _store_apk(self, build: Build, apk_path: str) -> None:
        """Store APK file in media storage."""
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{build.project.package_name}_{build.version}_{timestamp}.apk"

        # Open and save APK file
        with open(apk_path, 'rb') as apk_file:
            build.apk_file.save(filename, File(apk_file))

        # Update file size
        build.apk_size = os.path.getsize(apk_path)
        build.save()

    def _log_build_progress(self, build: Build, message: str, level: str = 'INFO') -> None:
        """Log build progress to database."""
        BuildLog.objects.create(
            build=build,
            level=level,
            message=message,
            timestamp=timezone.now()
        )

    def _handle_build_failure(self, build: Build, output: str) -> None:
        """Handle build failure."""
        build.status = 'failed'
        build.completed_at = timezone.now()
        build.build_output = output
        build.error_message = self._extract_error_message(output)
        build.save()

        self._log_build_progress(
            build,
            f"Build failed: {build.error_message}",
            level='ERROR'
        )

    def _handle_build_exception(self, build: Build, exception: Exception) -> None:
        """Handle build exception."""
        build.status = 'failed'
        build.completed_at = timezone.now()
        build.error_message = str(exception)
        build.save()

        self._log_build_progress(
            build,
            f"Build failed with exception: {exception}",
            level='ERROR'
        )

    def _extract_error_message(self, output: str) -> str:
        """Extract meaningful error message from build output."""
        # Look for common Flutter error patterns
        error_patterns = [
            "Error:",
            "FAILURE:",
            "BUILD FAILED",
            "Could not",
            "Unable to",
        ]

        lines = output.split('\n')
        for line in lines:
            for pattern in error_patterns:
                if pattern in line:
                    return line.strip()

        # Return last non-empty line if no pattern found
        for line in reversed(lines):
            if line.strip():
                return line.strip()

        return "Build failed with unknown error"