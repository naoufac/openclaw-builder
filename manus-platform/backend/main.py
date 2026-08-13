"""
FastAPI application — Manus-like platform backend (M1).

Endpoints:
    POST   /api/task          → Submit a goal, start agent session
    GET    /api/session/{id}  → Get session status
    WS     /ws/{session_id}   → Stream agent events in real time
    GET    /api/health        → Health check
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.loop import (
    AgentSession,
    EventType,
    SessionStatus,
    create_session,
    run_agent_loop,
)
from config import HOST, PORT, SESSION_WORKSPACE_ROOT
from ws.stream import manager, make_ws_callback


# ── Session registry (in-memory) ───────────────────────────────────

_sessions: dict[str, AgentSession] = {}


# ── Pydantic models ────────────────────────────────────────────────

class TaskRequest(BaseModel):
    """Request body for POST /api/task."""

    goal: str = Field(..., min_length=1, max_length=10000, description="The task goal")
    model: Optional[str] = Field(None, description="Model override (e.g. 'claude-sonnet-4-20250514')")


class TaskResponse(BaseModel):
    """Response for POST /api/task."""

    session_id: str
    status: str
    goal: str
    created_at: str


class SessionResponse(BaseModel):
    """Response for GET /api/session/{id}."""

    session_id: str
    status: str
    goal: str
    iteration: int
    todo_markdown: str
    result_summary: str
    created_at: str
    events_count: int


class HealthResponse(BaseModel):
    """Response for GET /api/health."""

    status: str
    timestamp: str
    active_sessions: int
    sessions_root: str


# ── App lifespan ───────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Ensure session workspace root exists
    Path(SESSION_WORKSPACE_ROOT).mkdir(parents=True, exist_ok=True)
    yield  # App runs


# ── FastAPI app ────────────────────────────────────────────────────

app = FastAPI(
    title="Manus Platform Backend",
    description="Self-hosted autonomous agent platform — M1 Core Agent Loop",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ─────────────────────────────────────────────────────────

@app.post("/api/task", response_model=TaskResponse)
async def create_task(request: TaskRequest) -> TaskResponse:
    """
    Accept a goal, create a session, and start the agent loop in the background.

    The agent loop runs as a background ``asyncio`` task.
    Connect to ``/ws/{session_id}`` to stream events.
    """
    session = create_session(request.goal)
    _sessions[session.session_id] = session

    # Build the event callback for WebSocket streaming
    ws_callback = make_ws_callback(session.session_id)

    # Start the agent loop in the background
    asyncio.create_task(
        run_agent_loop(
            session,
            on_event=ws_callback,
            model=request.model,
        )
    )

    return TaskResponse(
        session_id=session.session_id,
        status=session.status.value,
        goal=session.goal,
        created_at=session.created_at,
    )


@app.get("/api/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """
    Get the current status of a session.

    Returns the latest todo.md, iteration count, and result summary.
    """
    session = _sessions.get(session_id)
    if session is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return SessionResponse(
        session_id=session.session_id,
        status=session.status.value,
        goal=session.goal,
        iteration=session.iteration,
        todo_markdown=session.todo_markdown,
        result_summary=session.result_summary,
        created_at=session.created_at,
        events_count=len(session.events),
    )


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    active = sum(
        1 for s in _sessions.values()
        if s.status == SessionStatus.RUNNING
    )
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        active_sessions=active,
        sessions_root=SESSION_WORKSPACE_ROOT,
    )


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """
    WebSocket endpoint for real-time agent event streaming.

    Connect and receive events:
    - ``thought``: Agent reasoning
    - ``todo_update``: Plan updated
    - ``tool_call``: Tool invoked
    - ``tool_result``: Tool output
    - ``complete``: Session finished
    - ``error``: Error occurred
    """
    # Accept and register connection
    conn = await manager.connect(websocket, session_id)

    # Check session exists
    session = _sessions.get(session_id)
    if session is None:
        await websocket.send_text(json.dumps({
            "type": "error",
            "data": {"error": f"Session '{session_id}' not found"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
        await websocket.close()
        manager.disconnect(session_id, conn)
        return

    # If session has already produced events, replay them
    for event in session.events:
        await websocket.send_text(json.dumps(event))

    # Pump new events
    try:
        await conn.pump()
    finally:
        manager.disconnect(session_id, conn)


# ── Entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info",
    )
