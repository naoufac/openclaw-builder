"""
Unit tests for sub-agent spawning and Wide Research (M4).

These tests use mocks for the LLM and sandbox to avoid burning tokens
or creating real Docker containers where possible. Integration tests
that actually spawn sub-agents are marked with @pytest.mark.integration.

Run fast tests:
    pytest test_subagent.py -v

Run integration tests (requires Docker + LLM keys):
    pytest test_subagent.py -v -m integration
"""

from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.loop import AgentSession, SessionStatus
from agent.subagent import spawn_subagent, wide_research
from config import MAX_SUBAGENT_DEPTH


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def mock_session(tmp_path):
    """Create a mock parent session."""
    return AgentSession(
        session_id="test-parent-001",
        goal="Test parent goal",
        workspace=str(tmp_path),
    )


@pytest.fixture
def mock_on_event():
    """Mock event callback."""
    return AsyncMock()


# ── Depth Limiting Tests ───────────────────────────────────────────

class TestSubagentDepthLimit:
    """Tests for sub-agent recursion depth limiting."""

    @pytest.mark.asyncio
    async def test_spawn_at_max_depth_returns_error(self, mock_session, mock_on_event):
        """spawn_subagent_tool should refuse at MAX_SUBAGENT_DEPTH."""
        from tools.subagent import spawn_subagent_tool

        mock_session.subagent_depth = MAX_SUBAGENT_DEPTH
        result = await spawn_subagent_tool(mock_session, "test task")

        assert result["success"] is False
        assert "max depth" in result["output"].lower()

    @pytest.mark.asyncio
    async def test_wide_research_at_max_depth_returns_error(self, mock_session):
        """wide_research_tool should refuse at MAX_SUBAGENT_DEPTH."""
        from tools.subagent import wide_research_tool

        mock_session.subagent_depth = MAX_SUBAGENT_DEPTH
        result = await wide_research_tool(mock_session, ["topic1", "topic2"])

        assert result["success"] is False
        assert "max depth" in result["output"].lower()

    @pytest.mark.asyncio
    async def test_wide_research_empty_topics_returns_error(self, mock_session):
        """wide_research_tool should reject empty topics list."""
        from tools.subagent import wide_research_tool

        result = await wide_research_tool(mock_session, [])
        assert result["success"] is False
        assert "non-empty" in result["output"].lower()


# ── Sub-Agent Spawning Tests (Mocked LLM) ──────────────────────────

