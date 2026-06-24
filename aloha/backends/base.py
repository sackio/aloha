"""
aloha/backends/base.py

Abstract base class that all AI provider backends must implement.
Each backend translates the internal message/tool format into provider-
specific API calls and yields a normalized stream of dicts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from aloha.agent.types import ToolDef


class BaseBackend(ABC):
    """
    Abstract AI backend.

    Subclasses: AnthropicBackend, OpenAIBackend, GeminiBackend, OllamaBackend.

    Yielded dict shapes from chat_stream():

        Text delta:
            {"type": "content", "delta": str}

        Tool call (complete, not streamed incrementally):
            {"type": "tool_call", "id": str, "name": str, "args": dict}

        Error (non-fatal; stream may continue):
            {"type": "error", "message": str}
    """

    def __init__(
        self,
        api_key: str,
        model: str = "auto",
        base_url: str = "",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    # ---------------------------------------------------------------------------
    # Abstract methods — every subclass must implement these
    # ---------------------------------------------------------------------------

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        system: str,
        tools: list[ToolDef],
    ) -> AsyncIterator[dict]:
        """
        Stream a chat completion.

        Parameters
        ----------
        messages : list[dict]
            Conversation history in the OpenAI messages format:
              [{"role": "user"|"assistant"|"tool", "content": str, ...}]
            Tool result messages carry additional keys:
              {"role": "tool", "tool_call_id": str, "name": str, "content": str}
        system : str
            System prompt.  Passed separately because some APIs (Anthropic)
            treat system as a top-level parameter, not a message.
        tools : list[ToolDef]
            Tool definitions to advertise to the model.

        Yields
        ------
        dict
            See class docstring for yielded shapes.
        """
        ...

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """
        Validate credentials and connectivity.

        Returns
        -------
        (True, model_name)   on success
        (False, error_msg)   on failure
        """
        ...

    # ---------------------------------------------------------------------------
    # Abstract properties
    # ---------------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name, e.g. 'Anthropic'."""
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model ID to use when model='auto'."""
        ...

    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        """
        Ordered list of supported model IDs, best-first.
        Used to populate the model picker in the setup wizard.
        """
        ...
