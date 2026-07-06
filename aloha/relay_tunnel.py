"""
aloha/relay_tunnel.py

Box side of the MCP reverse-tunnel. Opens an outbound WebSocket to the Aloha
relay and forwards inbound requests to the box's own local MCP endpoint, so a
box behind home NAT gets a stable public MCP URL with no port-forwarding.

See aloha-server/tunnel.py for the relay side and the wire protocol.

Public API:
    creds = ensure_registered(relay_url, data_dir)      # {box_id, token}
    public_url(relay_url, box_id)                        # the URL users paste
    await run_tunnel(relay_url, box_id, token, local_base)   # long-running

Typically the app starts run_tunnel() as a background task when the tunnel is
enabled, and shows public_url() in the UI.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
from pathlib import Path

import httpx
import websockets

log = logging.getLogger("aloha.tunnel")

_HOP = {"host", "content-length", "transfer-encoding", "connection", "keep-alive",
        "proxy-authenticate", "proxy-authorization", "te", "trailers", "upgrade"}


def _creds_path(data_dir: Path) -> Path:
    return Path(data_dir) / "tunnel.json"


def load_creds(data_dir: Path) -> dict | None:
    try:
        return json.loads(_creds_path(data_dir).read_text())
    except Exception:
        return None


def ensure_registered(relay_url: str, data_dir: Path) -> dict:
    """Return persisted {box_id, token}, registering with the relay if needed."""
    existing = load_creds(data_dir)
    if existing and existing.get("box_id") and existing.get("token"):
        return existing
    r = httpx.post(f"{relay_url.rstrip('/')}/tunnel/register", timeout=30)
    r.raise_for_status()
    creds = r.json()
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    _creds_path(data_dir).write_text(json.dumps(creds))
    return creds


def public_url(relay_url: str, box_id: str) -> str:
    return f"{relay_url.rstrip('/')}/box/{box_id}/mcp"


def _ws_url(relay_url: str, box_id: str, token: str) -> str:
    base = relay_url.rstrip("/")
    if base.startswith("https://"):
        base = "wss://" + base[len("https://"):]
    elif base.startswith("http://"):
        base = "ws://" + base[len("http://"):]
    return f"{base}/tunnel/{box_id}?token={token}"


async def _handle_req(ws, send_lock: asyncio.Lock, frame: dict, local_base: str,
                      tasks: dict) -> None:
    rid = frame["id"]
    method = frame["method"]
    query = frame.get("query") or ""
    url = f"{local_base.rstrip('/')}{frame['path']}" + (f"?{query}" if query else "")
    headers = {k: v for k, v in (frame.get("headers") or {}).items()
               if k.lower() not in _HOP}
    body = base64.b64decode(frame["body"]) if frame.get("body") else None

    async def send(obj: dict) -> None:
        async with send_lock:
            await ws.send(json.dumps(obj))

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(method, url, headers=headers, content=body) as resp:
                await send({"t": "head", "id": rid, "status": resp.status_code,
                            "headers": dict(resp.headers)})
                async for chunk in resp.aiter_raw():
                    if chunk:
                        await send({"t": "chunk", "id": rid,
                                    "data": base64.b64encode(chunk).decode()})
                await send({"t": "end", "id": rid})
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        with contextlib.suppress(Exception):
            await send({"t": "err", "id": rid, "msg": str(exc)})
    finally:
        tasks.pop(rid, None)


async def run_tunnel(relay_url: str, box_id: str, token: str, local_base: str) -> None:
    """Maintain the tunnel forever, reconnecting with backoff."""
    ws_url = _ws_url(relay_url, box_id, token)
    backoff = 1.0
    while True:
        try:
            async with websockets.connect(ws_url, max_size=None, ping_interval=20,
                                           ping_timeout=20) as ws:
                log.info("tunnel connected: %s", public_url(relay_url, box_id))
                backoff = 1.0
                send_lock = asyncio.Lock()
                tasks: dict[int, asyncio.Task] = {}
                async for raw in ws:
                    frame = json.loads(raw)
                    t = frame.get("t")
                    if t == "req":
                        tasks[frame["id"]] = asyncio.create_task(
                            _handle_req(ws, send_lock, frame, local_base, tasks))
                    elif t == "cancel":
                        task = tasks.get(frame["id"])
                        if task:
                            task.cancel()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning("tunnel disconnected (%s); retrying in %.0fs", exc, backoff)
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30.0)
