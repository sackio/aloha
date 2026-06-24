"""
aloha/backends/anthropic.py

Anthropic (Claude) backend for the Aloha agent.
Uses the anthropic SDK with streaming via client.messages.stream().

Message normalization:
  - role "tool" is converted to role "user" with a tool_result content block,
    as required by the Anthropic Messages API.
"""

from __future__ import annotations

import uuid
from typing import AsyncIterator

from anthropic import AsyncAnthropic

from aloha.agent.types import ToolDef
from aloha.backends.base import BaseBackend


def _convert_tools(tools: list[ToolDef]) -> list[dict]:
    """Convert ToolDef list to Anthropic tools format."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.parameters if t.parameters else {
                "type": "object",
                "properties": {},
            },
        }
        for t in tools
    ]


def _normalize_messages(messages: list[dict]) -> list[dict]:
    """
    Convert OpenAI-style messages to Anthropic Messages API format.

    The main transformation: role "tool" becomes role "user" with a
    tool_result content block.  Adjacent tool results are merged into a
    single "user" message, as the Anthropic API does not allow consecutive
    same-role messages.
    """
    normalized: list[dict] = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")

        if role == "tool":
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": msg.get("tool_call_id", ""),
                "content": content,
            }
            # Merge into the previous user message if it already holds
            # tool_result blocks, otherwise create a new one.
            if (
                normalized
                and normalized[-1]["role"] == "user"
                and isinstance(normalized[-1]["content"], list)
                and any(
                    b.get("type") == "tool_result"
                    for b in normalized[-1]["content"]
                )
            ):
                normalized[-1]["content"].append(tool_result_block)
            else:
                normalized.append({"role": "user", "content": [tool_result_block]})

        elif role == "assistant":
            # If the assistant message has tool_calls attached (OpenAI format),
            # convert them to tool_use content blocks.
            tool_calls = msg.get("tool_calls") or []
            if tool_calls:
                blocks: list[dict] = []
                if content:
                    blocks.append({"type": "text", "text": content})
                for tc in tool_calls:
                    import json as _json
                    args = tc.get("function", {}).get("arguments", "{}")
                    if isinstance(args, str):
                        try:
                            args = _json.loads(args)
                        except Exception:
                            args = {}
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc.get("id", f"tu_{uuid.uuid4().hex[:12]}"),
                            "name": tc.get("function", {}).get("name", ""),
                            "input": args,
                        }
                    )
                normalized.append({"role": "assistant", "content": blocks})
            else:
                normalized.append({"role": "assistant", "content": content or ""})

        else:
            # "user" role — pass through as-is.
            normalized.append({"role": "user", "content": content or ""})

    return normalized


class AnthropicBackend(BaseBackend):
    """Claude backend using the Anthropic SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "auto",
        base_url: str = "",
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url)
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncAnthropic(**kwargs)

    # ------------------------------------------------------------------
    # BaseBackend properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "Anthropic"

    @property
    def default_model(self) -> str:
        return "claude-sonnet-4-6"

    @property
    def available_models(self) -> list[str]:
        return [
            "claude-sonnet-4-6",
            "claude-opus-4-8",
            "claude-haiku-4-5-20251001",
        ]

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

        anthropic_messages = _normalize_messages(messages)
        anthropic_tools = _convert_tools(tools)

        kwargs: dict = {
            "model": model,
            "max_tokens": 8192,
            "system": system,
            "messages": anthropic_messages,
        }
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        # Accumulate tool_use blocks keyed by id so we can emit them
        # once the stream finishes delivering each block.
        pending_tool_uses: dict[str, dict] = {}

        async with self._client.messages.stream(**kwargs) as stream:
            current_tool_id: str | None = None
            current_tool_name: str | None = None
            current_tool_input_json: str = ""

            async for event in stream:
                event_type = getattr(event, "type", None)

                if event_type == "content_block_start":
                    block = getattr(event, "content_block", None)
                    if block is None:
                        continue
                    block_type = getattr(block, "type", None)
                    if block_type == "tool_use":
                        current_tool_id = getattr(block, "id", f"tu_{uuid.uuid4().hex[:12]}")
                        current_tool_name = getattr(block, "name", "")
                        current_tool_input_json = ""

                elif event_type == "content_block_delta":
                    delta = getattr(event, "delta", None)
                    if delta is None:
                        continue
                    delta_type = getattr(delta, "type", None)

                    if delta_type == "text_delta":
                        text = getattr(delta, "text", "")
                        if text:
                            yield {"type": "content", "delta": text}

                    elif delta_type == "input_json_delta":
                        partial = getattr(delta, "partial_json", "")
                        current_tool_input_json += partial

                elif event_type == "content_block_stop":
                    # If we were accumulating a tool_use block, emit it now.
                    if current_tool_id is not None:
                        import json as _json
                        try:
                            args = _json.loads(current_tool_input_json) if current_tool_input_json else {}
                        except Exception:
                            args = {}
                        yield {
                            "type": "tool_call",
                            "id": current_tool_id,
                            "name": current_tool_name or "",
                            "args": args,
                        }
                        current_tool_id = None
                        current_tool_name = None
                        current_tool_input_json = ""

    # ------------------------------------------------------------------
    # test_connection
    # ------------------------------------------------------------------

    async def test_connection(self) -> tuple[bool, str]:
        try:
            model = self.model if self.model and self.model != "auto" else self.default_model
            response = await self._client.messages.create(
                model=model,
                max_tokens=16,
                messages=[{"role": "user", "content": "hi"}],
            )
            return (True, "Connected to Claude")
        except Exception as exc:
            return (False, str(exc))
