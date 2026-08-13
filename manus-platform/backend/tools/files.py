"""
File system tools.

Provides read, write, and list operations for the agent workspace.
All operations are confined to the session workspace directory.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FileResult:
    """Result of a file operation."""

    success: bool
    content: str = ""
    error: str = ""
    path: str = ""

    def to_observation(self) -> str:
        """Format as an observation string for the agent context."""
        if not self.success:
            return f"[File operation failed: {self.error}]"
        return self.content


def _safe_path(workspace: str, rel_path: str) -> Path:
    """
    Resolve *rel_path* inside *workspace*, preventing path traversal.

    Raises:
        ValueError: If the resolved path escapes the workspace.
    """
    workspace_abs = Path(workspace).resolve()
    target = (workspace_abs / rel_path).resolve()

    # Prevent path traversal
    if not str(target).startswith(str(workspace_abs)):
        raise ValueError(f"Path '{rel_path}' escapes workspace boundary")
    return target


async def file_read(workspace: str, path: str, *, max_bytes: int = 512_000) -> FileResult:
    """
    Read a file from the workspace.

    Args:
        workspace: Absolute path to the session workspace.
        path: Relative path within the workspace.
        max_bytes: Maximum bytes to read (≈500 KiB default).

    Returns:
        :class:`FileResult` with the file content.
    """
    try:
        target = _safe_path(workspace, path)
        if not target.exists():
            return FileResult(success=False, error=f"File not found: {path}", path=path)
        if not target.is_file():
            return FileResult(success=False, error=f"Not a file: {path}", path=path)

        data = target.read_bytes()
        if len(data) > max_bytes:
            data = data[:max_bytes]
            truncated = f"\n\n[... truncated at {max_bytes} bytes ...]"
        else:
            truncated = ""

        content = data.decode("utf-8", errors="replace") + truncated
        return FileResult(success=True, content=content, path=str(target))

    except ValueError as exc:
        return FileResult(success=False, error=str(exc), path=path)
    except Exception as exc:
        return FileResult(success=False, error=f"Read error: {exc}", path=path)


async def file_write(workspace: str, path: str, content: str) -> FileResult:
    """
    Write content to a file in the workspace.

    Creates parent directories if needed. Overwrites existing files.

    Args:
        workspace: Absolute path to the session workspace.
        path: Relative path within the workspace.
        content: Text content to write.

    Returns:
        :class:`FileResult` confirming the write.
    """
    try:
        target = _safe_path(workspace, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return FileResult(
            success=True,
            content=f"Wrote {len(content)} bytes to {path}",
            path=str(target),
        )

    except ValueError as exc:
        return FileResult(success=False, error=str(exc), path=path)
    except Exception as exc:
        return FileResult(success=False, error=f"Write error: {exc}", path=path)


async def file_list(workspace: str, path: str = ".") -> FileResult:
    """
    List files in a directory within the workspace.

    Args:
        workspace: Absolute path to the session workspace.
        path: Relative directory path (default: workspace root).

    Returns:
        :class:`FileResult` with a newline-separated listing.
    """
    try:
        target = _safe_path(workspace, path)
        if not target.exists():
            return FileResult(success=False, error=f"Directory not found: {path}", path=path)
        if not target.is_dir():
            return FileResult(success=False, error=f"Not a directory: {path}", path=path)

        entries: list[str] = []
        for entry in sorted(target.iterdir()):
            marker = "/" if entry.is_dir() else ""
            entries.append(f"{entry.name}{marker}")

        content = "\n".join(entries) if entries else "(empty directory)"
        return FileResult(success=True, content=content, path=str(target))

    except ValueError as exc:
        return FileResult(success=False, error=str(exc), path=path)
    except Exception as exc:
        return FileResult(success=False, error=f"List error: {exc}", path=path)
