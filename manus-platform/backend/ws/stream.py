"""
WebSocket manager.

Manages WebSocket connections for session event streaming.

Event format (JSON):

    {
        "type": "thought" | "todo_update" | "tool_call" | "tool_result" | "complete" | "error",
        "data": { ... },
        "timestamp": "2026-08-13T10:14:00Z"
    }
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

from agent.loop import EventType


# ── Connection registry ────────────────────────────────────────────

@dataclass
class SessionConnection:
    """A WebSocket connection subscribed to a session."""

    websocket: WebSocket
    session_id: str
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)

    async def send_event(self, event: dict[str, Any]) -> None:
        """Push an event onto the send queue."""
        await self.queue.put(event)

    async def pump(self) -> None:
        """
        Forward queued events to the WebSocket.

        Runs until the connection closes or the session ends.
        """
        try:
            while True:
                event = await self.queue.get()
                await self.websocket.send_text(json.dumps(event))
                if event.get("type") == "complete":
                    break
        except WebSocketDisconnect:
            pass
        except Exception:
            pass


class ConnectionManager:
    """
    Manages WebSocket connections per session.

    Usage:
        1. Client connects to ``ws://host/ws/{session_id}``
        2. ``manager.connect(ws, session_id)`` registers the connection
        3. ``manager.broadcast(session_id, event)`` sends to all subscribers
        4. ``manager.disconnect(session_id)`` cleans up
    """

    def __init__(self) -> None:
        self._connections: dict[str, list[SessionConnection]] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> SessionConnection:
        """
        Accept a WebSocket connection and register it for a session.

        Args:
            websocket: The incoming WebSocket.
            session_id: Session to subscribe to.

        Returns:
            The created :class:`SessionConnection`.
        """
        await websocket.accept()

        conn = SessionConnection(websocket=websocket, session_id=session_id)
        self._connections.setdefault(session_id, []).append(conn)

        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "data": {"session_id": session_id},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))

        return conn

    async def broadcast(self, session_id: str, event: dict[str, Any]) -> None:
        """
        Send an event to all connections subscribed to a session.

        Args:
            session_id: Target session.
            event: Event dict to send.
        """
        conns = self._connections.get(session_id, [])
        for conn in conns:
            await conn.send_event(event)

    def disconnect(self, session_id: str, conn: SessionConnection) -> None:
        """Remove a connection from the registry."""
        conns = self._connections.get(session_id, [])
        if conn in conns:
            conns.remove(conn)
        if not conns:
            self._connections.pop(session_id, None)

    def get_subscribers(self, session_id: str) -> int:
        """Return the number of active subscribers for a session."""
        return len(self._connections.get(session_id, []))


# Singleton manager
manager = ConnectionManager()


# ── Event callback factory ─────────────────────────────────────────

def make_ws_callback(session_id: str) -> Any:
    """
    Create an event callback that broadcasts to a session's WebSocket subscribers.

    Returns an async function suitable for passing to ``run_agent_loop``.
    """

    async def _callback(event_type: EventType, data: dict[str, Any]) -> None:
        event = {
            "type": event_type.value,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await manager.broadcast(session_id, event)

    return _callback
