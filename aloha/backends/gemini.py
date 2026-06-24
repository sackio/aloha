"""
aloha/backends/gemini.py

Google Gemini backend for the Aloha agent.
Uses google.generativeai (google-generativeai SDK).

Function calling is handled via the Gemini FunctionDeclaration / Tool API.
"""

from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

import google.generativeai as genai
from google.generativeai.types import AsyncGenerateContentResponse

from aloha.agent.types import ToolDef
from aloha.backends.base import BaseBackend


def _convert_tools(tools: list[ToolDef]) -> list[genai.protos.Tool] | None:
    """Convert ToolDef list to Gemini Tool / FunctionDeclaration format."""
    if not tools:
        return None

    declarations = []
    for t in tools:
        # Gemini expects a JSON-schema-like dict for parameters
        params = t.parameters if t.parameters else {
            "type": "object",
            "properties": {},
        }
        declarations.append(
            genai.protos.FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        k: _schema_to_gemini(v)
                        for k, v in params.get("properties", {}).items()
                    },
                    required=params.get("required", []),
                ),
            )
        )

    return [genai.protos.Tool(function_declarations=declarations)]


def _schema_to_gemini(schema: dict) -> genai.protos.Schema:
    """Recursively convert a JSON Schema dict to a Gemini Schema proto."""
    type_map = {
        "string": genai.protos.Type.STRING,
        "number": genai.protos.Type.NUMBER,
        "integer": genai.protos.Type.INTEGER,
        "boolean": genai.protos.Type.BOOLEAN,
        "array": genai.protos.Type.ARRAY,
        "object": genai.protos.Type.OBJECT,
    }
    gemini_type = type_map.get(schema.get("type", "string"), genai.protos.Type.STRING)

    kwargs: dict = {
        "type": gemini_type,
        "description": schema.get("description", ""),
    }

    if gemini_type == genai.protos.Type.OBJECT and "properties" in schema:
        kwargs["properties"] = {
            k: _schema_to_gemini(v) for k, v in schema["properties"].items()
        }
        if "required" in schema:
            kwargs["required"] = schema["required"]

    if gemini_type == genai.protos.Type.ARRAY and "items" in schema:
        kwargs["items"] = _schema_to_gemini(schema["items"])

    if "enum" in schema:
        kwargs["enum"] = schema["enum"]

    return genai.protos.Schema(**kwargs)


def _normalize_messages(
    messages: list[dict],
    system: str,
) -> tuple[str, list[genai.protos.Content]]:
    """
    Convert OpenAI-style messages to Gemini Content list.

    Returns (system_instruction, contents).

    Gemini uses:
      - role "user" for user and tool-result turns
      - role "model" for assistant turns
    Tool results are wrapped in FunctionResponse parts.
    """
    contents: list[genai.protos.Content] = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "user":
            contents.append(
                genai.protos.Content(
                    role="user",
                    parts=[genai.protos.Part(text=content)],
                )
            )

        elif role == "assistant":
            tool_calls = msg.get("tool_calls") or []
            parts: list[genai.protos.Part] = []
            if content:
                parts.append(genai.protos.Part(text=content))
            for tc in tool_calls:
                fn = tc.get("function", {})
                args_raw = fn.get("arguments", "{}")
                if isinstance(args_raw, str):
                    try:
                        args_raw = json.loads(args_raw)
                    except Exception:
                        args_raw = {}
                parts.append(
                    genai.protos.Part(
                        function_call=genai.protos.FunctionCall(
                            name=fn.get("name", ""),
                            args=args_raw,
                        )
                    )
                )
            if not parts:
                parts.append(genai.protos.Part(text=content or ""))
            contents.append(genai.protos.Content(role="model", parts=parts))

        elif role == "tool":
            # Emit a user-role FunctionResponse part
            try:
                result_data = json.loads(content) if content else {}
            except Exception:
                result_data = {"result": content}
            contents.append(
                genai.protos.Content(
                    role="user",
                    parts=[
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=msg.get("tool_name") or msg.get("name", ""),
                                response={"result": result_data},
                            )
                        )
                    ],
                )
            )

    return system, contents


class GeminiBackend(BaseBackend):
    """Google Gemini backend using google.generativeai."""

    def __init__(
        self,
        api_key: str,
        model: str = "auto",
        base_url: str = "",
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url)
        genai.configure(api_key=api_key)

    # ------------------------------------------------------------------
    # BaseBackend properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "Google Gemini"

    @property
    def default_model(self) -> str:
        return "gemini-2.0-flash"

    @property
    def available_models(self) -> list[str]:
        return ["gemini-2.0-flash", "gemini-2.5-pro"]

    # ------------------------------------------------------------------
    # chat_stream
    # ------------------------------------------------------------------

    async def chat_stream(
        self,
        messages: list[dict],
        system: str,
        tools: list[ToolDef],
    ) -> AsyncIterator[dict]:
        model_id = self.model if self.model and self.model != "auto" else self.default_model

        system_instruction, contents = _normalize_messages(messages, system)
        gemini_tools = _convert_tools(tools)

        generation_config = genai.GenerationConfig(
            max_output_tokens=8192,
        )

        model_kwargs: dict = {
            "generation_config": generation_config,
        }
        if system_instruction:
            model_kwargs["system_instruction"] = system_instruction
        if gemini_tools:
            model_kwargs["tools"] = gemini_tools

        client = genai.GenerativeModel(model_name=model_id, **model_kwargs)

        response: AsyncGenerateContentResponse = await client.generate_content_async(
            contents,
            stream=True,
        )

        async for chunk in response:
            if not hasattr(chunk, "candidates") or not chunk.candidates:
                continue

            for candidate in chunk.candidates:
                if not hasattr(candidate, "content") or not candidate.content:
                    continue

                for part in candidate.content.parts:
                    # Text delta
                    if hasattr(part, "text") and part.text:
                        yield {"type": "content", "delta": part.text}

                    # Function call
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        args = dict(fc.args) if fc.args else {}
                        yield {
                            "type": "tool_call",
                            "id": f"tc_{uuid.uuid4().hex[:12]}",
                            "name": fc.name,
                            "args": args,
                        }

    # ------------------------------------------------------------------
    # test_connection
    # ------------------------------------------------------------------

    async def test_connection(self) -> tuple[bool, str]:
        try:
            models = []
            for m in genai.list_models():
                models.append(m.name)
            return (True, "Connected to Google Gemini")
        except Exception as exc:
            return (False, str(exc))
