"""
File management utilities for handling build files and directories.
"""

import os
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class FileManager:
    """Utility class for managing build files and directories."""

    def create_temp_directory(self, prefix: str = 'flutter_build_') -> str:
        """
        Create a temporary directory for build.

        Args:
            prefix: Directory name prefix

        Returns:
            Path to created directory
        """
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        logger.debug(f"Created temporary directory: {temp_dir}")
        return temp_dir

    def write_project_files(self, base_dir: str, files: Dict[str, str]) -> None:
        """
        Write project files to directory structure.

        Args:
            base_dir: Base directory for the project
            files: Dictionary mapping file paths to content
        """
        logger.info(f"Writing {len(files)} files to {base_dir}")

        for file_path, content in files.items():
            full_path = os.path.join(base_dir, file_path)

            # Create directory if needed
            dir_path = os.path.dirname(full_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                logger.debug(f"Created directory: {dir_path}")

            # Write file
            try:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.debug(f"Wrote file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to write file {file_path}: {e}")
                raise

    def copy_file(self, src: str, dst: str) -> None:
        """
        Copy file from source to destination.

        Args:
            src: Source file path
            dst: Destination file path
        """
        # Create destination directory if needed
        dst_dir = os.path.dirname(dst)
        if dst_dir and not os.path.exists(dst_dir):
            os.makedirs(dst_dir, exist_ok=True)

        shutil.copy2(src, dst)
        logger.debug(f"Copied file: {src} -> {dst}")

    def copy_directory(self, src: str, dst: str) -> None:
        """
        Copy entire directory tree.

        Args:
            src: Source directory path
            dst: Destination directory path
        """
        shutil.copytree(src, dst)
        logger.debug(f"Copied directory: {src} -> {dst}")

    def cleanup_directory(self, path: str) -> bool:
        """
        Remove directory and all its contents.

        Args:
            path: Directory path to remove

        Returns:
            True if successful
        """
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
                logger.debug(f"Removed directory: {path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove directory {path}: {e}")
            return False

    def get_directory_size(self, path: str) -> int:
        """
        Get total size of directory in bytes.

        Args:
            path: Directory path

        Returns:
            Size in bytes
        """
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except:
                    pass
        return total_size

    def find_files(self, directory: str, pattern: str) -> List[str]:
        """
        Find files matching pattern in directory.

        Args:
            directory: Directory to search
            pattern: File pattern (e.g., '*.apk')

        Returns:
            List of matching file paths
        """
        path = Path(directory)
        return [str(p) for p in path.rglob(pattern)]

    def ensure_directory_exists(self, path: str) -> None:
        """
        Ensure directory exists, create if not.

        Args:
            path: Directory path
        """
        os.makedirs(path, exist_ok=True)
        logger.debug(f"Ensured directory exists: {path}")

    def read_file(self, path: str) -> Optional[str]:
        """
        Read file content.

        Args:
            path: File path

        Returns:
            File content or None if error
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            return None

    def write_binary_file(self, path: str, data: bytes) -> bool:
        """
        Write binary data to file.

        Args:
            path: File path
            data: Binary data

        Returns:
            True if successful
        """
        try:
            # Create directory if needed
            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            with open(path, 'wb') as f:
                f.write(data)

            logger.debug(f"Wrote binary file: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write binary file {path}: {e}")
            return False

    def get_available_space(self, path: str) -> int:
        """
        Get available disk space for path.

        Args:
            path: Directory path

        Returns:
            Available space in bytes
        """
        try:
            stat = os.statvfs(path) if hasattr(os, 'statvfs') else None
            if stat:
                return stat.f_bavail * stat.f_frsize
            else:
                # Windows
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(path),
                    ctypes.pointer(free_bytes),
                    None,
                    None
                )
                return free_bytes.value
        except:
            return 0

    def is_path_safe(self, path: str, base_dir: str) -> bool:
        """
        Check if path is safe (within base directory).

        Args:
            path: Path to check
            base_dir: Base directory

        Returns:
            True if path is safe
        """
        try:
            # Resolve to absolute paths
            abs_path = os.path.abspath(path)
            abs_base = os.path.abspath(base_dir)

            # Check if path is within base directory
            return abs_path.startswith(abs_base)
        except:
            return False

    def create_zip_archive(self, source_dir: str, output_path: str) -> bool:
        """
        Create ZIP archive from directory.

        Args:
            source_dir: Directory to archive
            output_path: Output ZIP file path

        Returns:
            True if successful
        """
        try:
            # Remove .zip extension as shutil adds it
            if output_path.endswith('.zip'):
                output_path = output_path[:-4]

            shutil.make_archive(output_path, 'zip', source_dir)
            logger.debug(f"Created ZIP archive: {output_path}.zip")
            return True

        except Exception as e:
            logger.error(f"Failed to create ZIP archive: {e}")
            return False