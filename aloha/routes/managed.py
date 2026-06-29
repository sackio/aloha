"""
aloha/routes/managed.py

"Aloha managed" tier — the box signs the user in/up against the hosted relay
(aloha.pushbuild.com) and stores the returned relay token. After that the box's
agent talks to the relay (provider="aloha") with that token; no provider API key
ever lives on the box.

The box proxies the auth server-side (no CORS, box controls token storage).
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from aloha.config import AlohaConfig

log = logging.getLogger(__name__)

router = APIRouter()


class ManagedCredentials(BaseModel):
    email: str
    password: str


def _relay_base(cfg: AlohaConfig) -> str:
    return (getattr(cfg, "managed_relay_url", "") or "https://aloha.pushbuild.com").rstrip("/")


async def _auth_and_store(path: str, creds: ManagedCredentials) -> JSONResponse:
    cfg = AlohaConfig.load()
    base = _relay_base(cfg)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{base}{path}",
                json={"email": creds.email, "password": creds.password},
            )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"could not reach Aloha service: {exc}")

    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
        except Exception:
            detail = r.text[:200]
        raise HTTPException(status_code=r.status_code, detail=detail or "authentication failed")

    data = r.json()
    token = data.get("token")
    status = data.get("status", "active")
    if not token:
        raise HTTPException(status_code=502, detail="Aloha service did not return a token")

    # Switch the box onto the managed tier and store the relay token.
    cfg.ai_provider = "aloha"
    cfg.model = getattr(cfg, "managed_model", "") or "anthropic/claude-sonnet-4.6"
    cfg.api_key = token                      # encrypted at rest
    cfg.setup_complete = (status == "active")  # pending beta accounts wait for activation
    cfg.save()

    return JSONResponse({"ok": True, "status": status, "email": data.get("email")})


@router.post("/api/managed/signup")
async def managed_signup(creds: ManagedCredentials) -> JSONResponse:
    return await _auth_and_store("/auth/signup", creds)


@router.post("/api/managed/login")
async def managed_login(creds: ManagedCredentials) -> JSONResponse:
    return await _auth_and_store("/auth/login", creds)


@router.get("/api/managed/usage")
async def managed_usage() -> JSONResponse:
    """Proxy the relay's usage/balance for the box's usage meter."""
    cfg = AlohaConfig.load()
    if cfg.ai_provider != "aloha" or not cfg.api_key:
        raise HTTPException(status_code=400, detail="not on the managed tier")
    base = _relay_base(cfg)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{base}/account/usage",
                headers={"Authorization": f"Bearer {cfg.api_key}"},
            )
        return JSONResponse(r.json(), status_code=r.status_code)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
