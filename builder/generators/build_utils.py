"""Build utilities for Flutter project generation"""

import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

import logging

logger = logging.getLogger(__name__)


class FlutterBuildUtils:
    """Utilities for Flutter project building and management"""

    @staticmethod
    def check_flutter_installation() -> Tuple[bool, str]:
        """
        Check if Flutter is installed and get version

        Returns:
            Tuple of (is_installed, version_string)
        """
        try:
            result = subprocess.run(
                ['flutter', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Extract version from output
                version_match = re.search(r'Flutter (\d+\.\d+\.\d+)', result.stdout)
                version = version_match.group(1) if version_match else 'Unknown'
                return True, version

            return False, ''

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, ''

    @staticmethod
    def get_flutter_doctor_info() -> Dict[str, bool]:
        """
        Run flutter doctor and get status

        Returns:
            Dictionary with component status
        """
        try:
            result = subprocess.run(
                ['flutter', 'doctor', '-v'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return {}

            output = result.stdout

            # Parse flutter doctor output
            status = {
                'flutter': '✓ Flutter' in output,
                'android_toolchain': '✓ Android toolchain' in output,
                'xcode': '✓ Xcode' in output,
                'chrome': '✓ Chrome' in output,
                'android_studio': '✓ Android Studio' in output,
                'vs_code': '✓ VS Code' in output,
                'connected_device': '✓ Connected device' in output,
            }

            return status

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {}

    @staticmethod
    def validate_package_name(package_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Flutter/Android package name

        Args:
            package_name: Package name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check format
        pattern = r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$'
        if not re.match(pattern, package_name):
            return False, "Package name must be lowercase letters, numbers, and underscores in reverse domain notation"

        # Check parts
        parts = package_name.split('.')
        if len(parts) < 2:
            return False, "Package name must have at least two parts (e.g., com.example)"

        # Check reserved words
        reserved_words = {
            'abstract', 'as', 'assert', 'async', 'await', 'break', 'case', 'catch',
            'class', 'const', 'continue', 'default', 'deferred', 'do', 'dynamic',
            'else', 'enum', 'export', 'extends', 'extension', 'external', 'factory',
            'false', 'final', 'finally', 'for', 'function', 'get', 'hide', 'if',
            'implements', 'import', 'in', 'interface', 'is', 'late', 'library',
            'mixin', 'new', 'null', 'on', 'operator', 'part', 'required', 'rethrow',
            'return', 'set', 'show', 'static', 'super', 'switch', 'sync', 'this',
            'throw', 'true', 'try', 'typedef', 'var', 'void', 'while', 'with', 'yield'
        }

        for part in parts:
            if part in reserved_words:
                return False, f"'{part}' is a reserved keyword"

        return True, None

    @staticmethod
    def create_flutter_project(self, project_path: str, name: str, org: str, description: str = None) -> Tuple[bool, str]:
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
            # Build flutter create command
            cmd = [
                self.flutter_path, 'create',
                '--project-name', name,
                '--org', org,
                '--platforms', 'android',  # Only Android for now
                '.'  # Create in current directory
            ]

            if description:
                cmd.extend(['--description', description])

            # Run flutter create
            result = self.command_runner.run_command(
                cmd,
                cwd=project_path,
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

    @staticmethod
    def run_pub_get(project_dir: Path) -> Tuple[bool, Optional[str]]:
        """
        Run flutter pub get in project directory

        Returns:
            Tuple of (success, error_message)
        """
        try:
            result = subprocess.run(
                ['flutter', 'pub', 'get'],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                return True, None
            else:
                return False, result.stderr

        except subprocess.TimeoutExpired:
            return False, "Flutter pub get timed out"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def build_apk(
            project_dir: Path,
            build_mode: str = 'release',
            target_platform: Optional[str] = None,
            split_per_abi: bool = False,
            obfuscate: bool = False
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Build APK for the Flutter project

        Args:
            project_dir: Project directory
            build_mode: Build mode (debug, profile, release)
            target_platform: Target platform (android-arm, android-arm64, android-x64)
            split_per_abi: Whether to split APK per ABI
            obfuscate: Whether to obfuscate Dart code

        Returns:
            Tuple of (success, apk_path, error_message)
        """
        try:
            # Build command
            cmd = ['flutter', 'build', 'apk', f'--{build_mode}']

            if target_platform:
                cmd.extend(['--target-platform', target_platform])

            if split_per_abi:
                cmd.append('--split-per-abi')

            if obfuscate and build_mode == 'release':
                cmd.append('--obfuscate')
                cmd.append('--split-debug-info=build/app/outputs/symbols')

            # Run build
            result = subprocess.run(
                cmd,
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )

            if result.returncode == 0:
                # Find APK path
                apk_path = FlutterBuildUtils._find_apk(project_dir, build_mode, split_per_abi)
                if apk_path:
                    return True, str(apk_path), None
                else:
                    return False, None, "APK file not found after build"
            else:
                return False, None, result.stderr

        except subprocess.TimeoutExpired:
            return False, None, "Build timed out after 10 minutes"
        except Exception as e:
            return False, None, str(e)

    @staticmethod
    def _find_apk(project_dir: Path, build_mode: str, split_per_abi: bool) -> Optional[Path]:
        """Find generated APK file"""
        apk_dir = project_dir / 'build' / 'app' / 'outputs' / 'flutter-apk'

        if not apk_dir.exists():
            return None

        # Look for APK based on build configuration
        if split_per_abi:
            # Look for architecture-specific APKs
            patterns = [
                f'app-arm64-v8a-{build_mode}.apk',
                f'app-armeabi-v7a-{build_mode}.apk',
                f'app-x86_64-{build_mode}.apk'
            ]

            for pattern in patterns:
                apk_path = apk_dir / pattern
                if apk_path.exists():
                    return apk_path
        else:
            # Look for universal APK
            apk_path = apk_dir / f'app-{build_mode}.apk'
            if apk_path.exists():
                return apk_path

            # Sometimes it's just app.apk
            apk_path = apk_dir / 'app.apk'
            if apk_path.exists():
                return apk_path

        # Try to find any APK
        for apk_file in apk_dir.glob('*.apk'):
            return apk_file

        return None

    @staticmethod
    def clean_project(project_dir: Path) -> bool:
        """
        Clean Flutter project build artifacts

        Returns:
            Success status
        """
        try:
            # Run flutter clean
            result = subprocess.run(
                ['flutter', 'clean'],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            return result.returncode == 0

        except:
            # Fallback to manual cleaning
            try:
                dirs_to_clean = [
                    project_dir / 'build',
                    project_dir / '.dart_tool',
                    project_dir / '.flutter-plugins',
                    project_dir / '.flutter-plugins-dependencies'
                ]

                for dir_path in dirs_to_clean:
                    if dir_path.exists():
                        shutil.rmtree(dir_path, ignore_errors=True)

                return True
            except:
                return False

    @staticmethod
    def analyze_project(project_dir: Path) -> Tuple[bool, List[str]]:
        """
        Run flutter analyze on project

        Returns:
            Tuple of (has_errors, issues_list)
        """
        try:
            result = subprocess.run(
                ['flutter', 'analyze'],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=60
            )

            issues = []
            has_errors = False

            if result.returncode != 0:
                # Parse analyze output
                lines = result.stdout.split('\n')
                for line in lines:
                    if ' • ' in line:  # Flutter analyze issue format
                        issues.append(line.strip())
                        if ' error ' in line:
                            has_errors = True

            return has_errors, issues

        except:
            return True, ["Failed to analyze project"]

    @staticmethod
    def format_dart_code(project_dir: Path) -> bool:
        """
        Format Dart code in project

        Returns:
            Success status
        """
        try:
            result = subprocess.run(
                ['dart', 'format', '.'],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            return result.returncode == 0

        except:
            # Try with flutter format (older Flutter versions)
            try:
                result = subprocess.run(
                    ['flutter', 'format', '.'],
                    cwd=str(project_dir),
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                return result.returncode == 0
            except:
                return False

    @staticmethod
    def get_project_info(project_dir: Path) -> Dict[str, any]:
        """
        Get information about a Flutter project

        Returns:
            Project information dictionary
        """
        info = {
            'exists': project_dir.exists(),
            'has_pubspec': (project_dir / 'pubspec.yaml').exists(),
            'has_lib': (project_dir / 'lib').exists(),
            'has_build': (project_dir / 'build').exists(),
            'file_count': 0,
            'dart_files': [],
            'size_mb': 0
        }

        if not info['exists']:
            return info

        # Count files and get size
        total_size = 0
        dart_files = []

        for root, dirs, files in os.walk(project_dir):
            # Skip hidden and build directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'build']

            info['file_count'] += len(files)

            for file in files:
                file_path = Path(root) / file
                total_size += file_path.stat().st_size

                if file.endswith('.dart'):
                    rel_path = file_path.relative_to(project_dir)
                    dart_files.append(str(rel_path))

        info['dart_files'] = dart_files
        info['size_mb'] = round(total_size / (1024 * 1024), 2)

        return info

    @staticmethod
    def create_temp_project() -> Path:
        """Create a temporary directory for Flutter project"""
        return Path(tempfile.mkdtemp(prefix='flutter_project_'))

    @staticmethod
    def cleanup_temp_project(project_dir: Path):
        """Clean up temporary project directory"""
        if project_dir.exists() and str(project_dir).startswith(tempfile.gettempdir()):
            shutil.rmtree(project_dir, ignore_errors=True)