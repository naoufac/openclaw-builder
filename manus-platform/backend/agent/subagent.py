"""
Wide Research sub-agent spawning (M4, Manus discipline §8).

Sub-agents are **parallel full instances** of the same agent loop —
same tools, same discipline, same model. They are NOT a deliberation
or consensus mechanism. They exist for *throughput* when tasks are
independent.

Lifecycle:
    1. ``spawn_subagent(parent_session, task, ...)`` creates a child session
    2. Child gets its own workspace + Docker sandbox
    3. ``run_agent_loop`` runs in a background ``asyncio`` task
    4. Child events are forwarded to the parent's ``on_event`` callback
    5. On completion (or failure), the child sandbox is destroyed
    6. Returns a result dict with summary, todo, and workspace file listing

Recursion is limited by ``subagent_depth`` (default max 2) to prevent
runaway spawning.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, TYPE_CHECKING

from config import MAX_SUBAGENT_DEPTH, SESSION_WORKSPACE_ROOT, SUBAGENT_MAX_ITERATIONS

if TYPE_CHECKING:
    from agent.loop import AgentSession, EventCallback, EventType

log = logging.getLogger("manus.subagent")

# Global counter for child IDs within a parent session
_child_counters: dict[str, int] = {}


def _next_child_id(parent_session_id: str) -> str:
    """Generate a unique child session ID derived from the parent."""
    n = _child_counters.get(parent_session_id, 0) + 1
    _child_counters[parent_session_id] = n
    return f"{parent_session_id}-sub{n}"


async def spawn_subagent(
    parent_session_id: str,
    task: str,
    parent_on_event: Optional[EventCallback] = None,
    *,
    parent_workspace: Optional[str] = None,
    model: Optional[str] = None,
    max_iterations: int = SUBAGENT_MAX_ITERATIONS,
    subagent_depth: int = 0,
) -> dict[str, Any]:
    """
    Spawn a single sub-agent to work on an independent task.

    Creates a child session with its own workspace and Docker sandbox,
    runs the full agent loop, and returns a result dict.

    Args:
        parent_session_id: Parent session ID (for naming / event forwarding).
        task: The specific task string for the sub-agent.
        parent_on_event: Optional callback to forward child events to.
        parent_workspace: Parent workspace path (child workspace created nearby).
        model: Model override for the child.
        max_iterations: Max loop iterations for the child.
        subagent_depth: Current depth (child gets depth + 1).

    Returns:
        Dict with keys: session_id, status, result_summary, todo_markdown,
        workspace_files, error (if any).
    """
    child_id = _next_child_id(parent_session_id)
    child_depth = subagent_depth + 1

    # Lazy imports to avoid circular dependency
    from agent.loop import AgentSession, EventType, SessionStatus, run_agent_loop
    import agent.loop as loop_mod

    # Determine child workspace path
    if parent_workspace:
        child_workspace = str(Path(parent_workspace) / "subagents" / child_id)
    else:
        child_workspace = str(Path(SESSION_WORKSPACE_ROOT) / child_id)

    log.info(f"Spawning sub-agent: child_id={child_id}, parent={parent_session_id}, depth={child_depth}, task={task[:100]}")

    # Create child session (never allow deeper spawning than MAX_SUBAGENT_DEPTH)
    child_session = AgentSession(
        session_id=child_id,
        goal=task,
        workspace=child_workspace,
    )

    # Store depth as a private attribute (read by tool dispatcher)
    child_session.subagent_depth = child_depth  # type: ignore[attr-defined]

    # ── Event forwarder ──
    async def child_event_forwarder(event_type: EventType, data: dict[str, Any]) -> None:
        """Forward child events to parent, prefixed with child ID."""
        forwarded = {
            **data,
            "child_id": child_id,
            "child_depth": child_depth,
        }
        if parent_on_event:
            try:
                await parent_on_event(event_type, forwarded)
            except Exception:
                pass  # Never let event delivery break the child

    # ── Run the child agent loop ──
    # We patch MAX_ITERATIONS temporarily by passing max_iterations through
    # the session context. The loop uses the global MAX_ITERATIONS, so we
    # monkey-patch for the child run.
    original_max = loop_mod.MAX_ITERATIONS
    loop_mod.MAX_ITERATIONS = max_iterations

    try:
        await run_agent_loop(
            child_session,
            on_event=child_event_forwarder,
            model=model,
        )
    except Exception as exc:
        log.error(f"Sub-agent failed: child_id={child_id}, error={exc}")
        child_session.status = SessionStatus.FAILED
        child_session.result_summary = f"Sub-agent error: {exc}"
        # Ensure sandbox cleanup
        if child_session.sandbox is not None:
            try:
                await child_session.sandbox.destroy()
            except Exception:
                pass
    finally:
        loop_mod.MAX_ITERATIONS = original_max

    # ── Collect results ──
    workspace_files: list[str] = []
    ws_path = Path(child_workspace)
    if ws_path.exists():
        workspace_files = [
            str(f.relative_to(ws_path))
            for f in ws_path.rglob("*")
            if f.is_file()
        ]

    result: dict[str, Any] = {
        "session_id": child_id,
        "status": child_session.status.value,
        "result_summary": child_session.result_summary,
        "todo_markdown": child_session.todo_markdown,
        "workspace_files": workspace_files,
    }

    if child_session.status != SessionStatus.COMPLETED:
        result["error"] = child_session.result_summary

    return result


async def wide_research(
    parent_session_id: str,
    topics: list[str],
    parent_on_event: Optional[EventCallback] = None,
    *,
    parent_workspace: Optional[str] = None,
    model: Optional[str] = None,
    max_iterations: int = SUBAGENT_MAX_ITERATIONS,
    subagent_depth: int = 0,
) -> dict[str, Any]:
    """
    Spawn N parallel sub-agents for independent research tasks (Wide Research).

    Each sub-agent is a full instance of the agent loop with its own
    sandbox and workspace. All sub-agents run concurrently via
    ``asyncio.gather``. The parent waits for all children before returning.

    Args:
        parent_session_id: Parent session ID.
        topics: List of independent task/topic strings.
        parent_on_event: Optional callback for event forwarding.
        parent_workspace: Parent workspace path.
        model: Model override for children.
        max_iterations: Max iterations per child.
        subagent_depth: Current depth (children get depth + 1).

    Returns:
        Dict with: topics (list of per-topic results), combined_summary,
        total_children, successful, failed.
    """
    log.info(f"Wide Research starting: parent={parent_session_id}, n_topics={len(topics)}, depth={subagent_depth}")

    # Spawn all children in parallel
    tasks = [
        spawn_subagent(
            parent_session_id=parent_session_id,
            task=topic if topic.startswith("Research") else f"Research the following topic and write a brief summary to a file: {topic}",
            parent_on_event=parent_on_event,
            parent_workspace=parent_workspace,
            model=model,
            max_iterations=max_iterations,
            subagent_depth=subagent_depth,
        )
        for topic in topics
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    topic_results: list[dict[str, Any]] = []
    successful = 0
    failed = 0

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            topic_results.append({
                "topic": topics[i],
                "status": "failed",
                "error": str(result),
                "result_summary": f"Sub-agent crashed: {result}",
            })
            failed += 1
        else:
            topic_results.append({
                "topic": topics[i],
                **result,
            })
            if result.get("status") == "completed":
                successful += 1
            else:
                failed += 1

    # Build combined summary
    summaries = []
    for tr in topic_results:
        summary = tr.get("result_summary", tr.get("error", "unknown"))
        summaries.append(f"**{tr['topic']}**: {summary}")

    combined = "\n\n".join(summaries)

    return {
        "topics": topic_results,
        "combined_summary": combined,
        "total_children": len(topics),
        "successful": successful,
        "failed": failed,
    }
