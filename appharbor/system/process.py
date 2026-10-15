"""Safe process execution wrapper."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

MAX_OUTPUT_BYTES = 5 * 1024 * 1024  # 5 MB safety limit


@dataclass
class ProcessResult:
    """Bounded, structured result of a subprocess execution."""
    exit_code: int
    stdout: str
    stderr: str
    was_timeout: bool = False
    was_cancelled: bool = False

    @property
    def is_success(self) -> bool:
        return self.exit_code == 0 and not self.was_timeout and not self.was_cancelled


def is_binary_available(binary_name: str) -> bool:
    """Check if an executable exists in PATH."""
    return shutil.which(binary_name) is not None


def run_command_safely(
    args: list[str],
    timeout_seconds: float = 30.0,
    cwd: Optional[str] = None,
    env: Optional[dict[str, str]] = None,
) -> ProcessResult:
    """Execute a command safely using argument vectors with timeouts and bounded output.
    
    Security rules:
    - Never uses shell=True.
    - Validates argument list.
    - Captures and bounds output buffer to avoid memory DOS.
    - Implements timeout to prevent deadlocks.
    """
    if not args or not isinstance(args, list):
        raise ValueError("Command arguments must be a non-empty list of strings.")

    # Ensure all items in args are strings
    str_args = [str(a) for a in args]
    binary = str_args[0]

    if not is_binary_available(binary):
        return ProcessResult(
            exit_code=127,
            stdout="",
            stderr=f"Executable '{binary}' not found on system.",
        )

    # Sanitize environment, defaulting to C.UTF-8 locale for consistent parsing
    exec_env = os.environ.copy()
    exec_env["LC_ALL"] = "C.UTF-8"
    exec_env["LANG"] = "C.UTF-8"
    if env:
        exec_env.update(env)

    try:
        proc = subprocess.Popen(
            str_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            cwd=cwd,
            env=exec_env,
            text=True,
            errors="replace",
        )

        try:
            stdout_data, stderr_data = proc.communicate(timeout=timeout_seconds)
            # Bound output to avoid huge string allocations
            if len(stdout_data.encode("utf-8", "replace")) > MAX_OUTPUT_BYTES:
                stdout_data = stdout_data[: MAX_OUTPUT_BYTES // 2] + "\n... [output truncated]"
            if len(stderr_data.encode("utf-8", "replace")) > MAX_OUTPUT_BYTES:
                stderr_data = stderr_data[: MAX_OUTPUT_BYTES // 2] + "\n... [output truncated]"

            return ProcessResult(
                exit_code=proc.returncode,
                stdout=stdout_data,
                stderr=stderr_data,
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout_data, stderr_data = proc.communicate()
            logger.warning("Command %s timed out after %s seconds", str_args, timeout_seconds)
            return ProcessResult(
                exit_code=-1,
                stdout=stdout_data or "",
                stderr=(stderr_data or "") + f"\nProcess timed out after {timeout_seconds} seconds.",
                was_timeout=True,
            )

    except Exception as exc:
        logger.error("Failed to run command %s: %s", str_args, exc)
        return ProcessResult(
            exit_code=-1,
            stdout="",
            stderr=str(exc),
        )
