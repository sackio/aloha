"""
aloha/agent/types.py

All domain types and SSE event models used across the Aloha agent.
Import from here; do not duplicate these definitions elsewhere.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Safety levels
# ---------------------------------------------------------------------------

class SafetyLevel(str, Enum):
    """
    Severity classification for each MCP tool.

    READ          — read-only; never modifies state; always auto-approved.
    WRITE_SOFT    — changes runtime state only (e.g. turn on a light);
                    reversible; auto-approved in normal safety mode.
    WRITE_CONFIG  — modifies persistent configuration files (YAML, JSON);
                    requires user approval or SAFETY_MODE=permissive.
    DESTRUCTIVE   — irreversible or high-risk (e.g. delete automation,
                    restart HA); always requires explicit user approval.
    """

    READ = "read"
    WRITE_SOFT = "write_soft"
    WRITE_CONFIG = "write_config"
    DESTRUCTIVE = "destructive"


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

class ToolDef(BaseModel):
    """
    Descriptor for a single MCP-style tool exposed to the AI backend.

    `parameters` is a JSON Schema object dict, e.g.:
        {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "..."}
            },
            "required": ["entity_id"]
        }
    """

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    safety: SafetyLevel = SafetyLevel.READ
    returns: str = "str"   # human-readable description of the return type


# ---------------------------------------------------------------------------
# Chat message
# ---------------------------------------------------------------------------

class Message(BaseModel):
    """
    A single turn in the conversation history.

    role       — "user" | "assistant" | "tool"
    content    — the text body of the message (may be empty string for
                 assistant turns that only contain tool calls)
    tool_call_id — present only when role == "tool"; links result to call
    tool_name    — present only when role == "tool"; used by some backends
    """

    role: Literal["user", "assistant", "tool"]
    content: str
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None


# ---------------------------------------------------------------------------
# SSE event models
# ---------------------------------------------------------------------------
# Every event emitted over the /api/chat SSE stream must be one of these.
# The frontend discriminates on the `type` field.

class ContentEvent(BaseModel):
    """Streamed text delta from the AI."""
    type: Literal["content"] = "content"
    delta: str


class ToolCallEvent(BaseModel):
    """
    The AI is invoking a tool.
    Emitted before the tool runs so the frontend can show a spinner.
    """
    type: Literal["tool_call"] = "tool_call"
    id: str           # unique call id (echoed back in ToolResultEvent)
    name: str         # tool name
    args: dict[str, Any]


class ToolResultEvent(BaseModel):
    """Result of a tool call (or error if the tool raised)."""
    type: Literal["tool_result"] = "tool_result"
    id: str           # matches ToolCallEvent.id
    name: str
    result: str       # JSON-serialised or plain-text result
    error: bool = False


class DiffEvent(BaseModel):
    """
    The AI proposes a file change that requires human approval.

    id      — unique diff id; used with POST /api/approve
    path    — absolute path of the file inside the container (e.g.
              /data/homeassistant/automations/lights.yaml)
    before  — current file content (empty string if file does not exist)
    after   — proposed new content
    content — same as `after`; included as a convenience alias so the
              frontend can write the file directly without re-deriving it
    """
    type: Literal["diff"] = "diff"
    id: str
    path: str
    before: str
    after: str
    content: str      # alias for after; value must equal after


class DoneEvent(BaseModel):
    """Signals end of stream. usage contains token counts if available."""
    type: Literal["done"] = "done"
    usage: Optional[dict[str, int]] = None


class ErrorEvent(BaseModel):
    """Fatal error during stream processing."""
    type: Literal["error"] = "error"
    message: str
    code: Optional[str] = None
