"""
aloha/routes/mcp_keys_route.py

Manage MCP access credentials (key + secret) from the box UI. The secret is
returned once, at mint/regenerate; afterwards only a prefix is shown.

  GET    /api/mcp-keys                  — list keys (no secrets)
  POST   /api/mcp-keys      {name?}     — mint a key -> {id, secret, name}
  POST   /api/mcp-keys/{id}/regenerate  — rotate the secret -> {id, secret}
  DELETE /api/mcp-keys/{id}             — terminate a key
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from aloha.config import AlohaConfig
from aloha.mcp import auth

router = APIRouter(prefix="/api/mcp-keys", tags=["mcp-keys"])


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class MintRequest(BaseModel):
    name: str = ""


@router.get("")
async def list_keys() -> JSONResponse:
    cfg = AlohaConfig.load()
    return JSONResponse(auth.list_keys(cfg.data_dir))


@router.post("")
async def mint_key(req: MintRequest) -> JSONResponse:
    cfg = AlohaConfig.load()
    return JSONResponse(auth.mint(cfg.data_dir, req.name, now=_now()))


@router.post("/{key_id}/regenerate")
async def regenerate_key(key_id: str) -> JSONResponse:
    cfg = AlohaConfig.load()
    out = auth.regenerate(cfg.data_dir, key_id)
    if out is None:
        raise HTTPException(status_code=404, detail="key not found")
    return JSONResponse(out)


@router.delete("/{key_id}")
async def revoke_key(key_id: str) -> JSONResponse:
    cfg = AlohaConfig.load()
    if not auth.revoke(cfg.data_dir, key_id):
        raise HTTPException(status_code=404, detail="key not found")
    return JSONResponse({"ok": True})
