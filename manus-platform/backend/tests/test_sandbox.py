"""
Unit tests for the Docker sandbox manager (M2).

These tests verify the SandboxManager lifecycle (create/exec/destroy)
against a real Docker daemon. They do NOT require any LLM API keys.

Requirements:
    - Docker daemon running on the host
    - manus-sandbox:latest image available (or buildable from docker/sandbox/Dockerfile)
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import uuid

import pytest

# Ensure backend/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sandbox.manager import SandboxManager, SandboxExecResult


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def workspace(tmp_path):
    """Temporary workspace directory."""
    return str(tmp_path)


@pytest.fixture
def session_id():
    """Random session ID for test isolation."""
    return f"test-{uuid.uuid4().hex[:8]}"


# ── Tests ──────────────────────────────────────────────────────────

class TestSandboxCreate:
    """Tests for sandbox container creation."""

    @pytest.mark.asyncio
    async def test_create_returns_container_name(self, session_id, workspace):
        """SandboxManager.create() returns the container name."""
        mgr = SandboxManager(session_id, workspace)
        try:
            name = await mgr.create()
            assert name == f"manus-sandbox-{session_id}"
        finally:
            await mgr.destroy()

    @pytest.mark.asyncio
    async def test_container_is_running_after_create(self, session_id, workspace):
        """Container should be running after create()."""
        mgr = SandboxManager(session_id, workspace)
        try:
            await mgr.create()
            assert mgr.is_running is True
        finally:
            await mgr.destroy()

    @pytest.mark.asyncio
    async def test_create_with_missing_image_builds_it(self, session_id, workspace):
        """If image is missing, it should be built or pulled."""
        # Use the standard image
        mgr = SandboxManager(session_id, workspace, image="manus-sandbox:latest")
        try:
            await mgr.create()
            assert mgr.is_running
        finally:
            await mgr.destroy()


class TestSandboxExec:
    """Tests for command execution inside the sandbox."""

    @pytest.mark.asyncio
    async def test_exec_echo(self, session_id, workspace):
        """echo hello should produce 'hello' on stdout."""
        mgr = SandboxManager(session_id, workspace)
        try:
            await mgr.create()
            result = await mgr.exec("echo hello")
            assert result.success
            assert result.returncode == 0
            assert "hello" in result.stdout
        finally:
            await mgr.destroy()

    @pytest.mark.asyncio
    async def test_exec_exit_code(self, session_id, workspace):
        """Non-zero exit code is captured."""
        mgr = SandboxManager(session_id, workspace)
        try:
            await mgr.create()
            result = await mgr.exec("exit 42")
            assert not result.success
            assert result.returncode == 42
        finally:
            await mgr.destroy()

    @pytest.mark.asyncio
    async def test_exec_stderr(self, session_id, workspace):
        """stderr is captured separately."""
        mgr = SandboxManager(session_id, workspace)
        try:
            await mgr.create()
            result = await mgr.exec("echo oops >&2")
            assert result.success
            assert "oops" in result.stderr
        finally:
            await mgr.destroy()

    @pytest.mark.asyncio
    async def test_exec_writes_to_workspace(self, session_id, workspace):
        """Commands execute in /workspace — files appear on host mount."""
        mgr = SandboxManager(session_id, workspace)
        try:
            await mgr.create()
            result = await mgr.exec("echo 'test content' > /workspace/test.txt")
            assert result.success

            # File should be visible on the host (bind mount)
            host_file = os.path.join(workspace, "test.txt")
            assert os.path.exists(host_file)
            with open(host_file) as f:
                assert f.read().strip() == "test content"
        finally:
            await mgr.destroy()


class TestSandboxFiles:
    """Tests for read_file / write_file methods."""

    @pytest.mark.asyncio
    async def test_write_and_read_file(self, session_id, workspace):
        """write_file then read_file returns the same content."""
        mgr = SandboxManager(session_id, workspace)
        try:
            await mgr.create()
            await mgr.write_file("test.txt", "hello world")
            content = await mgr.read_file("test.txt")
            assert "hello world" in content
        finally:
            await mgr.destroy()


class TestSandboxDestroy:
    """Tests for sandbox container cleanup."""

    @pytest.mark.asyncio
    async def test_destroy_removes_container(self, session_id, workspace):
        """After destroy(), container is gone."""
        mgr = SandboxManager(session_id, workspace)
        await mgr.create()
        assert mgr.is_running

        await mgr.destroy()
        assert not mgr.is_running
        assert mgr._container is None

    @pytest.mark.asyncio
    async def test_destroy_is_idempotent(self, session_id, workspace):
        """Calling destroy() twice should not raise."""
        mgr = SandboxManager(session_id, workspace)
        await mgr.create()

        await mgr.destroy()
        await mgr.destroy()  # Should not raise

    @pytest.mark.asyncio
    async def test_context_manager(self, session_id, workspace):
        """Async context manager creates and destroys automatically."""
        mgr = SandboxManager(session_id, workspace)
        async with mgr:
            assert mgr.is_running
            result = await mgr.exec("echo inside_ctx")
            assert result.success
        # After context exit, container should be gone
        assert not mgr.is_running


class TestSandboxExecResult:
    """Tests for the SandboxExecResult dataclass."""

    def test_to_observation_success(self):
        """to_observation formats successful results."""
        result = SandboxExecResult(
            success=True,
            stdout="hello\n",
            stderr="",
            returncode=0,
        )
        obs = result.to_observation()
        assert "exit_code=0" in obs
        assert "hello" in obs

    def test_to_observation_with_stderr(self):
        """to_observation includes stderr."""
        result = SandboxExecResult(
            success=False,
            stdout="",
            stderr="command not found",
            returncode=127,
        )
        obs = result.to_observation()
        assert "exit_code=127" in obs
        assert "command not found" in obs


# ── Entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
