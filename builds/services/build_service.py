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
# Don't import at module level to avoid circular imports

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
        """
        logger.info(f"Starting build {build.id} for project {build.project.name}")

        try:
            # Check if project has screens
            if not build.project.screens.exists():
                raise RuntimeError("Project has no screens. Please add at least one screen before building.")

            # Update build status
            build.status = 'building'
            build.started_at = timezone.now()
            build.save()

            # Create build log
            build_log = BuildLog.objects.create(
                build=build,
                level='info',
                stage='build_process',
                message='Build process started'
            )

            # Check Flutter SDK
            if not self.flutter_builder.check_flutter_sdk():
                raise RuntimeError("Flutter SDK not found or not properly configured")

            # Create temporary build directory
            build_dir = self._create_build_directory(build)

            try:
                # First, create a proper Flutter project structure using flutter create
                logger.info("Creating Flutter project structure...")
                self._log_build_progress(build, "Creating Flutter project structure", level='info')

                # Extract package name parts
                package_parts = build.project.package_name.split('.')
                org = '.'.join(package_parts[:-1])
                name = package_parts[-1]

                # Run flutter create to get proper project structure
                create_result = self.flutter_builder.create_flutter_project(
                    build_dir,
                    name=name,
                    org=org,
                    description=build.project.description or "Flutter app"
                )

                if not create_result[0]:
                    raise RuntimeError(f"Failed to create Flutter project: {create_result[1]}")

                # Now generate our custom Flutter code
                logger.info("Generating Flutter code...")
                self._log_build_progress(build, "Generating Flutter code", level='info')

                try:
                    # Import here to avoid circular imports
                    from builder.generators.flutter_generator import FlutterGenerator

                    generator = FlutterGenerator(build.project)
                    generated_files = generator.generate_project()
                except Exception as gen_error:
                    logger.error(f"Code generation failed: {str(gen_error)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    raise RuntimeError(f"Code generation failed: {str(gen_error)}")

                # Write generated files (only Dart/Flutter files, preserve platform files)
                logger.info(f"Writing custom files to {build_dir}")
                self._log_build_progress(build, f"Writing custom project files", level='info')

                # Only write Dart/Flutter specific files
                flutter_files_only = {}
                for file_path, content in generated_files.items():
                    # Only include:
                    # - Dart source files (lib/)
                    # - Flutter configuration (pubspec.yaml, l10n.yaml)
                    # - Asset files
                    # Skip all platform-specific files (android/, ios/, web/, etc.)
                    if (file_path.startswith('lib/') or
                            file_path == 'pubspec.yaml' or
                            file_path == 'l10n.yaml' or
                            file_path.startswith('assets/') or
                            file_path == 'analysis_options.yaml'):
                        flutter_files_only[file_path] = content
                        logger.debug(f"Writing Flutter file: {file_path}")
                    else:
                        logger.debug(f"Skipping platform-specific file: {file_path}")

                self.file_manager.write_project_files(build_dir, flutter_files_only)

                # Create or update local.properties (don't overwrite the whole file)
                local_properties_path = os.path.join(build_dir, 'android', 'local.properties')
                if os.path.exists(local_properties_path):
                    # Read existing content
                    with open(local_properties_path, 'r') as f:
                        existing_content = f.read()

                    # Update or add our properties
                    properties = {
                        'flutter.buildMode': build.build_type,
                        'flutter.versionName': str(build.version_number),
                        'flutter.versionCode': str(build.build_number)
                    }

                    lines = existing_content.split('\n')
                    updated_lines = []

                    for line in lines:
                        if '=' in line:
                            key = line.split('=')[0].strip()
                            if key not in properties:
                                updated_lines.append(line)
                        else:
                            updated_lines.append(line)

                    # Add our properties
                    for key, value in properties.items():
                        updated_lines.append(f'{key}={value}')

                    with open(local_properties_path, 'w') as f:
                        f.write('\n'.join(updated_lines))
                else:
                    # Create new local.properties
                    with open(local_properties_path, 'w') as f:
                        f.write(f'''sdk.dir={self.config.android_sdk_path or os.environ.get('ANDROID_SDK_ROOT', '')}
flutter.sdk={self.config.flutter_sdk_path or os.environ.get('FLUTTER_ROOT', '')}
flutter.buildMode={build.build_type}
flutter.versionName={build.version_number}
flutter.versionCode={build.build_number}
''')

                # Build APK
                logger.info("Building APK...")
                self._log_build_progress(build, "Running Flutter build", level='info')

                try:
                    success, output, apk_path = self.flutter_builder.build_apk(
                        build_dir,
                        build_mode=build.build_type
                    )

                    # Store the build output regardless of success/failure
                    build.build_log = output

                    if success:
                        # Store APK file
                        logger.info(f"Build successful, APK at: {apk_path}")
                        self._log_build_progress(build, f"Build successful: {apk_path}", level='info')

                        self._store_apk(build, apk_path)

                        # Update build status
                        build.status = 'success'
                        build.completed_at = timezone.now()
                        build.save()

                        self._log_build_progress(build, "Build completed successfully", level='info')
                    else:
                        # Build failed
                        logger.error(f"Build failed: {output}")
                        self._handle_build_failure(build, output)

                except Exception as build_error:
                    logger.error(f"Build process error: {str(build_error)}")
                    import traceback
                    logger.error(f"Build traceback: {traceback.format_exc()}")
                    raise RuntimeError(f"Build process failed: {str(build_error)}")

            except Exception as e:
                logger.error(f"Error during build process: {str(e)}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                raise

            finally:
                # Clean up temporary directory
                logger.info(f"Cleaning up build directory: {build_dir}")
                self.file_manager.cleanup_directory(build_dir)

            return build

        except Exception as e:
            logger.exception(f"Build {build.id} failed with exception")
            import traceback
            error_details = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            self._handle_build_exception(build, e, error_details)
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
            level=level.lower(),  # Convert to lowercase to match model choices
            message=message,
            stage='build_process'  # Add the required stage field
            # Remove timestamp=timezone.now() as created_at is auto-populated
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

    def _handle_build_exception(self, build: Build, exception: Exception, details: str = None) -> None:
        """Handle build exception."""
        build.status = 'failed'
        build.completed_at = timezone.now()
        build.error_message = str(exception)

        # Store detailed error in build_log
        if details:
            build.build_log = f"Error: {str(exception)}\n\n{details}"
        else:
            build.build_log = f"Error: {str(exception)}"

        build.save()

        self._log_build_progress(
            build,
            f"Build failed with exception: {exception}",
            level='error'
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
    def _ensure_flutter_project_structure(self, build_dir: str):
        """Ensure Flutter project has all required directories"""
        directories = [
            'lib',
            'lib/screens',
            'lib/theme',
            'lib/l10n',
            'android/app/src/main',
            'ios/Runner',
            'assets/images',
            'test'
        ]

        for directory in directories:
            dir_path = os.path.join(build_dir, directory)
            os.makedirs(dir_path, exist_ok=True)

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