class TestSpawnSubagent:
    """Tests for spawn_subagent with mocked LLM and sandbox."""

    @pytest.mark.asyncio
    async def test_spawn_subagent_creates_child_session(self, mock_session, mock_on_event):
        """spawn_subagent should create a child session with derived ID."""
        with patch("agent.loop.run_agent_loop") as mock_loop, \
             patch("agent.loop.SandboxManager"):
            # Make the mock loop set the session status to completed
            async def fake_loop(session, **kwargs):
                session.status = SessionStatus.COMPLETED
                session.result_summary = "Child completed"
                session.todo_markdown = "## Todo\n1. [✓] Done\n"

            mock_loop.side_effect = fake_loop

            result = await spawn_subagent(
                parent_session_id=mock_session.session_id,
                task="Test sub-task",
                parent_on_event=mock_on_event,
                parent_workspace=mock_session.workspace,
                subagent_depth=0,
            )

        assert result["session_id"].startswith("test-parent-001-sub")
        assert result["status"] == "completed"
        assert result["result_summary"] == "Child completed"

    @pytest.mark.asyncio
    async def test_spawn_subagent_increments_depth(self, mock_session, mock_on_event):
        """Child session should have depth = parent_depth + 1."""
        captured_depth = None

        with patch("agent.loop.run_agent_loop") as mock_loop, \
             patch("agent.loop.SandboxManager"):
            async def fake_loop(session, **kwargs):
                nonlocal captured_depth
                captured_depth = session.subagent_depth
                session.status = SessionStatus.COMPLETED
                session.result_summary = "Done"

            mock_loop.side_effect = fake_loop

            await spawn_subagent(
                parent_session_id=mock_session.session_id,
                task="Depth test",
                parent_on_event=mock_on_event,
                parent_workspace=mock_session.workspace,
                subagent_depth=1,  # Parent is at depth 1
            )

        assert captured_depth == 2

    @pytest.mark.asyncio
    async def test_spawn_subagent_creates_workspace(self, mock_session, mock_on_event):
        """spawn_subagent should create a child workspace directory."""
        import tempfile

        with patch("agent.loop.run_agent_loop") as mock_loop, \
             patch("agent.loop.SandboxManager"):
            async def fake_loop(session, **kwargs):
                session.status = SessionStatus.COMPLETED
                session.result_summary = "Done"
                # Simulate writing a file
                from pathlib import Path
                ws = Path(session.workspace)
                ws.mkdir(parents=True, exist_ok=True)
                (ws / "result.txt").write_text("research result")

            mock_loop.side_effect = fake_loop

            result = await spawn_subagent(
                parent_session_id=mock_session.session_id,
                task="Write a file",
                parent_on_event=mock_on_event,
                parent_workspace=mock_session.workspace,
                subagent_depth=0,
            )

        assert "result.txt" in result["workspace_files"]

    @pytest.mark.asyncio
    async def test_spawn_subagent_handles_failure(self, mock_session, mock_on_event):
        """spawn_subagent should handle child failure gracefully."""
        with patch("agent.loop.run_agent_loop") as mock_loop, \
             patch("agent.loop.SandboxManager"):
            async def fake_loop(session, **kwargs):
                session.status = SessionStatus.FAILED
                session.result_summary = "Child failed: could not complete"

            mock_loop.side_effect = fake_loop

            result = await spawn_subagent(
                parent_session_id=mock_session.session_id,
                task="Impossible task",
                parent_on_event=mock_on_event,
                parent_workspace=mock_session.workspace,
                subagent_depth=0,
            )

        assert result["status"] == "failed"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_spawn_subagent_handles_exception(self, mock_session, mock_on_event):
        """spawn_subagent should handle exceptions from run_agent_loop."""
        with patch("agent.loop.run_agent_loop") as mock_loop, \
             patch("agent.loop.SandboxManager"):
            async def fake_loop(session, **kwargs):
                raise RuntimeError("Boom!")

            mock_loop.side_effect = fake_loop

            result = await spawn_subagent(
                parent_session_id=mock_session.session_id,
                task="Crash test",
                parent_on_event=mock_on_event,
                parent_workspace=mock_session.workspace,
                subagent_depth=0,
            )

        assert result["status"] == "failed"
        assert "Boom" in result.get("error", "") or "Boom" in result.get("result_summary", "")

    @pytest.mark.asyncio
    async def test_child_events_forwarded_to_parent(self, mock_session, mock_on_event):
        """Child events should be forwarded to parent callback with child_id."""
        from agent.loop import EventType

        with patch("agent.loop.run_agent_loop") as mock_loop, \
             patch("agent.loop.SandboxManager"):
            async def fake_loop(session, *, on_event=None, **kwargs):
                session.status = SessionStatus.COMPLETED
                session.result_summary = "Done"
                if on_event:
                    await on_event(EventType.THOUGHT, {"content": "child thinking"})

            mock_loop.side_effect = fake_loop

            await spawn_subagent(
                parent_session_id=mock_session.session_id,
                task="Event forwarding test",
                parent_on_event=mock_on_event,
                parent_workspace=mock_session.workspace,
                subagent_depth=0,
            )

        # Parent callback should have been called with forwarded event
        mock_on_event.assert_called()
        call_args = mock_on_event.call_args
        event_type, data = call_args.args[0], call_args.args[1]
        assert "child_id" in data
        assert data["child_id"].startswith("test-parent-001-sub")


# ── Wide Research Tests (Mocked LLM) ───────────────────────────────

