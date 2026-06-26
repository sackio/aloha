"""
aloha/agent/loop.py

AgentLoop — the core agentic reasoning loop.

Responsibilities
----------------
- Drive multi-turn conversations with the AI backend.
- Execute tool calls via the tool registry.
- Handle the supervised approval gate for DiffEvent proposals:
    * supervised  — pause execution, wait for user approve/reject via
                    resolve_diff(), then write the file (or skip).
    * autonomous  — write the file immediately without pausing.
- Stream all events (content deltas, tool calls, tool results, diffs, done,
  errors) to callers via an asyncio.Queue.

Usage
-----
    loop = AgentLoop(config, backend)
    async for event in loop.run(session_id, user_message, history, mode="supervised"):
        # event is a dict with a "type" key matching SSE event models
        ...
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
from typing import Any, AsyncIterator

import aiofiles

from aloha.agent.types import (
    ContentEvent,
    DiffEvent,
    DoneEvent,
    ErrorEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from aloha.config import AlohaConfig
from aloha.ha.client import get_ha_client
from aloha.mcp.client import get_mcp_manager
from aloha.mcp.registry import ALL_TOOLS, execute_tool

log = logging.getLogger(__name__)

# Sentinel value placed on the queue to signal end-of-stream.
_DONE_SENTINEL = None


# ---------------------------------------------------------------------------
# AgentLoop
# ---------------------------------------------------------------------------


class AgentLoop:
    """
    Drives the agent reasoning loop for a single agent configuration.

    Parameters
    ----------
    config : AlohaConfig
        Runtime configuration (used for safety_mode, etc.).
    backend : BaseBackend
        AI provider backend that implements chat_stream().
    """

    def __init__(self, config: AlohaConfig, backend: Any) -> None:
        self._config = config
        self._backend = backend

        # diff_id → asyncio.Event; set when user calls resolve_diff()
        self._pending_diffs: dict[str, asyncio.Event] = {}
        # diff_id → "apply" | "reject"
        self._diff_decisions: dict[str, str] = {}
        # session_id → asyncio.Task
        self._active_sessions: dict[str, asyncio.Task] = {}  # type: ignore[type-arg]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        session_id: str,
        user_message: str,
        history: list[dict[str, Any]],
        mode: str = "supervised",
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Run one user turn and yield SSE-ready event dicts until the turn
        is complete.

        Parameters
        ----------
        session_id : str
            Identifies the conversation session (used for cancellation).
        user_message : str
            The new user message to append to history.
        history : list[dict]
            Prior conversation turns in OpenAI messages format.
        mode : str
            "supervised" — pause on diffs and wait for user approval.
            "autonomous" — apply diffs immediately without pausing.

        Yields
        ------
        dict
            SSE event dicts (content, tool_call, tool_result, diff, done,
            error).
        """
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

        task = asyncio.create_task(
            self._agent_turn(session_id, user_message, history, mode, queue),
            name=f"agent-turn-{session_id}",
        )
        self._active_sessions[session_id] = task

        try:
            while True:
                item = await queue.get()
                if item is _DONE_SENTINEL:
                    break
                yield item
        finally:
            self._active_sessions.pop(session_id, None)
            if not task.done():
                task.cancel()

    def resolve_diff(self, diff_id: str, action: str) -> bool:
        """
        Signal a pending diff approval decision.

        Parameters
        ----------
        diff_id : str
            The diff identifier from the DiffEvent.
        action : str
            "apply" or "reject".

        Returns
        -------
        bool
            True if the diff was found and resolved, False if not found.
        """
        event = self._pending_diffs.get(diff_id)
        if event is None:
            return False
        self._diff_decisions[diff_id] = action
        event.set()
        return True

    def cancel_session(self, session_id: str) -> bool:
        """
        Cancel an in-progress agent turn.

        Returns True if a task was found and cancelled.
        """
        task = self._active_sessions.get(session_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    # ------------------------------------------------------------------
    # Internal: agent turn
    # ------------------------------------------------------------------

    async def _agent_turn(
        self,
        session_id: str,
        user_message: str,
        history: list[dict[str, Any]],
        mode: str,
        queue: asyncio.Queue[dict[str, Any] | None],
    ) -> None:
        """
        Main agentic reasoning loop for one user turn.

        Runs until the model produces a response with no tool calls, then
        puts the done sentinel on the queue.
        """
        try:
            messages = list(history) + [{"role": "user", "content": user_message}]
            system = _build_system_prompt(self._config)
            ha_client = get_ha_client()

            # Built-in HA tools + any external MCP-server tools.
            mcp_manager = get_mcp_manager()
            tools = ALL_TOOLS + (mcp_manager.tools() if mcp_manager else [])

            while True:
                # Collect full response from the backend stream
                content_parts: list[str] = []
                tool_calls: list[dict[str, Any]] = []

                async for chunk in self._backend.chat_stream(messages, system, tools):
                    ctype = chunk.get("type")

                    if ctype == "content":
                        delta = chunk.get("delta", "")
                        content_parts.append(delta)
                        await queue.put(ContentEvent(delta=delta).model_dump())

                    elif ctype == "tool_call":
                        tool_calls.append(chunk)
                        await queue.put(
                            ToolCallEvent(
                                id=chunk["id"],
                                name=chunk["name"],
                                args=chunk.get("args", {}),
                            ).model_dump()
                        )

                    elif ctype == "error":
                        await queue.put(
                            ErrorEvent(message=chunk.get("message", "Unknown error")).model_dump()
                        )

                # If no tool calls, we're done
                if not tool_calls:
                    await queue.put(DoneEvent().model_dump())
                    await queue.put(_DONE_SENTINEL)
                    return

                # Build assistant message to append to history
                assistant_content = "".join(content_parts)
                # Append the assistant turn (with tool_calls embedded for
                # backends that need them in message history)
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    # Use None (not "") when the turn was tool-calls-only: an empty
                    # assistant text block is rejected by Anthropic/others as an
                    # "assistant message prefill" and breaks multi-step tool flows.
                    "content": assistant_content or None,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc.get("args", {})),
                            },
                        }
                        for tc in tool_calls
                    ],
                }
                messages.append(assistant_msg)

                # Execute each tool call and collect results
                for tc in tool_calls:
                    result_str = await self._execute_tool_call(tc, mode, queue, ha_client)

                    # Append tool result to messages
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": tc["name"],
                            "content": result_str,
                        }
                    )

                    await queue.put(
                        ToolResultEvent(
                            id=tc["id"],
                            name=tc["name"],
                            result=result_str,
                            error=False,
                        ).model_dump()
                    )

                # Loop back — send the updated messages to the backend

        except asyncio.CancelledError:
            await queue.put(ErrorEvent(message="Session cancelled.", code="CANCELLED").model_dump())
            await queue.put(_DONE_SENTINEL)
        except Exception as exc:
            log.exception("Agent turn failed for session %s", session_id)
            await queue.put(ErrorEvent(message=str(exc)).model_dump())
            await queue.put(_DONE_SENTINEL)

    # ------------------------------------------------------------------
    # Internal: tool execution
    # ------------------------------------------------------------------

    async def _execute_tool_call(
        self,
        tc: dict[str, Any],
        mode: str,
        queue: asyncio.Queue[dict[str, Any] | None],
        ha_client: Any,
    ) -> str:
        """
        Execute one tool call and return a string result.

        If the tool returns a DiffEvent dict:
          - Emits the diff event to the queue.
          - supervised: pauses and waits for resolve_diff() to be called.
            - "apply": writes the file, returns confirmation.
            - "reject": returns "Rejected".
          - autonomous: writes the file immediately.

        All other exceptions are caught and returned as error strings so
        the agent loop can continue.
        """
        name = tc.get("name", "")
        args = tc.get("args") or {}

        # Route external MCP-server tools to the MCP client manager.
        mcp_manager = get_mcp_manager()
        if mcp_manager is not None and mcp_manager.owns(name):
            try:
                return await mcp_manager.call_tool(name, args)
            except Exception as exc:
                log.warning("MCP tool %r raised: %s", name, exc)
                return f"Error: {exc}"

        try:
            result = await execute_tool(name, args, ha_client, self._config.ha_config_dir)
        except Exception as exc:
            log.warning("Tool %r raised: %s", name, exc)
            return f"Error: {exc}"

        # Check if the result is a DiffEvent dict
        if isinstance(result, dict) and result.get("type") == "diff":
            diff_event = DiffEvent(**result)
            diff_id = diff_event.id
            content = diff_event.content

            # Anchor relative paths (write tools emit paths like
            # "automations/foo.yaml") to the HA config dir, so files land in the
            # HA config — not the process CWD. Update the event before emitting
            # so the frontend and the write agree on the absolute path.
            path = diff_event.path
            if not os.path.isabs(path):
                path = os.path.join(str(self._config.ha_config_dir), path)
                diff_event.path = path

            # Emit the diff event so the frontend can display it
            await queue.put(diff_event.model_dump())

            if mode == "supervised":
                # Pause and wait for the user to approve or reject
                event = asyncio.Event()
                self._pending_diffs[diff_id] = event
                try:
                    await event.wait()
                finally:
                    self._pending_diffs.pop(diff_id, None)

                decision = self._diff_decisions.pop(diff_id, "reject")
                if decision == "apply":
                    await _write_file(path, content)
                    return f"Applied to {path}"
                else:
                    return "Rejected"
            else:
                # autonomous mode: write immediately
                await _write_file(path, content)
                return f"Applied to {path}"

        # Plain string result
        return str(result)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _write_file(path: str, content: str) -> None:
    """Write *content* to *path*, creating parent directories as needed."""
    p = os.path.abspath(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    async with aiofiles.open(p, "w", encoding="utf-8") as fh:
        await fh.write(content)
    log.info("Wrote file: %s (%d bytes)", p, len(content))


def _build_system_prompt(config: AlohaConfig) -> str:
    """
    Construct the system prompt from the base agent instructions plus any
    available HA context snapshot.
    """
    base = (
        "You are Aloha, an AI-powered Home Assistant agent. "
        "You help users control, configure, and automate their Home Assistant setup. "
        "You have access to tools to read entity states, control devices, manage automations, "
        "edit configuration files, and more. "
        "When making configuration changes, always show the user what will change before applying. "
        "For WRITE_CONFIG or DESTRUCTIVE operations, you must use the diff mechanism so the user "
        "can review and approve changes. "
        "Be concise, accurate, and safety-conscious. "
        "Never store or reveal credentials."
    )

    # Append the skill index so the agent knows which playbooks it can pull.
    try:
        from aloha.skills import load_skills, render_skill_index
        index = render_skill_index(load_skills(config.data_dir))
        if index:
            base = f"{base}\n\n--- Skills ---\n{index}"
    except Exception:
        log.debug("Could not build skill index", exc_info=True)

    # Append HA context if available
    try:
        from aloha.context.engine import get_context_engine
        engine = get_context_engine()
        summary = engine.get_system_prompt()
        if summary:
            return f"{base}\n\n--- Home Assistant Context ---\n{summary}"
    except RuntimeError:
        # Context engine not initialised — that is fine, proceed without it
        pass
    except Exception:
        log.debug("Could not retrieve context engine snapshot", exc_info=True)

    return base
