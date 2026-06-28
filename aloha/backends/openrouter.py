"""
aloha/backends/openrouter.py

OpenRouter backend for the Aloha agent.
Extends OpenAIBackend with OpenRouter's base URL and required HTTP headers.

OpenRouter exposes an OpenAI-compatible API at https://openrouter.ai/api/v1.
It requires two additional headers:
  HTTP-Referer  — the URL of the application using the API
  X-Title       — a human-readable name for the application
"""

from __future__ import annotations

from aloha.backends.openai_backend import OpenAIBackend

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_HTTP_REFERER = "https://github.com/sackio/aloha"
_X_TITLE = "Aloha - Home Assistant AI Agent"


class OpenRouterBackend(OpenAIBackend):
    """OpenRouter backend (OpenAI-compatible with extra headers)."""

    def __init__(
        self,
        api_key: str,
        model: str = "auto",
        base_url: str = "",
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url or _OPENROUTER_BASE_URL,
            extra_headers={
                "HTTP-Referer": _HTTP_REFERER,
                "X-Title": _X_TITLE,
            },
        )

    # ------------------------------------------------------------------
    # BaseBackend properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "OpenRouter"

    @property
    def default_model(self) -> str:
        # A strong, tool-capable default (OpenRouter slugs use dots, e.g. 4.6).
        return "anthropic/claude-sonnet-4.6"

    @property
    def available_models(self) -> list[str]:
        # OpenRouter exposes hundreds of models; return common tool-capable ones.
        return [
            "anthropic/claude-sonnet-4.6",
            "anthropic/claude-opus-4.8",
            "anthropic/claude-haiku-4.5",
            "openai/gpt-5.1",
            "openai/gpt-4.1",
            "google/gemini-2.5-pro",
            "google/gemini-2.5-flash",
            "meta-llama/llama-3.3-70b-instruct",
        ]