class TestWideResearch:
    """Tests for wide_research parallel spawning."""

    @pytest.mark.asyncio
    async def test_wide_research_spawns_n_parallel_children(self, mock_session, mock_on_event):
        """wide_research should spawn one child per topic, in parallel."""
        spawn_count = 0
        spawn_order: list[float] = []

        with patch("agent.loop.run_agent_loop") as mock_loop, \
             patch("agent.loop.SandboxManager"):
            async def fake_loop(session, *, on_event=None, **kwargs):
                nonlocal spawn_count
                spawn_count += 1
                spawn_order.append(asyncio.get_event_loop().time())
                # Simulate some work
                await asyncio.sleep(0.05)
                session.status = SessionStatus.COMPLETED
                session.result_summary = f"Researched: {session.goal}"

            mock_loop.side_effect = fake_loop

            result = await wide_research(
                parent_session_id=mock_session.session_id,
                topics=["python", "docker", "fastapi"],
                parent_on_event=mock_on_event,
                parent_workspace=mock_session.workspace,
                subagent_depth=0,
            )

        assert spawn_count == 3
        assert result["total_children"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_wide_research_combines_results(self, mock_session, mock_on_event):
        """wide_research should combine results from all children."""
        with patch("agent.loop.run_agent_loop") as mock_loop, \
             patch("agent.loop.SandboxManager"):
            async def fake_loop(session, *, on_event=None, **kwargs):
                session.status = SessionStatus.COMPLETED
                session.result_summary = f"Summary for {session.goal}"

            mock_loop.side_effect = fake_loop

            result = await wide_research(
                parent_session_id=mock_session.session_id,
                topics=["topic_a", "topic_b"],
                parent_on_event=mock_on_event,
                parent_workspace=mock_session.workspace,
                subagent_depth=0,
            )

        assert "topic_a" in result["combined_summary"]
        assert "topic_b" in result["combined_summary"]

    @pytest.mark.asyncio
    async def test_wide_research_partial_failure(self, mock_session, mock_on_event):
        """wide_research should handle partial failures."""
        call_count = 0

        with patch("agent.loop.run_agent_loop") as mock_loop, \
             patch("agent.loop.SandboxManager"):
            async def fake_loop(session, *, on_event=None, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise RuntimeError("Second child crashes")
                session.status = SessionStatus.COMPLETED
                session.result_summary = "OK"

            mock_loop.side_effect = fake_loop

            result = await wide_research(
                parent_session_id=mock_session.session_id,
                topics=["good1", "bad", "good2"],
                parent_on_event=mock_on_event,
                parent_workspace=mock_session.workspace,
                subagent_depth=0,
            )

        assert result["total_children"] == 3
        assert result["successful"] == 2
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_wide_research_children_run_concurrently(self, mock_session, mock_on_event):
        """Verify children actually run in parallel (not sequentially)."""
        start_times: list[float] = []

        with patch("agent.loop.run_agent_loop") as mock_loop, \
             patch("agent.loop.SandboxManager"):
            async def fake_loop(session, *, on_event=None, **kwargs):
                start_times.append(asyncio.get_event_loop().time())
                await asyncio.sleep(0.2)  # Each takes 200ms
                session.status = SessionStatus.COMPLETED
                session.result_summary = "Done"

            mock_loop.side_effect = fake_loop

            import time
            t0 = time.monotonic()
            await wide_research(
                parent_session_id=mock_session.session_id,
                topics=["a", "b", "c"],
                parent_on_event=mock_on_event,
                parent_workspace=mock_session.workspace,
                subagent_depth=0,
            )
            elapsed = time.monotonic() - t0

        # If truly parallel, total time should be < sum of individual times
        # 3 tasks × 0.2s sequential = 0.6s; parallel should be ~0.2s
        assert elapsed < 0.5, f"Expected parallel execution < 0.5s, got {elapsed:.2f}s"


# ── Tool Wrapper Tests ─────────────────────────────────────────────

class TestSubagentToolWrapper:
    """Tests for the tool interface wrappers."""

    @pytest.mark.asyncio
    async def test_spawn_subagent_tool_success(self, mock_session):
        """spawn_subagent_tool should return formatted result on success."""
        from tools.subagent import spawn_subagent_tool

        with patch("tools.subagent.spawn_subagent") as mock_spawn:
            mock_spawn.return_value = {
                "session_id": "child-001",
                "status": "completed",
                "result_summary": "Task done",
                "todo_markdown": "## Todo\n1. [✓] Done",
                "workspace_files": ["result.txt"],
            }

            result = await spawn_subagent_tool(mock_session, "test task")

        assert result["success"] is True
        assert "child-001" in result["output"]
        assert "result.txt" in result["output"]

    @pytest.mark.asyncio
    async def test_spawn_subagent_tool_no_task(self, mock_session):
        """spawn_subagent_tool should reject empty task."""
        from tools.subagent import spawn_subagent_tool

        result = await spawn_subagent_tool(mock_session, "")

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_wide_research_tool_success(self, mock_session):
        """wide_research_tool should return combined summary."""
        from tools.subagent import wide_research_tool

        with patch("tools.subagent.wide_research") as mock_wr:
            mock_wr.return_value = {
                "topics": [
                    {"topic": "a", "status": "completed", "result_summary": "A done"},
                    {"topic": "b", "status": "completed", "result_summary": "B done"},
                ],
                "combined_summary": "A done\n\nB done",
                "total_children": 2,
                "successful": 2,
                "failed": 0,
            }

            result = await wide_research_tool(mock_session, ["a", "b"])

        assert result["success"] is True
        assert "2/2" in result["output"]


# ── Integration Tests (require Docker + LLM) ───────────────────────

class TestSubagentIntegration:
    """Integration tests that actually spawn sub-agents."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_spawn_subagent(self, tmp_path):
        """Spawn a real sub-agent with a trivial task."""
        session = AgentSession(
            session_id="integration-001",
            goal="Write 'hello' to a file",
            workspace=str(tmp_path),
        )

        result = await spawn_subagent(
            parent_session_id="integration-parent",
            task="Write 'hello world' to a file called greeting.txt",
            parent_on_event=None,
            parent_workspace=str(tmp_path),
            subagent_depth=0,
        )

        assert result["status"] in ("completed", "failed")
        # Workspace should exist
        assert len(result["workspace_files"]) > 0 or result.get("error")


# ── Entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
