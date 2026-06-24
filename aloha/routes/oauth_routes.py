"""
aloha/routes/oauth_routes.py

OAuth flow endpoints:
  GET /auth/{provider}/start      — initiate OAuth; redirects to provider
  GET /auth/{provider}/callback   — handle OAuth callback; save token; redirect to /
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

log = logging.getLogger(__name__)

router = APIRouter()


def _redirect_base(request: Request) -> str:
    """Derive the public base URL from the incoming request."""
    # Use X-Forwarded-Proto / Host headers if behind a reverse proxy
    scheme = request.headers.get("X-Forwarded-Proto", request.url.scheme)
    host = request.headers.get("X-Forwarded-Host", request.url.netloc)
    return f"{scheme}://{host}"


@router.get("/auth/{provider}/start")
async def oauth_start(provider: str, request: Request) -> RedirectResponse:
    """
    Begin the OAuth flow for the given provider.

    Builds the authorization URL (with CSRF state) and redirects the
    user's browser to the provider's consent page.
    """
    from aloha.auth.oauth import OAUTH_CONFIGS, start_oauth

    if provider not in OAUTH_CONFIGS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown OAuth provider: {provider!r}",
        )

    try:
        redirect_base = _redirect_base(request)
        auth_url = start_oauth(provider, redirect_base)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/auth/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
) -> RedirectResponse:
    """
    Handle the OAuth callback from the provider.

    On success: saves the token to config and redirects to /?setup=complete.
    On failure: redirects to /?oauth_error=<reason>.
    """
    from aloha.auth.oauth import OAUTH_CONFIGS, handle_callback
    from aloha.config import AlohaConfig

    if error:
        log.warning("OAuth callback received error for %r: %s", provider, error)
        return RedirectResponse(url=f"/?oauth_error={error}", status_code=302)

    if not code or not state:
        return RedirectResponse(url="/?oauth_error=missing_code_or_state", status_code=302)

    if provider not in OAUTH_CONFIGS:
        return RedirectResponse(url=f"/?oauth_error=unknown_provider", status_code=302)

    redirect_base = _redirect_base(request)

    token = await handle_callback(
        provider=provider,
        code=code,
        state=state,
        redirect_base=redirect_base,
    )

    if token is None:
        log.warning("OAuth callback: token exchange failed for %r", provider)
        return RedirectResponse(url="/?oauth_error=token_exchange_failed", status_code=302)

    # Persist the token as the API key for the selected provider
    try:
        cfg = AlohaConfig.load()
        cfg.api_key = token

        # Map OAuth provider name to AI provider identifier
        provider_map = {
            "google": "gemini",
            "claude": "anthropic",
        }
        if provider in provider_map:
            cfg.ai_provider = provider_map[provider]  # type: ignore[assignment]

        cfg.save()
        log.info("OAuth token saved for provider %r", provider)
    except Exception as exc:
        log.exception("Failed to save OAuth token for %r", provider)
        return RedirectResponse(
            url=f"/?oauth_error=save_failed&detail={exc}",
            status_code=302,
        )

    return RedirectResponse(url="/?setup=complete", status_code=302)
