"""
aloha/backends/ollama.py

Ollama backend for the Aloha agent.
Uses httpx directly (no Ollama SDK dependency).

Streams via POST /api/chat with NDJSON response parsing.
Supports native Ollama tools format when the model supports it;
falls back to structured JSON extraction from the prompt for models
that do not declare tool support.
"""

from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

import httpx

from aloha.agent.types import ToolDef
from aloha.backends.base import BaseBackend

_TOOL_FALLBACK_SUFFIX = """

When you need to call a tool, respond with a JSON block on its own line using this format:
{"tool_call": {"name": "<tool_name>", "arguments": {<args>}}}

Only include one tool call per response. Do not include any other text on the same line as the JSON block.
"""


def _convert_tools_native(tools: list[ToolDef]) -> list[dict]:
    """Convert ToolDef list to Ollama native tools format."""
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


def _extract_tool_call_from_text(text: str) -> dict | None:
    """
    Attempt to extract a structured tool call JSON from text.
    Returns a dict with keys 'name' and 'arguments', or None if not found.
    """
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
            if "tool_call" in obj:
                tc = obj["tool_call"]
                return {
                    "name": tc.get("name", ""),
                    "arguments": tc.get("arguments", {}),
                }
        except Exception:
            continue
    return None


class OllamaBackend(BaseBackend):
    """Ollama local backend using httpx."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "auto",
        base_url: str = "",
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url)
        self._base_url = (base_url or "http://localhost:11434").rstrip("/")

    # ------------------------------------------------------------------
    # BaseBackend properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "Ollama"

    @property
    def default_model(self) -> str:
        return "qwen2.5-coder:7b"

    @property
    def available_models(self) -> list[str]:
        return [
            "qwen2.5-coder:7b",
            "llama3.1:8b",
            "mistral:7b",
            "codellama:13b",
            "qwen2.5:14b",
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

        # Build message list — Ollama uses the same role convention as OpenAI
        ollama_messages: list[dict] = []
        if system:
            ollama_messages.append({"role": "system", "content": system})

        # Detect whether we will use native tools or fallback mode.
        # We attempt native tools; if the API returns an error about tools
        # not being supported, we fall back automatically in a second pass.
        use_native_tools = bool(tools)
        native_tools = _convert_tools_native(tools) if use_native_tools else []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "tool":
                # Represent tool results as a user message in fallback mode,
                # or as a "tool" message in native mode.
                if use_native_tools:
                    ollama_messages.append(
                        {
                            "role": "tool",
                            "content": content,
                        }
                    )
                else:
                    ollama_messages.append(
                        {
                            "role": "user",
                            "content": f"Tool result: {content}",
                        }
                    )
            else:
                ollama_messages.append({"role": role, "content": content})

        # If in fallback mode, append tool usage instructions to system prompt
        if not use_native_tools and tools:
            # Inject fallback instructions into the last system message or prepend
            if ollama_messages and ollama_messages[0]["role"] == "system":
                ollama_messages[0]["content"] += _TOOL_FALLBACK_SUFFIX
            else:
                ollama_messages.insert(
                    0,
                    {"role": "system", "content": _TOOL_FALLBACK_SUFFIX.strip()},
                )

        payload: dict = {
            "model": model,
            "messages": ollama_messages,
            "stream": True,
        }
        if use_native_tools and native_tools:
            payload["tools"] = native_tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/chat",
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    accumulated_text = ""
                    tool_calls_emitted = False

                    async for raw_line in response.aiter_lines():
                        raw_line = raw_line.strip()
                        if not raw_line:
                            continue

                        try:
                            data = json.loads(raw_line)
                        except Exception:
                            continue

                        if "error" in data:
                            # If the model does not support tools, retry without them.
                            if use_native_tools and "tool" in data["error"].lower():
                                # Fall back: recurse without native tools
                                async for chunk in self._stream_fallback(
                                    messages, system, tools, model
                                ):
                                    yield chunk
                                return
                            yield {"type": "error", "message": data["error"]}
                            return

                        msg_data = data.get("message", {})

                        # Native tool calls
                        if "tool_calls" in msg_data and msg_data["tool_calls"]:
                            for tc in msg_data["tool_calls"]:
                                fn = tc.get("function", {})
                                args = fn.get("arguments", {})
                                if isinstance(args, str):
                                    try:
                                        args = json.loads(args)
                                    except Exception:
                                        args = {}
                                yield {
                                    "type": "tool_call",
                                    "id": f"tc_{uuid.uuid4().hex[:12]}",
                                    "name": fn.get("name", ""),
                                    "args": args,
                                }
                            tool_calls_emitted = True

                        # Text content
                        content_delta = msg_data.get("content", "")
                        if content_delta:
                            accumulated_text += content_delta
                            yield {"type": "content", "delta": content_delta}

                        # Check for done
                        if data.get("done", False):
                            # Fallback: extract tool calls from accumulated text
                            if not tool_calls_emitted and tools:
                                tc = _extract_tool_call_from_text(accumulated_text)
                                if tc:
                                    yield {
                                        "type": "tool_call",
                                        "id": f"tc_{uuid.uuid4().hex[:12]}",
                                        "name": tc["name"],
                                        "args": tc["arguments"],
                                    }
                            break

            except httpx.HTTPStatusError as exc:
                yield {"type": "error", "message": f"Ollama HTTP error: {exc}"}
            except httpx.ConnectError as exc:
                yield {"type": "error", "message": f"Ollama connection refused at {self._base_url}: {exc}"}

    async def _stream_fallback(
        self,
        messages: list[dict],
        system: str,
        tools: list[ToolDef],
        model: str,
    ) -> AsyncIterator[dict]:
        """
        Retry the request without native tools, using prompt-injection
        for structured tool extraction.
        """
        ollama_messages: list[dict] = []
        fallback_system = (system + "\n" + _TOOL_FALLBACK_SUFFIX).strip()
        if fallback_system:
            ollama_messages.append({"role": "system", "content": fallback_system})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "tool":
                ollama_messages.append({"role": "user", "content": f"Tool result: {content}"})
            else:
                ollama_messages.append({"role": role, "content": content})

        payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": True,
        }

        accumulated_text = ""

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for raw_line in response.aiter_lines():
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    try:
                        data = json.loads(raw_line)
                    except Exception:
                        continue

                    msg_data = data.get("message", {})
                    content_delta = msg_data.get("content", "")
                    if content_delta:
                        accumulated_text += content_delta
                        yield {"type": "content", "delta": content_delta}

                    if data.get("done", False):
                        tc = _extract_tool_call_from_text(accumulated_text)
                        if tc:
                            yield {
                                "type": "tool_call",
                                "id": f"tc_{uuid.uuid4().hex[:12]}",
                                "name": tc["name"],
                                "args": tc["arguments"],
                            }
                        break

    # ------------------------------------------------------------------
    # test_connection
    # ------------------------------------------------------------------

    async def test_connection(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self._base_url}/api/version")
                response.raise_for_status()
                version = response.json().get("version", "unknown")
                return (True, f"Connected to Ollama {version}")
        except httpx.ConnectError as exc:
            return (False, f"Ollama not reachable at {self._base_url}: {exc}")
        except Exception as exc:
            return (False, str(exc))
