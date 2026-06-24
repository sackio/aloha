"""
aloha/auth/oauth.py

OAuth 2.0 helpers for Aloha.

Supported providers: claude (Anthropic), google (Gemini).

Usage
-----
    from aloha.auth.oauth import start_oauth, handle_callback

    # In GET /auth/{provider}/start:
    redirect_url = start_oauth("google", redirect_base="https://my-aloha.local")
    return RedirectResponse(redirect_url)

    # In GET /auth/{provider}/callback:
    token = await handle_callback("google", code=code, state=state)
    if token:
        config.api_key = token
        config.save()
"""

from __future__ import annotations

import logging
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider OAuth configurations
# ---------------------------------------------------------------------------

OAUTH_CONFIGS: dict[str, dict[str, str]] = {
    "claude": {
        "auth_url": "https://claude.ai/oauth/authorize",
        "token_url": "https://claude.ai/oauth/token",
        # client_id is left empty — Aloha is a self-hosted app;
        # users supply their own credentials if needed.
        "client_id": "",
        "scope": "read write",
    },
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "client_id": "",  # populated from config/env at runtime if available
        "scope": "https://www.googleapis.com/auth/generative-language",
    },
}

# ---------------------------------------------------------------------------
# CSRF state store (in-process; sufficient for single-instance deployment)
# ---------------------------------------------------------------------------

# Maps state token -> provider name
_state_store: dict[str, str] = {}

_STATE_TTL_ENTRIES = 256  # prune after this many entries to bound memory


def _add_state(provider: str) -> str:
    """Generate a CSRF state token and store it."""
    state = secrets.token_urlsafe(32)
    _state_store[state] = provider

    # Prune oldest entries if the store grows too large
    if len(_state_store) > _STATE_TTL_ENTRIES:
        # Remove oldest half
        to_remove = list(_state_store.keys())[:_STATE_TTL_ENTRIES // 2]
        for k in to_remove:
            _state_store.pop(k, None)

    return state


def _consume_state(state: str) -> Optional[str]:
    """Validate and consume a CSRF state token. Returns provider or None."""
    return _state_store.pop(state, None)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def start_oauth(provider: str, redirect_base: str) -> str:
    """
    Build the OAuth authorization URL for the given provider.

    Parameters
    ----------
    provider : str
        One of the keys in OAUTH_CONFIGS ("claude", "google").
    redirect_base : str
        The base URL of the Aloha server (e.g. "http://localhost:7123").
        Used to construct the redirect_uri.

    Returns
    -------
    str
        The full authorization URL to redirect the user to.

    Raises
    ------
    ValueError
        If the provider is not in OAUTH_CONFIGS.
    """
    if provider not in OAUTH_CONFIGS:
        raise ValueError(
            f"Unknown OAuth provider: {provider!r}. "
            f"Supported: {list(OAUTH_CONFIGS.keys())}"
        )

    conf = OAUTH_CONFIGS[provider]
    state = _add_state(provider)
    redirect_uri = f"{redirect_base.rstrip('/')}/auth/{provider}/callback"

    params: dict[str, str] = {
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": conf["scope"],
    }
    if conf.get("client_id"):
        params["client_id"] = conf["client_id"]

    auth_url = conf["auth_url"] + "?" + urlencode(params)
    log.debug("OAuth start for %r: %s", provider, auth_url)
    return auth_url


async def handle_callback(
    provider: str,
    code: str,
    state: str,
    redirect_base: str = "",
) -> Optional[str]:
    """
    Handle the OAuth callback: validate state, exchange code for token.

    Parameters
    ----------
    provider : str
        Provider name from the URL path (must match stored state).
    code : str
        Authorization code from the callback query parameters.
    state : str
        CSRF state token from the callback query parameters.
    redirect_base : str
        Base URL used to reconstruct the redirect_uri.

    Returns
    -------
    str | None
        The access token on success, or None on failure.
    """
    # Validate CSRF state
    stored_provider = _consume_state(state)
    if stored_provider is None:
        log.warning("OAuth callback: unknown or expired state %r", state)
        return None
    if stored_provider != provider:
        log.warning(
            "OAuth callback: state provider mismatch (expected %r, got %r)",
            stored_provider,
            provider,
        )
        return None

    if provider not in OAUTH_CONFIGS:
        log.warning("OAuth callback: unknown provider %r", provider)
        return None

    conf = OAUTH_CONFIGS[provider]
    redirect_uri = f"{redirect_base.rstrip('/')}/auth/{provider}/callback" if redirect_base else ""

    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
    }
    if redirect_uri:
        payload["redirect_uri"] = redirect_uri
    if conf.get("client_id"):
        payload["client_id"] = conf["client_id"]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                conf["token_url"],
                data=payload,
                headers={"Accept": "application/json"},
            )
            r.raise_for_status()
            token_data = r.json()
    except Exception as exc:
        log.warning("OAuth token exchange failed for %r: %s", provider, exc)
        return None

    token = token_data.get("access_token")
    if not token:
        log.warning("OAuth token exchange returned no access_token: %s", token_data)
        return None

    log.info("OAuth token acquired for provider %r", provider)
    return token
