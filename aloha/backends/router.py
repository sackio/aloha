"""
aloha/backends/router.py

Factory function that maps an AlohaConfig to the appropriate BaseBackend.

Usage:
    from aloha.backends.router import get_backend
    backend = get_backend(config)
"""

from __future__ import annotations

from aloha.backends.base import BaseBackend


def get_backend(config) -> BaseBackend:  # noqa: ANN001
    """
    Return an instantiated BaseBackend for the given AlohaConfig.

    Parameters
    ----------
    config : AlohaConfig
        The loaded application configuration.

    Returns
    -------
    BaseBackend
        An instance of the appropriate backend subclass.

    Raises
    ------
    ValueError
        If config.ai_provider is not a recognised provider string.
    """
    provider = (config.ai_provider or "").lower()
    api_key = config.api_key or ""
    model = config.model or "auto"

    if provider == "anthropic":
        from aloha.backends.anthropic import AnthropicBackend
        return AnthropicBackend(api_key=api_key, model=model)

    if provider == "openai":
        from aloha.backends.openai_backend import OpenAIBackend
        return OpenAIBackend(api_key=api_key, model=model)

    if provider == "gemini":
        from aloha.backends.gemini import GeminiBackend
        return GeminiBackend(api_key=api_key, model=model)

    if provider == "ollama":
        from aloha.backends.ollama import OllamaBackend
        return OllamaBackend(
            api_key=api_key,
            model=model,
            base_url=config.ollama_url or "",
        )

    if provider == "openrouter":
        from aloha.backends.openrouter import OpenRouterBackend
        return OpenRouterBackend(api_key=api_key, model=model)

    if provider == "groq":
        from aloha.backends.groq import GroqBackend
        return GroqBackend(api_key=api_key, model=model)

    if provider == "aloha":
        # "Aloha managed": route through the hosted relay (OpenAI-compatible).
        # api_key is the user's relay token; no provider key lives on the box.
        from aloha.backends.openai_backend import OpenAIBackend
        managed_model = getattr(config, "managed_model", "") or "anthropic/claude-sonnet-4.6"
        relay = getattr(config, "managed_relay_url", "") or "https://aloha.pushbuild.com"
        return OpenAIBackend(
            api_key=api_key,
            model=(model if model and model != "auto" else managed_model),
            base_url=relay.rstrip("/") + "/v1",
        )

    if provider == "custom":
        from aloha.backends.openai_backend import OpenAIBackend
        return OpenAIBackend(
            api_key=api_key,
            model=model,
            base_url=config.custom_base_url or "",
        )

    raise ValueError(
        f"Unknown AI provider: {config.ai_provider!r}. "
        f"Valid options: anthropic, openai, gemini, ollama, openrouter, groq, custom."
    )
