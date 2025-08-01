"""
Main build service for orchestrating Flutter app builds.
"""

import os
import logging
import re
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
            build_dir = self._create_build_directory(build)  # <-- build_dir is defined here

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

                # Update app version in pubspec.yaml
                pubspec_path = os.path.join(build_dir, 'pubspec.yaml')
                if os.path.exists(pubspec_path):
                    with open(pubspec_path, 'r') as f:
                        pubspec_content = f.read()

                    # Update version line
                    import re
                    version_line = f'version: {build.version_number}+{build.build_number}'
                    pubspec_content = re.sub(
                        r'^version:.*$',
                        version_line,
                        pubspec_content,
                        flags=re.MULTILINE
                    )

                    with open(pubspec_path, 'w') as f:
                        f.write(pubspec_content)

                    logger.info(f"Updated pubspec.yaml with version: {version_line}")

                # ===== ADD THE ANDROID FIX HERE =====
                # Ensure Android build files are properly configured
                self._ensure_android_build_files(build_dir, build)  # <-- Now build_dir is in scope

                # Ensure Android SDK is properly configured
                self._ensure_android_sdk_config(build_dir, build)

                # Clean any previous build artifacts
                logger.info("Cleaning previous builds...")
                self.flutter_builder._run_flutter_clean(build_dir)

                # Get dependencies
                logger.info("Getting Flutter dependencies...")
                result = self.flutter_builder._run_pub_get(build_dir)
                if not result:
                    raise RuntimeError("Failed to get Flutter dependencies")

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
                        # Build failed - extract more details
                        logger.error(f"Build failed with output: {output}")

                        # Try to extract the actual Gradle error
                        error_details = self._extract_gradle_error(output)
                        if error_details:
                            self._log_build_progress(build, f"Gradle error: {error_details}", level='error')

                        # Check for common issues
                        if "Could not resolve all files" in output:
                            self._log_build_progress(build, "Dependencies resolution failed. Check internet connection.", level='error')
                        elif "compileSdkVersion" in output:
                            self._log_build_progress(build, "SDK version mismatch. Check Android SDK installation.", level='error')
                        elif "AAPT2" in output or "aapt2" in output:
                            self._log_build_progress(build, "Android build tools issue. Try updating Android SDK build-tools.", level='error')

                        self._handle_build_failure(build, output)

                except Exception as build_error:
                    logger.error(f"Build process error: {str(build_error)}")
                    import traceback
                    full_traceback = traceback.format_exc()
                    logger.error(f"Build traceback: {full_traceback}")

                    # Store detailed error in build log
                    build.build_log = f"Build exception: {str(build_error)}\n\nTraceback:\n{full_traceback}"
                    build.save()

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

    def _extract_gradle_error(self, output: str) -> Optional[str]:
        """Extract specific Gradle error from build output."""
        lines = output.split('\n')
        error_section = []
        in_error = False

        for line in lines:
            # Look for Gradle error markers
            if "FAILURE: Build failed with an exception." in line:
                in_error = True
                continue

            if in_error:
                if "BUILD FAILED" in line:
                    break
                if line.strip() and not line.startswith('['):
                    error_section.append(line.strip())

        if error_section:
            # Look for "What went wrong:" section
            what_went_wrong = []
            capture = False
            for line in error_section:
                if "What went wrong:" in line:
                    capture = True
                    continue
                if capture and line.startswith('*'):
                    break
                if capture:
                    what_went_wrong.append(line)

            if what_went_wrong:
                return ' '.join(what_went_wrong).strip()

            return ' '.join(error_section[:3])  # First 3 lines of error

        return None

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

    def _fix_android_gradle_versions(self, project_dir: str):
        """Fix Android Gradle versions for compatibility"""
        import re

        # Check if using Kotlin DSL (.kts files)
        build_gradle_kts_path = os.path.join(project_dir, 'android', 'build.gradle.kts')
        build_gradle_path = os.path.join(project_dir, 'android', 'build.gradle')

        is_kotlin_dsl = os.path.exists(build_gradle_kts_path)

        if is_kotlin_dsl:
            logger.info("Project uses Kotlin DSL (build.gradle.kts)")
            self._fix_kotlin_dsl_gradle_versions(project_dir)
        else:
            logger.info("Project uses Groovy DSL (build.gradle)")
            self._fix_groovy_gradle_versions(project_dir)

    def _fix_kotlin_dsl_gradle_versions(self, project_dir: str):
        """Fix Gradle versions for Kotlin DSL projects"""
        import re

        # Fix android/build.gradle.kts
        build_gradle_kts_path = os.path.join(project_dir, 'android', 'build.gradle.kts')
        if os.path.exists(build_gradle_kts_path):
            logger.info(f"Fixing Android build.gradle.kts at: {build_gradle_kts_path}")

            with open(build_gradle_kts_path, 'r') as f:
                content = f.read()

            # Update Kotlin version
            content = re.sub(
                r'id\("org\.jetbrains\.kotlin\.android"\)\s+version\s+"[\d.]+"',
                'id("org.jetbrains.kotlin.android") version "1.7.10"',
                content
            )

            # If using buildscript block
            content = re.sub(
                r'kotlin_version\s*=\s*"[\d.]+"',
                'kotlin_version = "1.7.10"',
                content
            )

            # Update AGP version
            content = re.sub(
                r'id\("com\.android\.application"\)\s+version\s+"[\d.]+"',
                'id("com.android.application") version "7.3.0"',
                content
            )

            # For buildscript dependencies
            content = re.sub(
                r'classpath\("com\.android\.tools\.build:gradle:[\d.]+"\)',
                'classpath("com.android.tools.build:gradle:7.3.0")',
                content
            )

            with open(build_gradle_kts_path, 'w') as f:
                f.write(content)

            logger.info("Updated android/build.gradle.kts versions")

        # Fix android/app/build.gradle.kts
        app_build_gradle_kts_path = os.path.join(project_dir, 'android', 'app', 'build.gradle.kts')
        if os.path.exists(app_build_gradle_kts_path):
            logger.info("Fixing android/app/build.gradle.kts")

            with open(app_build_gradle_kts_path, 'r') as f:
                content = f.read()

            # Replace Flutter SDK references with concrete values
            content = re.sub(r'compileSdk\s*=\s*flutter\.compileSdkVersion', 'compileSdk = 33', content)
            content = re.sub(r'targetSdk\s*=\s*flutter\.targetSdkVersion', 'targetSdk = 33', content)
            content = re.sub(r'minSdk\s*=\s*flutter\.minSdkVersion', 'minSdk = 21', content)

            # Also check for integer assignments
            content = re.sub(r'compileSdkVersion\s*\d+', 'compileSdk = 33', content)
            content = re.sub(r'targetSdkVersion\s*\d+', 'targetSdk = 33', content)
            content = re.sub(r'minSdkVersion\s*\d+', 'minSdk = 21', content)

            with open(app_build_gradle_kts_path, 'w') as f:
                f.write(content)

            logger.info("Fixed android/app/build.gradle.kts SDK versions")

        # Fix gradle-wrapper.properties (same for both DSLs)
        self._fix_gradle_wrapper(project_dir)

    def _fix_groovy_gradle_versions(self, project_dir: str):
        """Fix Gradle versions for Groovy DSL projects"""
        import re

        # Fix android/build.gradle
        build_gradle_path = os.path.join(project_dir, 'android', 'build.gradle')
        if os.path.exists(build_gradle_path):
            logger.info(f"Fixing Android build.gradle at: {build_gradle_path}")

            with open(build_gradle_path, 'r') as f:
                content = f.read()

            # Ensure buildscript block has kotlin_version defined
            if 'buildscript {' in content and 'ext.kotlin_version' not in content:
                # Add kotlin version at the beginning of buildscript block
                content = content.replace(
                    'buildscript {',
                    "buildscript {\n    ext.kotlin_version = '1.7.10'"
                )
            else:
                # Update existing kotlin version
                content = re.sub(
                    r"ext\.kotlin_version\s*=\s*['\"][\d.]+['\"]",
                    "ext.kotlin_version = '1.7.10'",
                    content
                )

            # Ensure repositories are defined in buildscript
            if 'buildscript {' in content and 'repositories {' not in content.split('buildscript {')[1].split('}')[0]:
                content = re.sub(
                    r'buildscript\s*{\s*\n(\s*ext\.kotlin_version[^\n]*\n)?',
                    lambda m: m.group(0) + '    repositories {\n        google()\n        mavenCentral()\n    }\n',
                    content
                )

            # Ensure dependencies block exists in buildscript
            buildscript_content = content.split('buildscript {')[1].split('}')[0] if 'buildscript {' in content else ''
            if 'dependencies {' not in buildscript_content:
                # Add dependencies block before closing buildscript
                content = re.sub(
                    r'(buildscript\s*{[^}]+)(})',
                    r'\1    dependencies {\n        classpath "com.android.tools.build:gradle:7.3.0"\n        classpath "org.jetbrains.kotlin:kotlin-gradle-plugin:$kotlin_version"\n    }\n\2',
                    content,
                    count=1
                )
            else:
                # Update Android Gradle Plugin version
                content = re.sub(
                    r"classpath\s+['\"]com\.android\.tools\.build:gradle:[\d.]+['\"]",
                    "classpath 'com.android.tools.build:gradle:7.3.0'",
                    content
                )

                # Ensure kotlin gradle plugin is included
                if 'kotlin-gradle-plugin' not in content:
                    content = re.sub(
                        r"(dependencies\s*{[^}]*)(classpath\s+['\"]com\.android\.tools\.build:gradle[^'\"]+['\"])",
                        r'\1\2\n        classpath "org.jetbrains.kotlin:kotlin-gradle-plugin:$kotlin_version"',
                        content
                    )

            with open(build_gradle_path, 'w') as f:
                f.write(content)

            logger.info("Updated android/build.gradle with Kotlin plugin configuration")

        # Fix android/app/build.gradle
        app_build_gradle_path = os.path.join(project_dir, 'android', 'app', 'build.gradle')
        if os.path.exists(app_build_gradle_path):
            logger.info("Fixing android/app/build.gradle")

            with open(app_build_gradle_path, 'r') as f:
                content = f.read()

            # Replace Flutter SDK references with concrete values
            content = re.sub(r'compileSdkVersion\s+flutter\.compileSdkVersion', 'compileSdkVersion 33', content)
            content = re.sub(r'targetSdkVersion\s+flutter\.targetSdkVersion', 'targetSdkVersion 33', content)
            content = re.sub(r'minSdkVersion\s+flutter\.minSdkVersion', 'minSdkVersion 21', content)

            # Also update direct version numbers
            content = re.sub(r'compileSdkVersion\s+\d+', 'compileSdkVersion 33', content)
            content = re.sub(r'targetSdkVersion\s+\d+', 'targetSdkVersion 33', content)
            content = re.sub(r'minSdkVersion\s+\d+', 'minSdkVersion 21', content)

            with open(app_build_gradle_path, 'w') as f:
                f.write(content)

            logger.info("Fixed android/app/build.gradle SDK versions")

        # Fix gradle-wrapper.properties
        self._fix_gradle_wrapper(project_dir)

    def _fix_gradle_wrapper(self, project_dir: str):
        """Fix gradle-wrapper.properties (common for both DSLs)"""
        import re

        gradle_wrapper_path = os.path.join(project_dir, 'android', 'gradle', 'wrapper', 'gradle-wrapper.properties')
        if os.path.exists(gradle_wrapper_path):
            logger.info("Fixing gradle-wrapper.properties")

            with open(gradle_wrapper_path, 'r') as f:
                content = f.read()

            # Update to Gradle 7.5
            content = re.sub(
                r'distributionUrl=.*gradle-[\d.]+-.*\.zip',
                'distributionUrl=https\\://services.gradle.org/distributions/gradle-7.5-all.zip',
                content
            )

            with open(gradle_wrapper_path, 'w') as f:
                f.write(content)

            logger.info("Fixed Gradle wrapper version to 7.5")
    def _ensure_android_sdk_config(self, project_dir: str, build):
        """Ensure Android SDK is properly configured"""
        # Create/update local.properties
        local_properties_path = os.path.join(project_dir, 'android', 'local.properties')

        android_sdk = (self.config.android_sdk_path or
                       os.environ.get('ANDROID_SDK_ROOT') or
                       os.environ.get('ANDROID_HOME', ''))

        flutter_sdk = (self.config.flutter_sdk_path or
                       os.environ.get('FLUTTER_ROOT', ''))

        # Write local.properties
        local_properties_content = []
        if android_sdk:
            # Use forward slashes even on Windows
            android_sdk = android_sdk.replace('\\', '/')
            local_properties_content.append(f'sdk.dir={android_sdk}')
        if flutter_sdk:
            # Use forward slashes even on Windows
            flutter_sdk = flutter_sdk.replace('\\', '/')
            local_properties_content.append(f'flutter.sdk={flutter_sdk}')

        # Add version information as simple integers
        local_properties_content.append(f'flutter.buildMode={build.build_type}')
        local_properties_content.append(f'flutter.versionName={build.version_number}')
        # Ensure versionCode is an integer
        local_properties_content.append(f'flutter.versionCode={build.build_number}')

        with open(local_properties_path, 'w') as f:
            f.write('\n'.join(local_properties_content))

        logger.info(f"Created local.properties with Android SDK: {android_sdk}")

        # Also create gradle.properties with basic settings
        gradle_properties_path = os.path.join(project_dir, 'android', 'gradle.properties')
        if not os.path.exists(gradle_properties_path):
            gradle_properties_content = '''org.gradle.jvmargs=-Xmx4G -XX:MaxMetaspaceSize=2G -XX:+HeapDumpOnOutOfMemoryError
    android.useAndroidX=true
    android.enableJetifier=true
    kotlin.code.style=official
    android.nonTransitiveRClass=true
    android.nonFinalResIds=true
    '''
            with open(gradle_properties_path, 'w') as f:
                f.write(gradle_properties_content)

            logger.info("Created gradle.properties with memory settings")

        # with open(local_properties_path, 'w') as f:
        #     f.write(local_properties_content)
        #
        # logger.info(f"Created local.properties with Android SDK: {android_sdk}")

        # Create gradle.properties if it doesn't exist
        gradle_properties_path = os.path.join(project_dir, 'android', 'gradle.properties')
        if not os.path.exists(gradle_properties_path):
            gradle_properties_content = '''org.gradle.jvmargs=-Xmx1536M
android.useAndroidX=true
android.enableJetifier=true
'''
            with open(gradle_properties_path, 'w') as f:
                f.write(gradle_properties_content)

            logger.info("Created gradle.properties")

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

    def _ensure_android_build_files(self, project_dir: str, build):
        """Ensure Android build files are properly configured"""
        logger.info("Skipping Android build file modifications - using Flutter defaults")

        # Only ensure local.properties exists with SDK paths
        local_properties_path = os.path.join(project_dir, 'android', 'local.properties')

        android_sdk = (self.config.android_sdk_path or
                       os.environ.get('ANDROID_SDK_ROOT') or
                       os.environ.get('ANDROID_HOME', ''))

        flutter_sdk = (self.config.flutter_sdk_path or
                       os.environ.get('FLUTTER_ROOT', ''))

        # Only write local.properties if we have SDK paths
        if android_sdk or flutter_sdk:
            local_properties_content = []
            if android_sdk:
                local_properties_content.append(f'sdk.dir={android_sdk}')
            if flutter_sdk:
                local_properties_content.append(f'flutter.sdk={flutter_sdk}')

            local_properties_content.append(f'flutter.buildMode={build.build_type}')
            local_properties_content.append(f'flutter.versionName={build.version_number}')
            local_properties_content.append(f'flutter.versionCode={build.build_number}')

            with open(local_properties_path, 'w') as f:
                f.write('\n'.join(local_properties_content))

            logger.info(f"Created local.properties with SDK paths")