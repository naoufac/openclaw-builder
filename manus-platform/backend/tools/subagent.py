"""
Sub-agent tool interface.

Wraps the subagent spawning logic as a tool that the agent loop
can dispatch. Returns a formatted result string for the parent
agent's context.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, TYPE_CHECKING

from agent.subagent import spawn_subagent, wide_research
from config import MAX_SUBAGENT_DEPTH

if TYPE_CHECKING:
    from agent.loop import AgentSession, EventCallback

log = logging.getLogger(__name__)


async def spawn_subagent_tool(
    parent_session: "AgentSession",
    task: str,
    *,
    model: Optional[str] = None,
    max_iterations: int = 5,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Tool wrapper for spawning a single sub-agent.

    Checks depth limit, spawns the sub-agent, and returns a formatted
    observation for the parent agent's context.

    Args:
        parent_session: The parent agent session.
        task: The task for the sub-agent.
        model: Optional model override.
        max_iterations: Max iterations for the child.

    Returns:
        Dict with success, output, and tool keys (standard tool result format).
    """
    depth = getattr(parent_session, "subagent_depth", 0)

    if not task or not task.strip():
        return {
            "success": False,
            "output": "[spawn_subagent rejected: no task provided]",
            "tool": "spawn_subagent",
        }

    if depth >= MAX_SUBAGENT_DEPTH:
        return {
            "success": False,
            "output": (
                f"[spawn_subagent rejected: max depth ({MAX_SUBAGENT_DEPTH}) reached. "
                f"Current depth: {depth}. Sub-agents cannot spawn further sub-agents.]"
            ),
            "tool": "spawn_subagent",
        }

    try:
        result = await spawn_subagent(
            parent_session_id=parent_session.session_id,
            task=task,
            parent_on_event=None,  # Events will be forwarded by the loop
            parent_workspace=parent_session.workspace,
            model=model,
            max_iterations=max_iterations,
            subagent_depth=depth,
        )

        # Format result as observation
        status = result.get("status", "unknown")
        summary = result.get("result_summary", "")
        child_id = result.get("session_id", "?")
        files = result.get("workspace_files", [])
        error = result.get("error")

        parts = [
            f"[Sub-agent '{child_id}' finished with status: {status}]",
            f"Summary: {summary}",
        ]
        if files:
            parts.append(f"Files created: {', '.join(files[:10])}")
        if error:
            parts.append(f"Error: {error}")

        return {
            "success": status == "completed",
            "output": "\n".join(parts),
            "tool": "spawn_subagent",
        }

    except Exception as exc:
        log.error("spawn_subagent_tool failed", error=str(exc))
        return {
            "success": False,
            "output": f"[spawn_subagent failed: {exc}]",
            "tool": "spawn_subagent",
        }


async def wide_research_tool(
    parent_session: "AgentSession",
    topics: list[str],
    *,
    model: Optional[str] = None,
    max_iterations: int = 5,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Tool wrapper for Wide Research — spawns N parallel sub-agents.

    Args:
        parent_session: The parent agent session.
        topics: List of independent research topics.
        model: Optional model override.
        max_iterations: Max iterations per child.

    Returns:
        Dict with success, output, and tool keys (standard tool result format).
    """
    depth = getattr(parent_session, "subagent_depth", 0)

    if depth >= MAX_SUBAGENT_DEPTH:
        return {
            "success": False,
            "output": (
                f"[wide_research rejected: max depth ({MAX_SUBAGENT_DEPTH}) reached. "
                f"Current depth: {depth}.]"
            ),
            "tool": "wide_research",
        }

    if not topics or not isinstance(topics, list):
        return {
            "success": False,
            "output": "[wide_research requires a non-empty 'topics' list]",
            "tool": "wide_research",
        }

    try:
        result = await wide_research(
            parent_session_id=parent_session.session_id,
            topics=topics,
            parent_on_event=None,
            parent_workspace=parent_session.workspace,
            model=model,
            max_iterations=max_iterations,
            subagent_depth=depth,
        )

        # Format combined result
        total = result["total_children"]
        ok = result["successful"]
        fail = result["failed"]
        combined = result["combined_summary"]

        output = (
            f"[Wide Research complete: {ok}/{total} succeeded, {fail} failed]\n\n"
            f"{combined}"
        )

        return {
            "success": fail == 0,
            "output": output,
            "tool": "wide_research",
        }

    except Exception as exc:
        log.error("wide_research_tool failed", error=str(exc))
        return {
            "success": False,
            "output": f"[wide_research failed: {exc}]",
            "tool": "wide_research",
        }
