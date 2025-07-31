"""
APK signing utilities for production builds.
"""

import os
import logging
from typing import Optional, Tuple

from django.conf import settings

from builds.utils.command_runner import CommandRunner

logger = logging.getLogger(__name__)


class APKSigner:
    """Utility class for signing APK files."""

    def __init__(self):
        self.command_runner = CommandRunner()
        self.keystore_path = getattr(settings, 'ANDROID_KEYSTORE_PATH', None)
        self.keystore_password = getattr(settings, 'ANDROID_KEYSTORE_PASSWORD', None)
        self.key_alias = getattr(settings, 'ANDROID_KEY_ALIAS', None)
        self.key_password = getattr(settings, 'ANDROID_KEY_PASSWORD', None)

    def is_signing_configured(self) -> bool:
        """
        Check if APK signing is properly configured.

        Returns:
            True if signing is configured
        """
        return all([
            self.keystore_path,
            self.keystore_password,
            self.key_alias,
            self.key_password,
            os.path.exists(self.keystore_path) if self.keystore_path else False
        ])

    def sign_apk(self, apk_path: str, output_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Sign an APK file.

        Args:
            apk_path: Path to unsigned APK
            output_path: Path for signed APK (optional)

        Returns:
            Tuple of (success, message)
        """
        if not self.is_signing_configured():
            logger.warning("APK signing not configured")
            return False, "APK signing not configured"

        if not os.path.exists(apk_path):
            return False, f"APK file not found: {apk_path}"

        # Use apksigner tool
        apksigner = self._find_apksigner()
        if not apksigner:
            return False, "apksigner tool not found"

        # Prepare output path
        if not output_path:
            base, ext = os.path.splitext(apk_path)
            output_path = f"{base}-signed{ext}"

        # Build signing command
        cmd = [
            apksigner,
            'sign',
            '--ks', self.keystore_path,
            '--ks-pass', f'pass:{self.keystore_password}',
            '--ks-key-alias', self.key_alias,
            '--key-pass', f'pass:{self.key_password}',
            '--out', output_path,
            apk_path
        ]

        # Run signing command
        result = self.command_runner.run_command(cmd, timeout=60)

        if result.returncode == 0:
            logger.info(f"APK signed successfully: {output_path}")
            return True, output_path
        else:
            logger.error(f"APK signing failed: {result.stderr}")
            return False, result.stderr

    def verify_signature(self, apk_path: str) -> Tuple[bool, str]:
        """
        Verify APK signature.

        Args:
            apk_path: Path to APK file

        Returns:
            Tuple of (valid, message)
        """
        if not os.path.exists(apk_path):
            return False, f"APK file not found: {apk_path}"

        # Use apksigner tool
        apksigner = self._find_apksigner()
        if not apksigner:
            return False, "apksigner tool not found"

        # Run verification command
        cmd = [apksigner, 'verify', '--verbose', apk_path]
        result = self.command_runner.run_command(cmd, timeout=30)

        if result.returncode == 0:
            logger.info(f"APK signature valid: {apk_path}")
            return True, result.stdout
        else:
            logger.error(f"APK signature invalid: {result.stderr}")
            return False, result.stderr

    def _find_apksigner(self) -> Optional[str]:
        """
        Find apksigner tool in Android SDK.

        Returns:
            Path to apksigner or None
        """
        # Check if apksigner is in PATH
        if self.command_runner.check_command_exists('apksigner'):
            return 'apksigner'

        # Check Android SDK path
        android_sdk = os.environ.get('ANDROID_SDK_ROOT') or \
                      os.environ.get('ANDROID_HOME') or \
                      getattr(settings, 'ANDROID_SDK_PATH', None)

        if android_sdk:
            # Look for apksigner in build-tools
            build_tools_dir = os.path.join(android_sdk, 'build-tools')
            if os.path.exists(build_tools_dir):
                # Get latest version
                versions = sorted([
                    d for d in os.listdir(build_tools_dir)
                    if os.path.isdir(os.path.join(build_tools_dir, d))
                ], reverse=True)

                for version in versions:
                    apksigner_path = os.path.join(
                        build_tools_dir, version, 'apksigner'
                    )
                    if os.path.exists(apksigner_path):
                        return apksigner_path

                    # Windows
                    apksigner_path = f"{apksigner_path}.bat"
                    if os.path.exists(apksigner_path):
                        return apksigner_path

        return None

    def create_debug_keystore(self) -> Tuple[bool, str]:
        """
        Create a debug keystore for development builds.

        Returns:
            Tuple of (success, keystore_path)
        """
        keystore_dir = os.path.join(settings.MEDIA_ROOT, 'keystores')
        os.makedirs(keystore_dir, exist_ok=True)

        keystore_path = os.path.join(keystore_dir, 'debug.keystore')

        # Skip if already exists
        if os.path.exists(keystore_path):
            return True, keystore_path

        # Use keytool to create keystore
        cmd = [
            'keytool',
            '-genkey',
            '-v',
            '-keystore', keystore_path,
            '-alias', 'androiddebugkey',
            '-keyalg', 'RSA',
            '-keysize', '2048',
            '-validity', '10000',
            '-storepass', 'android',
            '-keypass', 'android',
            '-dname', 'CN=Android Debug,O=Android,C=US'
        ]

        result = self.command_runner.run_command(cmd, timeout=30)

        if result.returncode == 0:
            logger.info(f"Debug keystore created: {keystore_path}")
            return True, keystore_path
        else:
            logger.error(f"Failed to create debug keystore: {result.stderr}")
            return False, ""