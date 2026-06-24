"""
aloha/backends/groq.py

Groq backend for the Aloha agent.
Extends OpenAIBackend with Groq's base URL.

Groq exposes an OpenAI-compatible API at https://api.groq.com/openai/v1
with extremely fast inference via custom hardware.
"""

from __future__ import annotations

from aloha.backends.openai_backend import OpenAIBackend

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqBackend(OpenAIBackend):
    """Groq backend (OpenAI-compatible, ultra-low latency)."""

    def __init__(
        self,
        api_key: str,
        model: str = "auto",
        base_url: str = "",
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url or _GROQ_BASE_URL,
        )

    # ------------------------------------------------------------------
    # BaseBackend properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "Groq"

    @property
    def default_model(self) -> str:
        return "llama-3.1-70b-versatile"

    @property
    def available_models(self) -> list[str]:
        return [
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]
