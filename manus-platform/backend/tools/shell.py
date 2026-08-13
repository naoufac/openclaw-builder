"""
Shell execution tool.

Runs subprocess commands with timeout, capturing stdout and stderr.
Used by the agent loop for code execution, file system operations, etc.
"""

from __future__ import annotations

import asyncio
import shlex
from dataclasses import dataclass
from typing import Optional

from config import TOOL_TIMEOUT


@dataclass
class ShellResult:
    """Result of a shell command execution."""

    success: bool
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False

    def to_observation(self) -> str:
        """Format as an observation string for the agent context."""
        parts: list[str] = []
        if self.timed_out:
            parts.append(f"[Command timed out after {TOOL_TIMEOUT}s]")
        parts.append(f"$ exit_code={self.returncode}")
        if self.stdout.strip():
            parts.append(f"stdout:\n{self.stdout}")
        if self.stderr.strip():
            parts.append(f"stderr:\n{self.stderr}")
        return "\n".join(parts)


async def run_shell(
    command: str,
    *,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
) -> ShellResult:
    """
    Execute a shell command asynchronously.

    Args:
        command: The shell command string to execute.
        cwd: Working directory for the command.
        timeout: Override the default timeout (seconds).

    Returns:
        :class:`ShellResult` with captured output.
    """
    effective_timeout = timeout or TOOL_TIMEOUT

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=effective_timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ShellResult(
                success=False,
                stdout="",
                stderr=f"Command timed out after {effective_timeout}s",
                returncode=-1,
                timed_out=True,
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        returncode = proc.returncode if proc.returncode is not None else -1

        return ShellResult(
            success=returncode == 0,
            stdout=stdout,
            stderr=stderr,
            returncode=returncode,
        )

    except Exception as exc:
        return ShellResult(
            success=False,
            stdout="",
            stderr=f"Shell execution error: {exc}",
            returncode=-1,
        )
