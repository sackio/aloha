"""
aloha/routes/relay_account.py

Drive the $1/mo Aloha relay subscription from the box UI. The box proxies the
hosted relay's account + billing endpoints server-side and stores the account
token (config.relay_token) — separate from the AI api_key, so a bring-your-own-
key user can still subscribe to the relay tunnel.

  POST /api/relay/signup   {email, password}  -> create account, store token
  POST /api/relay/login    {email, password}  -> log in, store token
  POST /api/relay/subscribe                    -> Stripe checkout URL ($1/mo)
  GET  /api/relay/status                       -> {has_account, entitled}
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from aloha.config import AlohaConfig

router = APIRouter(prefix="/api/relay", tags=["relay"])


class Credentials(BaseModel):
    email: str
    password: str


def _base(cfg: AlohaConfig) -> str:
    return (getattr(cfg, "managed_relay_url", "") or "https://aloha.pushbuild.com").rstrip("/")


async def _auth(path: str, creds: Credentials) -> JSONResponse:
    cfg = AlohaConfig.load()
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(f"{_base(cfg)}{path}",
                             json={"email": creds.email, "password": creds.password})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"could not reach Aloha service: {exc}")
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
        except Exception:
            detail = r.text[:200]
        raise HTTPException(status_code=r.status_code, detail=detail or "authentication failed")
    data = r.json()
    token = data.get("token")
    if not token:
        raise HTTPException(status_code=502, detail="Aloha service did not return a token")
    cfg.relay_token = token   # encrypted; does NOT change the AI provider
    cfg.save()
    return JSONResponse({"ok": True, "email": data.get("email")})


@router.post("/signup")
async def relay_signup(creds: Credentials) -> JSONResponse:
    return await _auth("/auth/signup", creds)


@router.post("/login")
async def relay_login(creds: Credentials) -> JSONResponse:
    return await _auth("/auth/login", creds)


@router.post("/subscribe")
async def relay_subscribe() -> JSONResponse:
    """Start the $1/mo relay subscription — returns a Stripe checkout URL."""
    cfg = AlohaConfig.load()
    token = cfg.relay_token or (cfg.api_key if cfg.ai_provider == "aloha" else "")
    if not token:
        raise HTTPException(status_code=401, detail="sign in to your Aloha account first")
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(f"{_base(cfg)}/billing/subscribe-relay",
                             headers={"Authorization": f"Bearer {token}"})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"could not reach Aloha service: {exc}")
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
        except Exception:
            detail = r.text[:200]
        raise HTTPException(status_code=r.status_code, detail=detail or "could not start checkout")
    return JSONResponse(r.json())


@router.get("/status")
async def relay_status() -> JSONResponse:
    cfg = AlohaConfig.load()
    token = cfg.relay_token or (cfg.api_key if cfg.ai_provider == "aloha" else "")
    if not token:
        return JSONResponse({"has_account": False, "entitled": False})
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{_base(cfg)}/account/relay-status",
                            headers={"Authorization": f"Bearer {token}"})
        entitled = bool(r.json().get("entitled")) if r.status_code < 400 else False
    except Exception:
        entitled = False
    return JSONResponse({"has_account": True, "entitled": entitled})
