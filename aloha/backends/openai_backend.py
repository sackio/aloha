"""
aloha/backends/openai_backend.py

OpenAI-compatible backend for the Aloha agent.
Named openai_backend.py (not openai.py) to avoid shadowing the openai package.

Supports any OpenAI-compatible endpoint via custom base_url, making this
backend reusable by OpenRouterBackend and GroqBackend via subclassing.
"""

from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

from openai import AsyncOpenAI

from aloha.agent.types import ToolDef
from aloha.backends.base import BaseBackend


def _convert_tools(tools: list[ToolDef]) -> list[dict]:
    """Convert ToolDef list to OpenAI function-calling tools format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters if t.parameters else {
                    "type": "object",
                    "properties": {},
                },
            },
        }
        for t in tools
    ]


class OpenAIBackend(BaseBackend):
    """OpenAI (and compatible) backend using the openai SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "auto",
        base_url: str = "",
        extra_headers: dict | None = None,
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url)
        self._extra_headers = extra_headers or {}

        kwargs: dict = {"api_key": api_key or "none"}
        if base_url:
            kwargs["base_url"] = base_url
        if self._extra_headers:
            kwargs["default_headers"] = self._extra_headers

        self._client = AsyncOpenAI(**kwargs)

    # ------------------------------------------------------------------
    # BaseBackend properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def default_model(self) -> str:
        return "gpt-4o"

    @property
    def available_models(self) -> list[str]:
        return ["gpt-4o", "gpt-4o-mini", "o3", "o4-mini"]

    # ------------------------------------------------------------------
    # chat_stream
    # ------------------------------------------------------------------

    async def chat_stream(
        self,
        messages: list[dict],
        system: str,
        tools: list[ToolDef],
    ) -> AsyncIterator[dict]:
        model = self.model if self.model and self.model != "auto" else self.default_model

        # Prepend system message
        openai_messages: list[dict] = []
        if system:
            openai_messages.append({"role": "system", "content": system})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "tool":
                openai_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg.get("tool_call_id", ""),
                        "name": msg.get("tool_name") or msg.get("name", ""),
                        "content": content,
                    }
                )
            else:
                openai_messages.append({"role": role, "content": content})

        kwargs: dict = {
            "model": model,
            "messages": openai_messages,
            "stream": True,
        }

        oai_tools = _convert_tools(tools)
        if oai_tools:
            kwargs["tools"] = oai_tools
            kwargs["tool_choice"] = "auto"

        # Accumulate tool call deltas keyed by index
        tool_calls_acc: dict[int, dict] = {}

        async with await self._client.chat.completions.create(**kwargs) as stream:
            async for chunk in stream:
                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                # Text content
                if delta.content:
                    yield {"type": "content", "delta": delta.content}

                # Tool call deltas
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id": tc_delta.id or f"tc_{uuid.uuid4().hex[:12]}",
                                "name": "",
                                "arguments": "",
                            }

                        if tc_delta.id:
                            tool_calls_acc[idx]["id"] = tc_delta.id

                        if tc_delta.function:
                            if tc_delta.function.name:
                                tool_calls_acc[idx]["name"] += tc_delta.function.name
                            if tc_delta.function.arguments:
                                tool_calls_acc[idx]["arguments"] += tc_delta.function.arguments

                # Emit completed tool calls when the choice finishes
                if choice.finish_reason in ("tool_calls", "stop") and tool_calls_acc:
                    for tc in tool_calls_acc.values():
                        try:
                            args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                        except Exception:
                            args = {}
                        yield {
                            "type": "tool_call",
                            "id": tc["id"],
                            "name": tc["name"],
                            "args": args,
                        }
                    tool_calls_acc.clear()

        # Safety: emit any remaining accumulated tool calls
        for tc in tool_calls_acc.values():
            try:
                args = json.loads(tc["arguments"]) if tc["arguments"] else {}
            except Exception:
                args = {}
            yield {
                "type": "tool_call",
                "id": tc["id"],
                "name": tc["name"],
                "args": args,
            }

    # ------------------------------------------------------------------
    # test_connection
    # ------------------------------------------------------------------

    async def test_connection(self) -> tuple[bool, str]:
        try:
            model = self.model if self.model and self.model != "auto" else self.default_model
            await self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=8,
            )
            return (True, f"Connected to {self.name} ({model})")
        except Exception as exc:
            return (False, str(exc))
