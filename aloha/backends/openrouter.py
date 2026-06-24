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
_HTTP_REFERER = "https://github.com/aloha-ha/aloha"
_X_TITLE = "Aloha — Home Assistant AI Agent"


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
        return "auto"

    @property
    def available_models(self) -> list[str]:
        # OpenRouter exposes hundreds of models; return common ones.
        # The "auto" special value lets OpenRouter pick the best model.
        return [
            "auto",
            "anthropic/claude-sonnet-4-6",
            "anthropic/claude-opus-4-8",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "google/gemini-2.0-flash",
            "meta-llama/llama-3.1-70b-instruct",
            "mistralai/mixtral-8x7b-instruct",
        ]
