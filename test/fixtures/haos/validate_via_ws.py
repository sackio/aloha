#!/usr/bin/env python3
"""
validate_via_ws.py — validate the real supervisor.py tools against a live HAOS,
from OUTSIDE the VM, without installing the add-on.

The Supervisor API is normally only reachable from inside an add-on container
(where a SUPERVISOR_TOKEN is injected). But HA Core — which holds its own
Supervisor token — proxies Supervisor calls for admins over the authenticated
WebSocket `supervisor/api` command (this is how the frontend's Supervisor panel
works). We reuse that: an admin LLAT + the WS proxy gives us the real Supervisor
API over the wire.

This harness monkeypatches `aloha.mcp.tools.supervisor._sup` to route through
the WS proxy instead of `http://supervisor`, then runs the *actual*
`execute_supervisor_tool` dispatch — so we validate the real tool code (path
construction, response unwrapping, output formatting) against a real Supervisor,
not a mock.

    python3 validate_via_ws.py --url http://localhost:8125 --token <admin-LLAT>
    # or: TOKEN in ./.ha_token / $HA_TOKEN

Note: this validates the endpoint *contract*. The only thing it does NOT exercise
is SUPERVISOR_TOKEN injection into the add-on container (trivial env plumbing,
covered by haos-addon/config.yaml + run.sh). For a full in-container run use
validate_supervisor.py inside the installed add-on instead.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import websockets

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import aloha.mcp.tools.supervisor as sup  # noqa: E402


class WSProxy:
    """Routes Supervisor REST calls through Core's authenticated WS proxy."""

    def __init__(self, ws):
        self.ws = ws
        self._id = 1

    async def call(self, method: str, path: str, json_body: dict | None = None) -> dict:
        self._id += 1
        msg = {"id": self._id, "type": "supervisor/api", "endpoint": path, "method": method.lower()}
        if json_body is not None:
            msg["data"] = json_body
        await self.ws.send(json.dumps(msg))
        # The WS may interleave events; read until we get our id.
        while True:
            resp = json.loads(await self.ws.recv())
            if resp.get("id") == self._id:
                break
        if not resp.get("success"):
            err = resp.get("error", {})
            raise RuntimeError(f"Supervisor {method} {path} -> {err.get('code')}: {err.get('message')}")
        # supervisor.py's _data() expects {"data": ...}; the WS proxy already
        # returns the unwrapped payload in "result".
        return {"result": "ok", "data": resp["result"]}


READ_TOOLS = [
    ("get_environment", {}),
    ("get_supervisor_info", {}),
    ("get_core_info", {}),
    ("get_os_info", {}),
    ("check_updates", {}),
    ("list_addons", {}),
    ("search_addons", {"query": "terminal"}),
    ("list_backups", {}),
]


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("HA_URL", "http://localhost:8125"))
    ap.add_argument("--token", default=os.environ.get("HA_TOKEN", ""))
    ap.add_argument("--with-backup", action="store_true", help="also create+list a real backup")
    args = ap.parse_args()

    token = args.token
    if not token:
        tf = os.path.join(os.path.dirname(__file__), ".ha_token")
        if os.path.exists(tf):
            token = open(tf).read().strip()
    if not token:
        print("No admin token. Pass --token, set HA_TOKEN, or drop it in .ha_token.", file=sys.stderr)
        return 2

    ws_url = args.url.rstrip("/").replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
    async with websockets.connect(ws_url, max_size=None) as ws:
        await ws.recv()  # auth_required
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(await ws.recv()).get("type") != "auth_ok":
            print("WS auth failed — token not accepted.", file=sys.stderr)
            return 2

        proxy = WSProxy(ws)
        # Route the real tool code through the WS proxy + force the supervisor gate open.
        sup._sup = proxy.call
        sup.has_supervisor = lambda: True

        print("== Supervisor tools vs live HAOS (via Core WS proxy) ==")
        results = []
        tools = list(READ_TOOLS)

        # Discover an installed add-on slug for the by-slug read tools.
        # NOTE: get_addon_logs is intentionally excluded here — the Supervisor
        # logs endpoint returns *plain text*, which the JSON-only WS proxy can't
        # carry (it surfaces as unknown_error). The tool itself handles text via
        # its {"raw": r.text} fallback on a direct call; that path is covered by
        # the in-container validate_supervisor.py, not this outside-the-VM one.
        addons_out = await sup.execute_supervisor_tool("list_addons", {})
        try:
            addons = json.loads(addons_out)
            if addons:
                slug = addons[0]["slug"]
                tools += [("get_addon_info", {"slug": slug})]
                print(f"  (note: get_addon_logs skipped — text response can't cross the JSON WS proxy; "
                      f"use validate_supervisor.py in-container to cover it)")
        except Exception:
            pass

        if args.with_backup:
            tools += [("create_backup", {"name": "aloha-fixture-test"}), ("list_backups", {})]

        for name, a in tools:
            try:
                out = await sup.execute_supervisor_tool(name, a)
                ok = not out.lower().startswith("error")
            except Exception as exc:  # noqa: BLE001
                out, ok = f"raised {type(exc).__name__}: {exc}", False
            print(f"  {'✓' if ok else '✗'} {name}: {out.replace(chr(10), ' ')[:110]}")
            results.append(ok)

        passed = sum(results)
        print(f"\n{passed}/{len(results)} tool calls succeeded against HAOS {args.url}.")
        return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
