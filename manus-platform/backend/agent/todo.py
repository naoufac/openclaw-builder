"""
todo.md protocol.

The todo file is the agent's persistent plan. It is:
- Created at session start from the user's goal.
- Read at the START of every iteration (recency bias mitigation).
- Updated at the END of every iteration.

Format (Markdown):

    ## Todo

    1. [✓] Step description           ← completed
    2. [→] Current step description   ← in progress
    3. [ ] Future step description     ← pending
    4. [✗] Failed step description     ← failed (stays in context)

"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StepStatus(str, Enum):
    """Status of a todo step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# Status marker mapping
_STATUS_MARKERS: dict[StepStatus, str] = {
    StepStatus.COMPLETED: "✓",
    StepStatus.IN_PROGRESS: "→",
    StepStatus.PENDING: " ",
    StepStatus.FAILED: "✗",
}

_MARKER_TO_STATUS: dict[str, StepStatus] = {
    "✓": StepStatus.COMPLETED,
    "✅": StepStatus.COMPLETED,
    "x": StepStatus.COMPLETED,
    "X": StepStatus.COMPLETED,
    "→": StepStatus.IN_PROGRESS,
    "->": StepStatus.IN_PROGRESS,
    ">": StepStatus.IN_PROGRESS,
    "...": StepStatus.IN_PROGRESS,
    "✗": StepStatus.FAILED,
    "✘": StepStatus.FAILED,
    "!": StepStatus.FAILED,
}

# Regex for parsing numbered steps: ``1. [✓] description``
_STEP_RE = re.compile(
    r"^(\d+)\.\s*\[([^\]]*)\]\s*(.*)$"
)


@dataclass
class TodoStep:
    """A single step in the todo list."""

    number: int
    status: StepStatus
    description: str

    def to_markdown(self) -> str:
        """Serialize to a markdown line."""
        marker = _STATUS_MARKERS[self.status]
        return f"{self.number}. [{marker}] {self.description}"


@dataclass
class TodoState:
    """Parsed state of a todo.md file."""

    steps: list[TodoStep] = field(default_factory=list)

    @property
    def current_step(self) -> Optional[TodoStep]:
        """The step currently in progress, if any."""
        for step in self.steps:
            if step.status == StepStatus.IN_PROGRESS:
                return step
        return None

    @property
    def next_pending(self) -> Optional[TodoStep]:
        """The first pending step."""
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                return step
        return None

    @property
    def is_complete(self) -> bool:
        """True when all steps are completed (or failed, which counts as resolved)."""
        if not self.steps:
            return False
        return all(
            s.status in (StepStatus.COMPLETED, StepStatus.FAILED) for s in self.steps
        )

    @property
    def completed_count(self) -> int:
        """Number of completed steps."""
        return sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)

    @property
    def total_count(self) -> int:
        """Total number of steps."""
        return len(self.steps)

    def to_markdown(self) -> str:
        """Serialize the full todo to markdown."""
        lines = ["## Todo", ""]
        for step in self.steps:
            lines.append(step.to_markdown())
        lines.append("")
        return "\n".join(lines)


# ── Parsing ────────────────────────────────────────────────────────

def parse_todo(content: str) -> TodoState:
    """
    Parse a todo.md string into :class:`TodoState`.

    Handles the ``N. [marker] description`` format.
    Non-matching lines are ignored.
    """
    state = TodoState()

    for line in content.splitlines():
        line = line.strip()
        match = _STEP_RE.match(line)
        if not match:
            continue

        number = int(match.group(1))
        marker_str = match.group(2).strip()
        description = match.group(3).strip()

        status = _MARKER_TO_STATUS.get(marker_str, StepStatus.PENDING)
        state.steps.append(
            TodoStep(number=number, status=status, description=description)
        )

    return state


# ── Mutation helpers ───────────────────────────────────────────────

def mark_status(state: TodoState, step_number: int, status: StepStatus) -> TodoState:
    """
    Return a *new* TodoState with the given step's status updated.

    Args:
        state: Current todo state.
        step_number: 1-based step number to update.
        status: New status.

    Returns:
        Updated TodoState (does not mutate the original).
    """
    new_steps: list[TodoStep] = []
    for step in state.steps:
        if step.number == step_number:
            new_steps.append(
                TodoStep(number=step.number, status=status, description=step.description)
            )
        else:
            new_steps.append(step)
    return TodoState(steps=new_steps)


def mark_completed(state: TodoState, step_number: int) -> TodoState:
    """Mark a step as completed."""
    return mark_status(state, step_number, StepStatus.COMPLETED)


def mark_in_progress(state: TodoState, step_number: int) -> TodoState:
    """Mark a step as in progress (and clear any other in-progress)."""
    new_steps: list[TodoStep] = []
    for step in state.steps:
        if step.number == step_number:
            new_steps.append(
                TodoStep(number=step.number, status=StepStatus.IN_PROGRESS, description=step.description)
            )
        elif step.status == StepStatus.IN_PROGRESS:
            # Demote previous in-progress back to pending
            new_steps.append(
                TodoStep(number=step.number, status=StepStatus.PENDING, description=step.description)
            )
        else:
            new_steps.append(step)
    return TodoState(steps=new_steps)


def mark_failed(state: TodoState, step_number: int) -> TodoState:
    """Mark a step as failed. Failures stay in context per Manus discipline."""
    return mark_status(state, step_number, StepStatus.FAILED)


# ── Initial todo generation ────────────────────────────────────────

SYSTEM_PROMPT_FOR_TODO = """\
You are a task planning assistant. Given a goal, create a step-by-step todo list.
Each step should be concrete, actionable, and ordered.
Use simple language. 3-8 steps typically.

Output ONLY the todo list in this exact format:

## Todo

1. [ ] First step description
2. [ ] Second step description
3. [ ] Third step description

Do not add any other text before or after.
"""


def render_initial_todo(steps: list[str]) -> str:
    """
    Render an initial todo.md string from a list of step descriptions.

    This is used when the LLM generates the plan.
    """
    lines = ["## Todo", ""]
    for i, desc in enumerate(steps, 1):
        lines.append(f"{i}. [ ] {desc}")
    lines.append("")
    return "\n".join(lines)
