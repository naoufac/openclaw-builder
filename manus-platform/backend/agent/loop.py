"""
THE CORE AGENT LOOP (Manus discipline §1).

Single loop. No multi-agent consensus. No voting.

Each iteration:
    1. Read todo.md (recency bias mitigation, §4)
    2. Build context (frozen prefix + append-only working area, §7)
    3. Call LLM → get next tool call
    4. Execute tool → get observation
    5. Update todo.md (mark complete/failed/in-progress)
    6. Emit events (for WebSocket streaming)
    7. Repeat until all steps complete or finish tool is called

Failures stay in context (§5). The file system is long-term memory (§6).
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import logging

log = logging.getLogger(__name__)

from agent.context import AgentContext
from agent.todo import (
    StepStatus,
    TodoState,
    mark_completed,
    mark_failed,
    mark_in_progress,
    parse_todo,
    render_initial_todo,
)
from config import MAX_ITERATIONS, SESSION_WORKSPACE_ROOT
from models.router import ChatMessage, chat_completion, stream_chat_completion
from tools.files import file_list, file_read, file_write
from tools.shell import run_shell
from tools.web import web_fetch


# ── Event types ────────────────────────────────────────────────────

class EventType(str, Enum):
    """Events streamed to WebSocket clients."""

    THOUGHT = "thought"            # Agent reasoning
    TODO_UPDATE = "todo_update"    # todo.md changed
    TOOL_CALL = "tool_call"        # Agent is calling a tool
    TOOL_RESULT = "tool_result"    # Tool finished
    COMPLETE = "complete"          # Session finished
    ERROR = "error"                # Unrecoverable error
    ITERATION = "iteration"        # Iteration counter


# Event callback type
EventCallback = Callable[[EventType, dict[str, Any]], Awaitable[None]]


# ── Session state ──────────────────────────────────────────────────

class SessionStatus(str, Enum):
    """Status of an agent session."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentSession:
    """A single agent session."""

    session_id: str
    goal: str
    workspace: str
    status: SessionStatus = SessionStatus.CREATED
    todo_markdown: str = ""
    context: Optional[AgentContext] = None
    iteration: int = 0
    result_summary: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    events: list[dict[str, Any]] = field(default_factory=list)


# ── Tool call parsing ──────────────────────────────────────────────

_TOOL_CALL_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
_TOOL_CALL_RE_FALLBACK = re.compile(r"(\{[^{}]*\"tool\"[^{}]*\})", re.DOTALL)


def parse_tool_call(llm_output: str) -> Optional[dict[str, Any]]:
    """
    Extract a JSON tool call from the LLM output.

    Handles:
    - ```json { ... } ``` blocks
    - Bare { "tool": ... } JSON
    - First JSON object on a line

    Returns:
        Parsed tool call dict, or None if no valid tool call found.
    """
    # Try fenced code block first
    match = _TOOL_CALL_RE.search(llm_output)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try bare JSON object with "tool" key
    match = _TOOL_CALL_RE_FALLBACK.search(llm_output)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try line-by-line
    for line in llm_output.strip().splitlines():
        line = line.strip()
        if line.startswith("{") and '"tool"' in line:
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

    return None


# ── Tool execution ─────────────────────────────────────────────────

async def execute_tool(
    tool_call: dict[str, Any],
    workspace: str,
) -> dict[str, Any]:
    """
    Execute a parsed tool call and return the observation.

    Args:
        tool_call: Dict with "tool" and "args" keys.
        workspace: Absolute path to the session workspace.

    Returns:
        Dict with "success", "output", and "tool" keys.
    """
    tool_name = tool_call.get("tool", "")
    args = tool_call.get("args", {})

    if tool_name == "shell":
        command = args.get("command", "")
        if not command:
            return {"success": False, "output": "No command provided", "tool": "shell"}
        result = await run_shell(command, cwd=workspace)
        return {
            "success": result.success,
            "output": result.to_observation(),
            "tool": "shell",
        }

    elif tool_name == "file_write":
        path = args.get("path", "")
        content = args.get("content", "")
        if not path:
            return {"success": False, "output": "No path provided", "tool": "file_write"}
        result = await file_write(workspace, path, content)
        return {
            "success": result.success,
            "output": result.to_observation(),
            "tool": "file_write",
        }

    elif tool_name == "file_read":
        path = args.get("path", "")
        if not path:
            return {"success": False, "output": "No path provided", "tool": "file_read"}
        result = await file_read(workspace, path)
        return {
            "success": result.success,
            "output": result.to_observation(),
            "tool": "file_read",
        }

    elif tool_name == "file_list":
        path = args.get("path", ".")
        result = await file_list(workspace, path)
        return {
            "success": result.success,
            "output": result.to_observation(),
            "tool": "file_list",
        }

    elif tool_name == "web_fetch":
        url = args.get("url", "")
        if not url:
            return {"success": False, "output": "No URL provided", "tool": "web_fetch"}
        result = await web_fetch(url)
        return {
            "success": result.success,
            "output": result.to_observation(),
            "tool": "web_fetch",
        }

    elif tool_name == "finish":
        return {
            "success": True,
            "output": "__FINISH__",
            "tool": "finish",
            "summary": args.get("summary", "Task completed"),
        }

    else:
        return {
            "success": False,
            "output": f"Unknown tool: {tool_name}",
            "tool": tool_name,
        }


