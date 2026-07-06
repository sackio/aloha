"""
aloha/routes/public_url_route.py

Manage the box's public MCP URL (relay / cloudflared / ngrok).

  GET  /api/public-url            -> current provider, url, online, error
  POST /api/public-url            -> {provider, ngrok_authtoken?}: (re)start + persist
  POST /api/public-url/disable    -> tear down + persist provider=none
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/public-url", tags=["public-url"])


class EnableRequest(BaseModel):
    provider: str  # relay | cloudflared | ngrok
    ngrok_authtoken: str | None = None


@router.get("")
async def get_status(request: Request) -> JSONResponse:
    mgr = request.app.state.public_url_manager
    return JSONResponse(mgr.status())


@router.post("")
async def enable(req: EnableRequest, request: Request) -> JSONResponse:
    config = request.app.state.config
    mgr = request.app.state.public_url_manager

    if req.ngrok_authtoken is not None:
        config.ngrok_authtoken = req.ngrok_authtoken
    config.public_url_provider = req.provider if req.provider in (
        "relay", "cloudflared", "ngrok") else "none"

    status = await mgr.start(config.public_url_provider, config.ngrok_authtoken or "")

    # Only persist the provider if it actually started (else fall back to none).
    if status.get("error"):
        config.public_url_provider = "none"
    try:
        config.save()
    except Exception:
        pass
    return JSONResponse(status)


@router.post("/disable")
async def disable(request: Request) -> JSONResponse:
    config = request.app.state.config
    mgr = request.app.state.public_url_manager
    await mgr.stop()
    config.public_url_provider = "none"
    try:
        config.save()
    except Exception:
        pass
    return JSONResponse(mgr.status())
