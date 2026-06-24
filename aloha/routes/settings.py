"""
aloha/routes/settings.py

Settings and provider endpoints:
  GET  /api/settings          — sanitized settings (no plaintext keys)
  POST /api/settings          — update settings (all fields optional)
  GET  /api/providers         — static provider config list
  POST /api/auth/test         — test a provider connection
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from aloha.config import AlohaConfig

log = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Static provider data
# ---------------------------------------------------------------------------

PROVIDERS = [
    {
        "id": "anthropic",
        "name": "Anthropic",
        "requires_api_key": True,
        "models": ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-3-5"],
        "default_model": "claude-opus-4-5",
        "wizard_steps": [
            {
                "step": 1,
                "title": "Create an Anthropic account",
                "instruction": "Visit console.anthropic.com and sign up for an account if you don't have one.",
                "url": "https://console.anthropic.com/",
                "image_alt": "Anthropic Console sign-up page",
            },
            {
                "step": 2,
                "title": "Navigate to API Keys",
                "instruction": "In the Anthropic Console, click on 'API Keys' in the left sidebar.",
                "url": "https://console.anthropic.com/settings/keys",
                "image_alt": "API Keys section in Anthropic Console",
            },
            {
                "step": 3,
                "title": "Create a new API key",
                "instruction": "Click 'Create Key', give it a name (e.g. 'Aloha'), and copy the key.",
                "action": "copy_key",
            },
            {
                "step": 4,
                "title": "Add billing",
                "instruction": "Make sure you have a payment method added at console.anthropic.com/settings/billing.",
                "url": "https://console.anthropic.com/settings/billing",
                "image_alt": "Billing settings page",
            },
            {
                "step": 5,
                "title": "Enter your API key",
                "instruction": "Paste your Anthropic API key in the field below.",
                "action": "enter_key",
            },
        ],
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "requires_api_key": True,
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "default_model": "gpt-4o",
        "wizard_steps": [
            {
                "step": 1,
                "title": "Create an OpenAI account",
                "instruction": "Visit platform.openai.com and sign up or log in.",
                "url": "https://platform.openai.com/",
                "image_alt": "OpenAI Platform sign-up page",
            },
            {
                "step": 2,
                "title": "Navigate to API Keys",
                "instruction": "Go to platform.openai.com/api-keys.",
                "url": "https://platform.openai.com/api-keys",
                "image_alt": "OpenAI API Keys page",
            },
            {
                "step": 3,
                "title": "Create a new secret key",
                "instruction": "Click 'Create new secret key', give it a name, and copy it immediately.",
                "action": "copy_key",
            },
            {
                "step": 4,
                "title": "Add billing credits",
                "instruction": "Ensure you have credits at platform.openai.com/settings/organization/billing.",
                "url": "https://platform.openai.com/settings/organization/billing",
                "image_alt": "OpenAI billing page",
            },
            {
                "step": 5,
                "title": "Enter your API key",
                "instruction": "Paste your OpenAI API key in the field below.",
                "action": "enter_key",
            },
        ],
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "requires_api_key": True,
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "default_model": "gemini-2.0-flash",
        "wizard_steps": [
            {
                "step": 1,
                "title": "Open Google AI Studio",
                "instruction": "Visit aistudio.google.com and sign in with your Google account.",
                "url": "https://aistudio.google.com/",
                "image_alt": "Google AI Studio home page",
            },
            {
                "step": 2,
                "title": "Get an API key",
                "instruction": "Click 'Get API key' then 'Create API key in new project'.",
                "url": "https://aistudio.google.com/app/apikey",
                "image_alt": "Get API key button in AI Studio",
            },
            {
                "step": 3,
                "title": "Copy your API key",
                "instruction": "Copy the API key shown on screen.",
                "action": "copy_key",
            },
            {
                "step": 4,
                "title": "Enter your API key",
                "instruction": "Paste your Gemini API key in the field below.",
                "action": "enter_key",
            },
        ],
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "requires_api_key": True,
        "models": ["anthropic/claude-opus-4-5", "openai/gpt-4o", "google/gemini-2.0-flash"],
        "default_model": "anthropic/claude-opus-4-5",
        "wizard_steps": [
            {
                "step": 1,
                "title": "Create an OpenRouter account",
                "instruction": "Visit openrouter.ai and sign up.",
                "url": "https://openrouter.ai/",
                "image_alt": "OpenRouter sign-up page",
            },
            {
                "step": 2,
                "title": "Get your API key",
                "instruction": "Go to openrouter.ai/keys and create a new key.",
                "url": "https://openrouter.ai/keys",
                "image_alt": "OpenRouter API keys page",
            },
            {
                "step": 3,
                "title": "Add credits",
                "instruction": "Add credits at openrouter.ai/credits to use paid models.",
                "url": "https://openrouter.ai/credits",
                "image_alt": "OpenRouter credits page",
            },
            {
                "step": 4,
                "title": "Enter your API key",
                "instruction": "Paste your OpenRouter API key in the field below.",
                "action": "enter_key",
            },
        ],
    },
    {
        "id": "groq",
        "name": "Groq",
        "requires_api_key": True,
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "default_model": "llama-3.3-70b-versatile",
        "wizard_steps": [
            {
                "step": 1,
                "title": "Create a Groq account",
                "instruction": "Visit console.groq.com and sign up.",
                "url": "https://console.groq.com/",
                "image_alt": "Groq Console sign-up page",
            },
            {
                "step": 2,
                "title": "Create an API key",
                "instruction": "Go to console.groq.com/keys and create a new key.",
                "url": "https://console.groq.com/keys",
                "image_alt": "Groq API keys page",
            },
            {
                "step": 3,
                "title": "Enter your API key",
                "instruction": "Paste your Groq API key in the field below.",
                "action": "enter_key",
            },
        ],
    },
    {
        "id": "ollama",
        "name": "Ollama (local)",
        "requires_api_key": False,
        "models": [],
        "default_model": "",
        "wizard_steps": [
            {
                "step": 1,
                "title": "Install Ollama",
                "instruction": "Download and install Ollama from ollama.com.",
                "url": "https://ollama.com/",
                "image_alt": "Ollama download page",
            },
            {
                "step": 2,
                "title": "Pull a model",
                "instruction": "Run: ollama pull llama3.2 (or any supported model).",
                "action": "run_command",
            },
        ],
    },
    {
        "id": "custom",
        "name": "Custom (OpenAI-compatible)",
        "requires_api_key": False,
        "models": [],
        "default_model": "",
        "wizard_steps": [
            {
                "step": 1,
                "title": "Enter your base URL",
                "instruction": "Provide the base URL for your OpenAI-compatible API endpoint (e.g. http://localhost:1234/v1).",
                "action": "enter_url",
            },
            {
                "step": 2,
                "title": "Enter your API key (optional)",
                "instruction": "If your endpoint requires authentication, enter the API key.",
                "action": "enter_key",
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SettingsUpdate(BaseModel):
    """All fields optional — only supplied fields are updated."""

    ai_provider: Optional[Literal["anthropic", "openai", "gemini", "ollama", "openrouter", "groq", "custom"]] = None
    model: Optional[str] = None
    safety_mode: Optional[Literal["strict", "normal", "permissive"]] = None
    ha_url: Optional[str] = None
    context_refresh_minutes: Optional[int] = None
    ollama_url: Optional[str] = None
    custom_base_url: Optional[str] = None
    setup_complete: Optional[bool] = None
    # Credentials — written encrypted, never returned
    api_key: Optional[str] = None
    ha_token: Optional[str] = None


class AuthTestRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    ollama_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("/api/settings")
async def get_settings() -> JSONResponse:
    """Return sanitized settings — no plaintext credentials."""
    cfg = AlohaConfig.load()
    return JSONResponse(
        {
            "ai_provider": cfg.ai_provider,
            "model": cfg.model,
            "safety_mode": cfg.safety_mode,
            "ha_url": cfg.ha_url,
            "context_refresh_minutes": cfg.context_refresh_minutes,
            "mode": cfg.mode,
            "port": cfg.port,
            "ollama_url": cfg.ollama_url,
            "custom_base_url": cfg.custom_base_url,
            "setup_complete": cfg.setup_complete,
            "has_api_key": cfg.api_key is not None,
            "has_ha_token": cfg.ha_token is not None,
        }
    )


@router.post("/api/settings")
async def post_settings(body: SettingsUpdate) -> JSONResponse:
    """Update settings. Only supplied (non-None) fields are applied."""
    cfg = AlohaConfig.load()

    if body.ai_provider is not None:
        cfg.ai_provider = body.ai_provider
    if body.model is not None:
        cfg.model = body.model
    if body.safety_mode is not None:
        cfg.safety_mode = body.safety_mode
    if body.ha_url is not None:
        cfg.ha_url = body.ha_url
    if body.context_refresh_minutes is not None:
        cfg.context_refresh_minutes = body.context_refresh_minutes
    if body.ollama_url is not None:
        cfg.ollama_url = body.ollama_url
    if body.custom_base_url is not None:
        cfg.custom_base_url = body.custom_base_url
    if body.setup_complete is not None:
        cfg.setup_complete = body.setup_complete

    # Credentials use the encrypted setter
    if body.api_key is not None:
        cfg.api_key = body.api_key
    if body.ha_token is not None:
        cfg.ha_token = body.ha_token

    cfg.save()
    return JSONResponse({"ok": True})


@router.get("/api/providers")
async def get_providers() -> JSONResponse:
    """Return static provider config list (including wizard steps)."""
    return JSONResponse(PROVIDERS)


@router.post("/api/auth/test")
async def auth_test(body: AuthTestRequest) -> JSONResponse:
    """
    Instantiate the requested backend and call test_connection().
    Returns {ok, model} on success or {ok, error} on failure.
    """
    provider = body.provider.lower()
    api_key = body.api_key or ""
    model = body.model or "auto"
    base_url = body.base_url or ""
    ollama_url = body.ollama_url or ""

    try:
        if provider == "anthropic":
            from aloha.backends.anthropic import AnthropicBackend
            backend = AnthropicBackend(api_key=api_key, model=model)

        elif provider == "openai":
            from aloha.backends.openai_backend import OpenAIBackend
            backend = OpenAIBackend(api_key=api_key, model=model)

        elif provider == "gemini":
            from aloha.backends.gemini import GeminiBackend
            backend = GeminiBackend(api_key=api_key, model=model)

        elif provider == "ollama":
            from aloha.backends.ollama import OllamaBackend
            backend = OllamaBackend(api_key=api_key, model=model, base_url=ollama_url or "http://localhost:11434")

        elif provider == "openrouter":
            from aloha.backends.openrouter import OpenRouterBackend
            backend = OpenRouterBackend(api_key=api_key, model=model)

        elif provider == "groq":
            from aloha.backends.groq import GroqBackend
            backend = GroqBackend(api_key=api_key, model=model)

        elif provider == "custom":
            from aloha.backends.openai_backend import OpenAIBackend
            backend = OpenAIBackend(api_key=api_key, model=model, base_url=base_url)

        else:
            return JSONResponse({"ok": False, "error": f"Unknown provider: {provider!r}"})

        success, message = await backend.test_connection()
        if success:
            return JSONResponse({"ok": True, "model": message})
        else:
            return JSONResponse({"ok": False, "error": message})

    except Exception as exc:
        log.warning("Auth test for %r failed: %s", provider, exc)
        return JSONResponse({"ok": False, "error": str(exc)})
