"""
Shell execution tool.

Runs commands either inside a Docker sandbox (when a SandboxManager is
provided) or directly on the host via subprocess (fallback / testing).

Used by the agent loop for code execution, file system operations, etc.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from config import TOOL_TIMEOUT

if TYPE_CHECKING:
    from sandbox.manager import SandboxManager

log = logging.getLogger(__name__)


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
        parts.append(f"exit_code={self.returncode}")
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
    sandbox: Optional["SandboxManager"] = None,
) -> ShellResult:
    """
    Execute a shell command.

    If a *sandbox* manager is provided, the command runs inside the
    sandbox Docker container.  Otherwise it runs directly on the host
    via ``asyncio.create_subprocess_shell`` (for testing / local dev).

    Args:
        command: The shell command string to execute.
        cwd: Working directory for the command.
        timeout: Override the default timeout (seconds).
        sandbox: Optional :class:`SandboxManager` for container execution.

    Returns:
        :class:`ShellResult` with captured output.
    """
    if sandbox is not None:
        return await _run_in_sandbox(command, cwd=cwd, timeout=timeout, sandbox=sandbox)
    return await _run_on_host(command, cwd=cwd, timeout=timeout)


# ── Sandbox execution ──

async def _run_in_sandbox(
    command: str,
    *,
    cwd: Optional[str],
    timeout: Optional[int],
    sandbox: "SandboxManager",
) -> ShellResult:
    """Execute inside a Docker sandbox container."""
    effective_timeout = timeout or TOOL_TIMEOUT

    try:
        result = await sandbox.exec(command, timeout=effective_timeout, cwd=cwd)
        return ShellResult(
            success=result.success,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            timed_out=result.timed_out,
        )
    except Exception as exc:
        log.error("Sandbox shell execution error", error=str(exc))
        return ShellResult(
            success=False,
            stdout="",
            stderr=f"Sandbox execution error: {exc}",
            returncode=-1,
        )


# ── Host execution (fallback) ──

async def _run_on_host(
    command: str,
    *,
    cwd: Optional[str],
    timeout: Optional[int],
) -> ShellResult:
    """Execute directly on the host (no sandbox)."""
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