# ── Initial todo generation ────────────────────────────────────────

async def generate_initial_todo(goal: str) -> str:
    """
    Ask the LLM to generate a todo.md plan from the goal.

    Falls back to a simple 3-step plan if the LLM is unavailable.
    """
    from agent.todo import SYSTEM_PROMPT_FOR_TODO

    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT_FOR_TODO),
        ChatMessage(role="user", content=f"Goal: {goal}"),
    ]

    try:
        response = await chat_completion(messages, temperature=0.0, max_tokens=1024)
        content = response.content.strip()

        # Validate it looks like a todo list
        if "## Todo" in content or _is_valid_todo(content):
            return content
        # If not valid, wrap it
        return render_initial_todo_from_text(content)

    except Exception as exc:
        log.warning("LLM unavailable for todo generation, using fallback", error=str(exc))
        return render_initial_todo([
            "Analyze the goal and determine what needs to be done",
            "Execute the necessary steps to accomplish the goal",
            "Verify the result and clean up",
        ])


def _is_valid_todo(text: str) -> bool:
    """Check if text contains at least one numbered step."""
    return bool(re.search(r"^\d+\.\s*\[", text, re.MULTILINE))


def render_initial_todo_from_text(text: str) -> str:
    """Try to extract step descriptions from arbitrary text and render as todo."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    steps: list[str] = []

    for line in lines:
        # Strip leading numbering
        cleaned = re.sub(r"^\d+[\.\)]\s*", "", line)
        if cleaned and len(cleaned) > 5:
            steps.append(cleaned)

    if not steps:
        steps = ["Execute the goal"]

    return render_initial_todo(steps[:8])  # max 8 steps


# ── The loop ───────────────────────────────────────────────────────

async def run_agent_loop(
    session: AgentSession,
    *,
    on_event: Optional[EventCallback] = None,
    model: Optional[str] = None,
) -> None:
    """
    Run the core agent loop to completion.

    This function:
    1. Sets up the workspace
    2. Generates initial todo.md
    3. Loops: read todo → LLM → tool → update todo → repeat
    4. Streams events via *on_event* callback

    Args:
        session: The session to run (mutated in place).
        on_event: Async callback for streaming events.
        model: Override model name.
    """
    async def emit(event_type: EventType, data: dict[str, Any]) -> None:
        """Send event to callback and store in session."""
        event = {"type": event_type.value, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}
        session.events.append(event)
        if on_event:
            try:
                await on_event(event_type, data)
            except Exception:
                pass  # Don't let event delivery break the loop

    # ── Setup ──
    workspace_path = Path(session.workspace)
    workspace_path.mkdir(parents=True, exist_ok=True)

    session.status = SessionStatus.RUNNING

    # Generate todo.md (Manus discipline §4)
    session.todo_markdown = await generate_initial_todo(session.goal)
    todo_state = parse_todo(session.todo_markdown)

    # Write todo.md to workspace
    (workspace_path / "todo.md").write_text(session.todo_markdown, encoding="utf-8")

    await emit(EventType.TODO_UPDATE, {"todo": session.todo_markdown})

    # Initialize context (Manus discipline §7)
    session.context = AgentContext(
        goal=session.goal,
        todo_markdown=session.todo_markdown,
    )

    # ── Main loop ──
    for iteration in range(1, MAX_ITERATIONS + 1):
        session.iteration = iteration

        await emit(EventType.ITERATION, {"iteration": iteration})

        # Step 1: Read todo.md (recency bias mitigation, §4)
        try:
            todo_content = (workspace_path / "todo.md").read_text(encoding="utf-8")
            session.todo_markdown = todo_content
            session.context.update_todo(todo_content)
            todo_state = parse_todo(todo_content)
        except FileNotFoundError:
            pass  # Use cached version

        # Check completion
        if todo_state.is_complete:
            session.status = SessionStatus.COMPLETED
            session.result_summary = "All todo steps completed."
            await emit(EventType.COMPLETE, {
                "status": "completed",
                "summary": session.result_summary,
                "iteration": iteration,
            })
            return

        # Mark next pending step as in-progress
        if todo_state.next_pending:
            todo_state = mark_in_progress(todo_state, todo_state.next_pending.number)
            new_md = todo_state.to_markdown()
            session.todo_markdown = new_md
            session.context.update_todo(new_md)
            (workspace_path / "todo.md").write_text(new_md, encoding="utf-8")
            await emit(EventType.TODO_UPDATE, {"todo": new_md})

        # Step 2: Build context & call LLM
        messages = session.context.to_messages()

        try:
            response = await chat_completion(messages, model=model, temperature=0.0)
            llm_output = response.content
        except Exception as exc:
            # Keep failure in context (§5)
            error_msg = f"[LLM call failed: {exc}]"
            session.context.append_observation(error_msg)
            await emit(EventType.ERROR, {"error": str(exc), "iteration": iteration})
            # Retry on next iteration if we haven't exhausted attempts
            if iteration >= MAX_ITERATIONS:
                session.status = SessionStatus.FAILED
                session.result_summary = f"LLM failed after {MAX_ITERATIONS} iterations: {exc}"
                await emit(EventType.COMPLETE, {
                    "status": "failed",
                    "summary": session.result_summary,
                })
                return
            continue

        # Step 3: Parse & execute tool call
        tool_call = parse_tool_call(llm_output)

        if tool_call is None:
            # LLM didn't produce a valid tool call — nudge it
            session.context.append_assistant(llm_output)
            session.context.append_observation(
                "Your last response did not contain a valid JSON tool call. "
                "Please respond with exactly one tool call in JSON format."
            )
            await emit(EventType.THOUGHT, {
                "content": llm_output[:500],
                "note": "No valid tool call detected",
            })
            continue

        # Record the assistant's action
        session.context.append_assistant(llm_output)

        await emit(EventType.TOOL_CALL, {
            "tool": tool_call.get("tool"),
            "args": tool_call.get("args", {}),
        })

        # Execute the tool
        result = await execute_tool(tool_call, session.workspace)

        # Step 4: Observe result (failures stay in context, §5)
        observation = result["output"]
        session.context.append_observation(observation)

        await emit(EventType.TOOL_RESULT, {
            "tool": result["tool"],
            "success": result["success"],
            "output": observation[:2000],  # Truncate for event
        })

        # Check for finish tool
        if result["output"] == "__FINISH__":
            # Mark all remaining steps as completed
            for step in todo_state.steps:
                if step.status in (StepStatus.PENDING, StepStatus.IN_PROGRESS):
                    todo_state = mark_completed(todo_state, step.number)

            new_md = todo_state.to_markdown()
            session.todo_markdown = new_md
            (workspace_path / "todo.md").write_text(new_md, encoding="utf-8")
            await emit(EventType.TODO_UPDATE, {"todo": new_md})

            session.status = SessionStatus.COMPLETED
            session.result_summary = result.get("summary", "Task completed via finish tool")
            await emit(EventType.COMPLETE, {
                "status": "completed",
                "summary": session.result_summary,
                "iteration": iteration,
            })
            return

        # Step 5: Update todo.md
        current_step = todo_state.current_step
        if current_step:
            if result["success"]:
                todo_state = mark_completed(todo_state, current_step.number)
            else:
                # Keep failure in context — don't immediately mark as failed
                # Let the agent retry or try a different approach
                pass

        new_md = todo_state.to_markdown()
        session.todo_markdown = new_md
        session.context.update_todo(new_md)
        (workspace_path / "todo.md").write_text(new_md, encoding="utf-8")
        await emit(EventType.TODO_UPDATE, {"todo": new_md})

    # ── Exhausted iterations ──
    session.status = SessionStatus.FAILED
    session.result_summary = f"Reached max iterations ({MAX_ITERATIONS}) without completion."
    await emit(EventType.COMPLETE, {
        "status": "failed",
        "summary": session.result_summary,
    })


# ── Session factory ────────────────────────────────────────────────

def create_session(goal: str) -> AgentSession:
    """
    Create a new agent session with a unique ID and workspace.

    Args:
        goal: The user's task/goal string.

    Returns:
        A new :class:`AgentSession` ready to run.
    """
    session_id = uuid.uuid4().hex[:12]
    workspace = str(Path(SESSION_WORKSPACE_ROOT) / session_id)
    return AgentSession(
        session_id=session_id,
        goal=goal,
        workspace=workspace,
    )
