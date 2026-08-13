"""
Context management — frozen prefix + append-only working area.

Layout (Manus discipline §7):

    [FROZEN PREFIX — never modified after session start]
      - System instructions (tool descriptions, rules)
      - User goal
      - todo.md contents (current snapshot)
    [APPEND-ONLY WORKING AREA — grows each iteration]
      - Thoughts, tool calls, tool results, observations, errors

The prefix is re-serialized every iteration (todo.md is re-read) but
the *instructions* and *goal* portions are stable, enabling KV-cache
reuse.  The working area only grows; nothing is ever removed.

Failures stay in context (Manus discipline §5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.todo import TodoState
from models.router import ChatMessage


# ── System prompt ──────────────────────────────────────────────────

SYSTEM_INSTRUCTIONS = """\
You are Manus, an autonomous AI agent that completes tasks by using tools.

## How You Work

1. You maintain a todo.md file with your plan.
2. Each iteration, you read todo.md, choose the next action, execute a tool, and observe the result.
3. You update todo.md after each step.

## Available Tools

You respond with a JSON tool call on a single line. The format is:

```json
{"tool": "<name>", "args": {<key-value pairs>}}
```

### Tools

- **shell**: Run a shell command.
  - args: {"command": "<shell command>"}
  - Example: {"tool": "shell", "args": {"command": "echo hello && python3 script.py"}}

- **file_write**: Write content to a file.
  - args: {"path": "<relative path>", "content": "<file content>"}
  - Example: {"tool": "file_write", "args": {"path": "hello.py", "content": "print('hello')"}}

- **file_read**: Read a file.
  - args: {"path": "<relative path>"}
  - Example: {"tool": "file_read", "args": {"path": "output.txt"}}

- **file_list**: List files in a directory.
  - args: {"path": "<relative path, default .>"}
  - Example: {"tool": "file_list", "args": {"path": "."}}

- **web_fetch**: Fetch a URL and return the page content.
  - args: {"url": "<https url>"}
  - Example: {"tool": "web_fetch", "args": {"url": "https://example.com"}}

- **spawn_subagent**: Spawn a single sub-agent for an independent sub-task.
  - Use when you have a self-contained task that can run in parallel.
  - The sub-agent gets its own sandbox and workspace.
  - Sub-agents CANNOT spawn their own sub-agents beyond depth 2.
  - Only use for INDEPENDENT tasks — never for tasks that depend on each other.
  - args: {"task": "<clear task description>", "max_iterations": 5}
  - Example: {"tool": "spawn_subagent", "args": {"task": "Research the history of Python and write a summary file", "max_iterations": 5}}

- **wide_research**: Spawn N parallel sub-agents to research multiple topics at once.
  - Use when you have multiple INDEPENDENT topics to research simultaneously.
  - Each topic gets its own sub-agent running in its own sandbox.
  - All sub-agents run in PARALLEL and results are combined.
  - Do NOT use for sequential/dependent tasks.
  - args: {"topics": ["topic1", "topic2", ...], "max_iterations": 5}
  - Example: {"tool": "wide_research", "args": {"topics": ["python async programming", "docker best practices", "fastapi tutorial"], "max_iterations": 5}}

- **finish**: Signal that the task is complete.
  - args: {"summary": "<brief summary of what was accomplished>"}
  - Example: {"tool": "finish", "args": {"summary": "Created hello.py with a print statement"}}

## Rules

- ALWAYS respond with exactly ONE tool call per turn.
- Use the shell tool for running code, installing packages, or system operations.
- Write files for anything that needs to persist.
- Keep working until the task is done, then call finish.
- If something fails, try a different approach. Failures are information.
- Be concise in your reasoning before the tool call.
- Use **spawn_subagent** or **wide_research** only for tasks that are truly independent and can run in parallel.
- Do NOT spawn sub-agents for tasks that depend on each other's output — sequence those in the main loop.
- When using wide_research, wait for ALL results before synthesizing.
"""


# ── Context manager ────────────────────────────────────────────────

@dataclass
class AgentContext:
    """
    Manages the conversation context for a single agent session.

    The prefix (instructions + goal + todo) is rebuilt each iteration
    because todo.md may change. The working area is append-only.
    """

    goal: str
    todo_markdown: str = ""
    working_area: list[ChatMessage] = field(default_factory=list)

    # ── Prefix ──

    def _build_prefix(self) -> list[ChatMessage]:
        """Build the frozen prefix messages."""
        prefix_content = (
            f"{SYSTEM_INSTRUCTIONS}\n\n"
            f"## Goal\n\n{self.goal}\n\n"
            f"## Current Plan (todo.md)\n\n{self.todo_markdown}"
        )
        return [ChatMessage(role="system", content=prefix_content)]

    def update_todo(self, todo_markdown: str) -> None:
        """
        Update the todo.md snapshot in the prefix.

        This replaces the todo portion of the prefix. The instructions
        and goal remain stable for cache reuse.
        """
        self.todo_markdown = todo_markdown

    # ── Working area (append-only) ──

    def append_user(self, content: str) -> None:
        """Append a user-role message (observation) to the working area."""
        self.working_area.append(ChatMessage(role="user", content=content))

    def append_assistant(self, content: str) -> None:
        """Append an assistant-role message (thought/action) to the working area."""
        self.working_area.append(ChatMessage(role="assistant", content=content))

    def append_observation(self, observation: str) -> None:
        """Append a tool result observation to the working area."""
        # Observations come as user messages (OpenAI convention)
        self.working_area.append(
            ChatMessage(
                role="user",
                content=f"## Observation\n\n{observation}",
            )
        )

    # ── Serialization ──

    def to_messages(self) -> list[ChatMessage]:
        """
        Serialize to a message list for the LLM call.

        Returns: [prefix_system_msg] + [working_area_messages...]

        The prefix is rebuilt fresh each call (todo.md is current).
        The working area messages retain their order (append-only).
        """
        return self._build_prefix() + list(self.working_area)

    # ── Summary ──

    def __repr__(self) -> str:
        return (
            f"AgentContext(goal={self.goal!r}, "
            f"working_msgs={len(self.working_area)}, "
            f"todo_len={len(self.todo_markdown)})"
        )
