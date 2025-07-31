"""
Utility for running shell commands with proper error handling and timeout.
"""

import logging
import subprocess
import os
from typing import List, Optional, Dict, Union

logger = logging.getLogger(__name__)


class CommandRunner:
    """Utility class for running shell commands safely."""

    def run_command(
            self,
            command: List[str],
            cwd: Optional[str] = None,
            env: Optional[Dict[str, str]] = None,
            timeout: Optional[int] = None,
            capture_output: bool = True,
            shell: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Run a shell command with proper error handling.

        Args:
            command: Command and arguments as list
            cwd: Working directory for the command
            env: Environment variables
            timeout: Command timeout in seconds
            capture_output: Whether to capture stdout/stderr
            shell: Whether to run command in shell

        Returns:
            CompletedProcess instance with results
        """
        # Prepare environment
        cmd_env = os.environ.copy()
        if env:
            cmd_env.update(env)

        # Log command execution
        cmd_str = ' '.join(command) if isinstance(command, list) else command
        logger.debug(f"Running command: {cmd_str}")
        if cwd:
            logger.debug(f"Working directory: {cwd}")

        try:
            # Run command
            result = subprocess.run(
                command,
                cwd=cwd,
                env=cmd_env,
                timeout=timeout,
                capture_output=capture_output,
                text=True,
                shell=shell
            )

            # Log result
            if result.returncode == 0:
                logger.debug(f"Command succeeded: {cmd_str}")
            else:
                logger.warning(f"Command failed with code {result.returncode}: {cmd_str}")
                if result.stderr:
                    logger.warning(f"Error output: {result.stderr}")

            return result

        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out after {timeout}s: {cmd_str}")
            # Create a CompletedProcess-like object for timeout
            return subprocess.CompletedProcess(
                args=command,
                returncode=-1,
                stdout=e.stdout.decode() if e.stdout else '',
                stderr=e.stderr.decode() if e.stderr else f'Command timed out after {timeout} seconds'
            )

        except Exception as e:
            logger.exception(f"Command execution failed: {cmd_str}")
            # Create a CompletedProcess-like object for exception
            return subprocess.CompletedProcess(
                args=command,
                returncode=-1,
                stdout='',
                stderr=str(e)
            )

    def run_command_async(
            self,
            command: List[str],
            cwd: Optional[str] = None,
            env: Optional[Dict[str, str]] = None
    ) -> subprocess.Popen:
        """
        Start a command asynchronously.

        Args:
            command: Command and arguments as list
            cwd: Working directory for the command
            env: Environment variables

        Returns:
            Popen instance for the running process
        """
        # Prepare environment
        cmd_env = os.environ.copy()
        if env:
            cmd_env.update(env)

        # Log command execution
        cmd_str = ' '.join(command)
        logger.debug(f"Starting async command: {cmd_str}")

        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=cmd_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            logger.debug(f"Async process started with PID: {process.pid}")
            return process

        except Exception as e:
            logger.exception(f"Failed to start async command: {cmd_str}")
            raise

    def check_command_exists(self, command: str) -> bool:
        """
        Check if a command exists in the system PATH.

        Args:
            command: Command name to check

        Returns:
            True if command exists
        """
        try:
            result = self.run_command(
                ['which', command] if os.name != 'nt' else ['where', command],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def get_command_version(self, command: str, version_flag: str = '--version') -> Optional[str]:
        """
        Get version string for a command.

        Args:
            command: Command name
            version_flag: Flag to get version (default: --version)

        Returns:
            Version string or None
        """
        try:
            result = self.run_command(
                [command, version_flag],
                capture_output=True,
                timeout=10
            )

            if result.returncode == 0:
                return result.stdout.strip()

            return None

        except:
            return None

    def kill_process_tree(self, pid: int) -> bool:
        """
        Kill a process and all its children.

        Args:
            pid: Process ID to kill

        Returns:
            True if successful
        """
        try:
            if os.name == 'nt':
                # Windows
                self.run_command(
                    ['taskkill', '/F', '/T', '/PID', str(pid)],
                    shell=True,
                    capture_output=True
                )
            else:
                # Unix-like
                import signal
                os.killpg(os.getpgid(pid), signal.SIGTERM)

            logger.info(f"Killed process tree for PID: {pid}")
            return True

        except Exception as e:
            logger.error(f"Failed to kill process tree for PID {pid}: {e}")
            return False