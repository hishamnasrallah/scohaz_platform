import os
import tempfile
import shutil
from datetime import datetime
from typing import Optional
from django.utils import timezone
from django.conf import settings
from simple_builds.models import Build, BuildLog
from simple_builder.generators.flutter_generator import FlutterGenerator
from .flutter_builder import FlutterBuilder


class BuildService:
    """Orchestrates the build process"""

    def __init__(self):
        self.flutter_builder = FlutterBuilder()

    def start_build(self, build: Build):
        """Start the build process"""
        temp_dir = None

        try:
            # Update build status
            build.status = 'building'
            build.started_at = timezone.now()
            build.save()

            self._log(build, 'info', 'setup', 'Build process started')

            # Check if using mock build
            if getattr(settings, 'USE_MOCK_BUILD', True):  # Default to True for testing
                self._run_mock_build(build)
                return

            # Check Flutter installation
            success, message = self.flutter_builder.check_flutter_installation()
            if not success:
                raise Exception(f"Flutter not properly installed: {message}")

            # Parse Flutter version
            if 'Flutter' in message:
                for line in message.split('\n'):
                    if 'Flutter' in line and 'channel' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'Flutter' and i + 1 < len(parts):
                                build.flutter_version = parts[i + 1]
                                break
                    if 'Dart' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'Dart' and i + 1 < len(parts):
                                build.dart_version = parts[i + 1]
                                break
                build.save()

            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            project_name = build.project.package_name.split('.')[-1]
            project_path = os.path.join(temp_dir, project_name)

            self._log(build, 'info', 'setup', f'Created temporary directory: {temp_dir}')

            # Generate Flutter code
            self._log(build, 'info', 'generate', 'Generating Flutter code...')
            generator = FlutterGenerator(build.project)
            files = generator.generate_project()

            # Create Flutter project structure
            self._log(build, 'info', 'create', 'Creating Flutter project structure...')
            org = '.'.join(build.project.package_name.split('.')[:-1])

            success, message = self.flutter_builder.create_flutter_project(
                project_path,
                project_name,
                org,
                build.project.description or "Flutter app"
            )

            if not success:
                raise Exception(f"Failed to create Flutter project: {message}")

            # Write generated files
            self._log(build, 'info', 'write', 'Writing generated files...')
            for filepath, content in files.items():
                full_path = os.path.join(project_path, filepath)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            # Fix Gradle issues
            self.flutter_builder._fix_gradle_issues(project_path)

            # Build APK
            self._log(build, 'info', 'build', f'Building {build.build_type} APK...')
            success, message, apk_path = self.flutter_builder.build_apk(
                project_path,
                build.build_type
            )

            if not success:
                raise Exception(f"Build failed: {message}")

            # Save APK
            self._log(build, 'info', 'save', 'Saving APK file...')
            build.save_apk(apk_path)

            # Update build status
            build.status = 'success'
            build.completed_at = timezone.now()
            build.duration_seconds = int((build.completed_at - build.started_at).total_seconds())
            build.save()

            self._log(build, 'info', 'complete', 'Build completed successfully')

        except Exception as e:
            # Handle build failure
            build.status = 'failed'
            build.error_message = str(e)
            build.completed_at = timezone.now()
            if build.started_at:
                build.duration_seconds = int((build.completed_at - build.started_at).total_seconds())
            build.save()

            self._log(build, 'error', 'error', str(e))

        finally:
            # Cleanup
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    self._log(build, 'info', 'cleanup', 'Cleaned up temporary files')
                except Exception as e:
                    self._log(build, 'warning', 'cleanup', f'Failed to cleanup: {e}')

    def _run_mock_build(self, build: Build):
        """Run a mock build for testing without Flutter"""
        import time

        self._log(build, 'info', 'mock', 'Running mock build (Flutter not required)')

        # Simulate build stages
        stages = [
            ('generate', 'Generating Flutter code...', 1),
            ('create', 'Creating project structure...', 1),
            ('dependencies', 'Resolving dependencies...', 2),
            ('compile', 'Compiling application...', 3),
            ('package', 'Packaging APK...', 2),
        ]

        for stage, message, duration in stages:
            self._log(build, 'info', stage, message)
            time.sleep(duration)

        # Mock successful completion
        build.status = 'success'
        build.flutter_version = '3.10.0 (mock)'
        build.dart_version = '3.0.0 (mock)'
        build.completed_at = timezone.now()
        build.duration_seconds = int((build.completed_at - build.started_at).total_seconds())

        # Create a mock APK file
        mock_apk_content = b'This is a mock APK file for testing purposes'
        from django.core.files.base import ContentFile
        filename = f"{build.project.package_name}-{build.version_number}-{build.build_type}-mock.apk"
        build.apk_file.save(filename, ContentFile(mock_apk_content))
        build.apk_size = len(mock_apk_content)

        build.save()

        self._log(build, 'info', 'complete', 'Mock build completed successfully')

    def _log(self, build: Build, level: str, stage: str, message: str):
        """Create a build log entry"""
        BuildLog.objects.create(
            build=build,
            level=level,
            stage=stage,
            message=message
        )