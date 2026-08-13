"""
Docker sandbox lifecycle manager (M2).

Each agent session gets an isolated Docker container.  Tools execute
inside the container, not on the host filesystem.

The session workspace (a host directory) is bind-mounted into the
container at ``/workspace``, so files written from the host side are
immediately visible inside the sandbox and vice-versa.

Lifecycle:
    1. ``SandboxManager(session_id, workspace_host)`` — construct
    2. ``await manager.create()``  — start container
    3. ``await manager.exec(cmd)`` — run command inside container
    4. ``await manager.destroy()`` — stop + remove container
"""

from __future__ import annotations

import logging
import shlex
from dataclasses import dataclass
from typing import Optional

import docker
from docker.errors import APIError, ImageNotFound, NotFound
from docker.models.containers import Container

from config import SANDBOX_IMAGE, SANDBOX_TIMEOUT, SANDBOX_WORKSPACE, TOOL_TIMEOUT

log = logging.getLogger(__name__)


# ── Result type ────────────────────────────────────────────────────

@dataclass
class SandboxExecResult:
    """Result of a command executed inside the sandbox."""

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


# ── Manager ────────────────────────────────────────────────────────

class SandboxManager:
    """
    Manage a single Docker sandbox container per agent session.

    Args:
        session_id: Unique session identifier (used in container name).
        workspace_host: Absolute host path to the session workspace
                        (will be bind-mounted into the container).
        image: Docker image to use (default from config).
    """

    def __init__(
        self,
        session_id: str,
        workspace_host: str,
        *,
        image: str = SANDBOX_IMAGE,
    ) -> None:
        self.session_id = session_id
        self.workspace_host = workspace_host
        self.image = image
        self.container_name = f"manus-sandbox-{session_id}"
        self._container: Optional[Container] = None
        self._client: Optional[docker.DockerClient] = None

    # ── Lazy Docker client ──

    @property
    def client(self) -> docker.DockerClient:
        """Lazily create a Docker client (singleton per manager)."""
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    # ── Lifecycle ──

    async def create(self) -> str:
        """
        Start the sandbox container.

        - Ensures the image exists (builds from Dockerfile if missing).
        - Bind-mounts *workspace_host* → ``/workspace`` in the container.
        - Keeps the container running with ``sleep infinity``.

        Returns:
            The container name.

        Raises:
            RuntimeError: If the container cannot be started.
        """
        try:
            # Ensure image exists
            await self._ensure_image()

            # Remove stale container if it exists
            try:
                old = self.client.containers.get(self.container_name)
                log.warning("Found stale sandbox container, removing", name=self.container_name)
                old.remove(force=True)
            except NotFound:
                pass

            # Ensure workspace is world-writable (sandbox runs as non-root 'agent' user)
            os.chmod(self.workspace_host, 0o777)

            log.info(
                "Creating sandbox container",
                name=self.container_name,
                image=self.image,
                workspace=self.workspace_host,
            )

            self._container = self.client.containers.run(
                image=self.image,
                name=self.container_name,
                command=["sleep", "infinity"],
                detach=True,
                volumes={
                    self.workspace_host: {"bind": SANDBOX_WORKSPACE, "mode": "rw"},
                },
                working_dir=SANDBOX_WORKSPACE,
                auto_remove=False,
                network_mode="bridge",
            )

            log.info("Sandbox container started", name=self.container_name, id=self._container.short_id)
            return self.container_name

        except Exception as exc:
            raise RuntimeError(f"Failed to create sandbox container: {exc}") from exc

    async def _ensure_image(self) -> None:
        """Ensure the sandbox image exists locally; build if missing."""
        try:
            self.client.images.get(self.image)
        except ImageNotFound:
            log.info("Sandbox image not found, attempting build", image=self.image)
            # Try to build from the known Dockerfile location
            import os
            possible_contexts = [
                "/app/docker/sandbox",       # inside backend container
                "../docker/sandbox",          # relative to backend dir
                "manus-platform/docker/sandbox",
            ]
            for ctx in possible_contexts:
                dockerfile_path = os.path.join(ctx, "Dockerfile")
                if os.path.isfile(dockerfile_path):
                    log.info("Building sandbox image", context=ctx)
                    image, build_logs = self.client.images.build(
                        path=ctx,
                        dockerfile="Dockerfile",
                        tag=self.image,
                    )
                    log.info("Sandbox image built", id=image.short_id)
                    return
            # If no Dockerfile found, pull from registry
            log.info("No Dockerfile found, pulling image", image=self.image)
            self.client.images.pull(self.image)

    # ── Command execution ──

    async def exec(
        self,
        command: str,
        *,
        timeout: int = TOOL_TIMEOUT,
        cwd: Optional[str] = None,
    ) -> SandboxExecResult:
        """
        Execute a shell command inside the sandbox container.

        Args:
            command: Shell command string.
            timeout: Maximum execution time (seconds).
            cwd: Working directory inside the container
                 (defaults to ``/workspace``).

        Returns:
            :class:`SandboxExecResult` with captured output.
        """
        if self._container is None:
            return SandboxExecResult(
                success=False,
                stdout="",
                stderr="Sandbox container not created. Call create() first.",
                returncode=-1,
            )

        work_dir = cwd or SANDBOX_WORKSPACE

        try:
            # Use docker exec to run the command
            exec_handle = self.client.api.exec_create(
                self._container.id,
                cmd=["sh", "-c", command],
                workdir=work_dir,
            )

            exec_output = self.client.api.exec_start(
                exec_handle["Id"],
                demux=True,
            )

            # exec_start returns (stdout_bytes, stderr_bytes) when demux=True
            if isinstance(exec_output, tuple):
                stdout_bytes, stderr_bytes = exec_output
            else:
                stdout_bytes = exec_output
                stderr_bytes = b""

            # Get exit code
            exec_inspect = self.client.api.exec_inspect(exec_handle["Id"])
            returncode = exec_inspect.get("ExitCode", -1)

            stdout = (stdout_bytes or b"").decode("utf-8", errors="replace")
            stderr = (stderr_bytes or b"").decode("utf-8", errors="replace")

            return SandboxExecResult(
                success=returncode == 0,
                stdout=stdout,
                stderr=stderr,
                returncode=returncode if returncode is not None else -1,
            )

        except Exception as exc:
            log.error("Sandbox exec failed", error=str(exc), command=command[:200])
            return SandboxExecResult(
                success=False,
                stdout="",
                stderr=f"Sandbox exec error: {exc}",
                returncode=-1,
            )

    # ── File operations ──

    async def read_file(self, path: str) -> str:
        """
        Read a file from inside the sandbox container.

        Args:
            path: Absolute path or path relative to /workspace.

        Returns:
            File contents as a string.

        Raises:
            RuntimeError: If the read fails.
        """
        full_path = path if path.startswith("/") else f"{SANDBOX_WORKSPACE}/{path}"
        result = await self.exec(f"cat {shlex.quote(full_path)}")
        if not result.success:
            raise RuntimeError(f"Failed to read {full_path}: {result.stderr}")
        return result.stdout

    async def write_file(self, path: str, content: str) -> None:
        """
        Write a file inside the sandbox container.

        Args:
            path: Absolute path or path relative to /workspace.
            content: Text content to write.

        Raises:
            RuntimeError: If the write fails.
        """
        full_path = path if path.startswith("/") else f"{SANDBOX_WORKSPACE}/{path}"
        # Use a heredoc to safely write content
        # Escape any existing heredoc markers
        marker = "MANUS_EOF_MARKER"
        while marker in content:
            marker += "_X"

        command = f"mkdir -p {shlex.quote(os.path.dirname(full_path))} && cat > {shlex.quote(full_path)} <<'{marker}'\n{content}\n{marker}"

        result = await self.exec(command)
        if not result.success:
            raise RuntimeError(f"Failed to write {full_path}: {result.stderr}")

    # ── Teardown ──

    async def destroy(self) -> None:
        """
        Stop and remove the sandbox container.

        Safe to call multiple times — ignores errors if container
        is already gone.
        """
        # Try via tracked container object first
        if self._container is not None:
            try:
                self._container.stop(timeout=5)
            except Exception:
                pass  # May already be stopped
            try:
                self._container.remove(force=True)
            except Exception:
                pass
            self._container = None
            return

        # Fallback: lookup by name
        try:
            container = self.client.containers.get(self.container_name)
            container.stop(timeout=5)
            container.remove(force=True)
        except NotFound:
            pass  # Already gone — fine
        except Exception as exc:
            log.warning("Error destroying sandbox", name=self.container_name, error=str(exc))

        self._container = None

    # ── Status ──

    @property
    def is_running(self) -> bool:
        """Check if the sandbox container is currently running."""
        if self._container is None:
            return False
        try:
            self._container.reload()
            return self._container.status == "running"
        except Exception:
            return False

    # ── Context manager support ──

    async def __aenter__(self) -> "SandboxManager":
        await self.create()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.destroy()


# Late import for write_file
import os
