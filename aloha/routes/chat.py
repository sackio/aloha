"""
aloha/routes/chat.py

Chat and session endpoints:
  GET    /api/sessions           — list all sessions
  POST   /api/sessions           — create a new session
  GET    /api/sessions/{id}      — get session with full message history
  DELETE /api/sessions/{id}      — delete session

  POST   /api/chat               — SSE streaming chat
  POST   /api/approve            — approve or reject a pending diff
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from aloha.config import AlohaConfig

log = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Module-level store for active AgentLoop instances (session_id -> AgentLoop)
# ---------------------------------------------------------------------------
_active_loops: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class CreateSessionRequest(BaseModel):
    title: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ApproveRequest(BaseModel):
    diff_id: str
    action: str  # "apply" | "reject"


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------


def _sessions_dir(config: AlohaConfig) -> Path:
    return config.data_dir / "sessions"


def _session_path(config: AlohaConfig, session_id: str) -> Path:
    return _sessions_dir(config) / f"{session_id}.json"


def _make_session_id() -> str:
    """ses_ + 12 hex chars."""
    return "ses_" + secrets.token_hex(6)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_session(config: AlohaConfig, session_id: str) -> dict[str, Any]:
    path = _session_path(config, session_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    with path.open() as f:
        return json.load(f)


def _save_session(config: AlohaConfig, session: dict[str, Any]) -> None:
    d = _sessions_dir(config)
    d.mkdir(parents=True, exist_ok=True)
    path = _session_path(config, session["id"])
    with path.open("w") as f:
        json.dump(session, f, indent=2)


def _session_summary(session: dict[str, Any]) -> dict[str, Any]:
    """Strip messages; return lightweight summary."""
    messages = session.get("messages", [])
    return {
        "id": session["id"],
        "title": session.get("title", "New conversation"),
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "message_count": len(messages),
    }


# ---------------------------------------------------------------------------
# Session CRUD endpoints
# ---------------------------------------------------------------------------


@router.get("/api/sessions")
async def list_sessions() -> JSONResponse:
    """Return all sessions sorted newest-first."""
    cfg = AlohaConfig.load()
    d = _sessions_dir(cfg)
    if not d.exists():
        return JSONResponse([])

    sessions = []
    for path in sorted(d.glob("ses_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with path.open() as f:
                data = json.load(f)
            sessions.append(_session_summary(data))
        except Exception:
            log.debug("Could not load session file %s", path, exc_info=True)

    return JSONResponse(sessions)


@router.post("/api/sessions", status_code=201)
async def create_session(body: CreateSessionRequest) -> JSONResponse:
    """Create a new empty session."""
    cfg = AlohaConfig.load()
    now = _now_iso()
    session: dict[str, Any] = {
        "id": _make_session_id(),
        "title": body.title or "New conversation",
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    _save_session(cfg, session)
    return JSONResponse(_session_summary(session))


@router.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> JSONResponse:
    """Return session with full message history."""
    cfg = AlohaConfig.load()
    session = _load_session(cfg, session_id)
    return JSONResponse(session)


@router.delete("/api/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str) -> None:
    """Delete a session file."""
    cfg = AlohaConfig.load()
    path = _session_path(cfg, session_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    path.unlink()


# ---------------------------------------------------------------------------
# Chat (SSE streaming)
# ---------------------------------------------------------------------------


@router.post("/api/chat")
async def chat(body: ChatRequest, request: Request) -> StreamingResponse:
    """
    Stream a chat completion as Server-Sent Events.

    Each event is: data: <JSON>\\n\\n
    Event types: content, tool_call, tool_result, diff, done, error
    """
    cfg = AlohaConfig.load()

    # Load or create session
    try:
        session = _load_session(cfg, body.session_id)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Session not found")

    history = session.get("messages", [])

    return StreamingResponse(
        _event_stream(cfg, session, history, body.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _event_stream(
    cfg: AlohaConfig,
    session: dict[str, Any],
    history: list[dict[str, Any]],
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    Drive the AgentLoop and yield SSE-formatted event strings.

    After the stream ends (done/error), saves updated session to disk.
    """
    from aloha.agent.loop import AgentLoop
    from aloha.backends.router import get_backend

    session_id = session["id"]
    assistant_content_parts: list[str] = []
    stream_errored = False

    try:
        backend = get_backend(cfg)
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'message': f'Backend not configured: {exc}', 'code': 'BACKEND_ERROR'})}\n\n"
        return

    loop = AgentLoop(cfg, backend)
    _active_loops[session_id] = loop

    # Determine supervision mode from safety setting
    mode = "supervised" if cfg.safety_mode != "permissive" else "autonomous"

    # Build history in OpenAI format for the loop
    openai_history = [
        {"role": m["role"], "content": m["content"]}
        for m in history
        if m["role"] in ("user", "assistant")
    ]

    try:
        async for event in loop.run(session_id, user_message, openai_history, mode=mode):
            event_type = event.get("type")

            # Accumulate assistant text for session save
            if event_type == "content":
                assistant_content_parts.append(event.get("delta", ""))
            elif event_type == "error":
                stream_errored = True

            yield f"data: {json.dumps(event)}\n\n"

    except Exception as exc:
        log.exception("SSE stream failed for session %s", session_id)
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        stream_errored = True

    finally:
        _active_loops.pop(session_id, None)

        # Persist updated session
        try:
            now = _now_iso()
            # Append user message
            session["messages"].append({"role": "user", "content": user_message})

            # Append assistant message if we got content
            assistant_text = "".join(assistant_content_parts)
            if assistant_text:
                session["messages"].append({"role": "assistant", "content": assistant_text})

            # Auto-set title from first user message if still default
            if session.get("title") in (None, "New conversation", "") and user_message:
                session["title"] = user_message[:60].strip()

            session["updated_at"] = now
            _save_session(cfg, session)
        except Exception:
            log.warning("Failed to save session %s after stream", session_id, exc_info=True)


# ---------------------------------------------------------------------------
# Approve endpoint
# ---------------------------------------------------------------------------


@router.post("/api/approve")
async def approve(body: ApproveRequest) -> JSONResponse:
    """
    Resolve a pending diff by approving or rejecting it.

    Searches all active AgentLoop instances for the diff_id.
    Returns 404 if the diff_id is not found or already resolved.
    """
    if body.action not in ("apply", "reject"):
        raise HTTPException(status_code=400, detail="action must be 'apply' or 'reject'")

    diff_id = body.diff_id

    # Search active loops for the pending diff
    for loop in list(_active_loops.values()):
        if loop.resolve_diff(diff_id, body.action):
            return JSONResponse({"ok": True, "diff_id": diff_id, "action": body.action})

    raise HTTPException(status_code=404, detail="Diff not found or already resolved")
