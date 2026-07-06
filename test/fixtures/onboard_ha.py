#!/usr/bin/env python3
"""
onboard_ha.py — drive a fresh Home Assistant instance through onboarding and
mint a long-lived access token (LLAT), non-interactively.

Shared by the docker and haos test fixtures. A brand-new HA (Core or HAOS) boots
into an onboarding wizard; this script completes just enough of it to get a
working owner account + an LLAT the Aloha agent can authenticate with.

Flow (all against the HA REST/WS API):
  1. POST /api/onboarding/users        -> create owner, returns an auth_code
  2. POST /auth/token                  -> exchange auth_code for access+refresh
  3. POST /api/onboarding/core_config  -> mark core step done (best-effort)
  4. POST /api/onboarding/analytics    -> opt out (best-effort)
  5. POST /api/onboarding/integration  -> finish wizard (best-effort)
  6. WS  auth/long_lived_access_token  -> mint the LLAT

Prints the LLAT to stdout (and nothing else on success), so callers can do:
    TOKEN=$(python3 onboard_ha.py --url http://localhost:8124)

Usage:
    python3 onboard_ha.py [--url URL] [--user NAME] [--pass PASS] [--name FULL]

Idempotency: if HA is already onboarded, step 1 returns HTTP 403/404 with an
"onboarding" error; pass --user/--pass matching the existing owner and the
script will fall back to a normal password login before minting the LLAT.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import httpx
import websockets

CLIENT_ID = "http://aloha-test.local/"


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


async def _exchange_password(base: str, username: str, password: str) -> str:
    """Fallback: normal user/pass login → access_token (for already-onboarded HA)."""
    async with httpx.AsyncClient(base_url=base, timeout=30) as c:
        # 1. start a login flow
        r = await c.post("/auth/login_flow", json={
            "client_id": CLIENT_ID,
            "handler": ["homeassistant", None],
            "redirect_uri": CLIENT_ID,
        })
        r.raise_for_status()
        flow_id = r.json()["flow_id"]
        # 2. submit credentials
        r = await c.post(f"/auth/login_flow/{flow_id}", json={
            "client_id": CLIENT_ID,
            "username": username,
            "password": password,
        })
        r.raise_for_status()
        result = r.json()
        if result.get("type") != "create_entry":
            raise RuntimeError(f"login failed: {json.dumps(result)[:300]}")
        code = result["result"]
        # 3. exchange the auth code
        r = await c.post("/auth/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": CLIENT_ID,
        })
        r.raise_for_status()
        return r.json()["access_token"]


async def _onboard(base: str, username: str, password: str, name: str) -> str:
    """Create the owner via onboarding → access_token. Raises if already onboarded."""
    async with httpx.AsyncClient(base_url=base, timeout=30) as c:
        r = await c.post("/api/onboarding/users", json={
            "client_id": CLIENT_ID,
            "name": name,
            "username": username,
            "password": password,
            "language": "en",
        })
        if r.status_code >= 400:
            raise RuntimeError(f"onboarding/users HTTP {r.status_code}: {r.text[:200]}")
        auth_code = r.json()["auth_code"]

        r = await c.post("/auth/token", data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": CLIENT_ID,
        })
        r.raise_for_status()
        access = r.json()["access_token"]

        # Best-effort: advance the remaining wizard steps so HA lands on the
        # normal UI. Failures here are non-fatal for token minting.
        h = {"Authorization": f"Bearer {access}"}
        for path, body in [
            ("/api/onboarding/core_config", {}),
            ("/api/onboarding/analytics", {}),
            ("/api/onboarding/integration", {"client_id": CLIENT_ID, "redirect_uri": CLIENT_ID}),
        ]:
            try:
                await c.post(path, headers=h, json=body)
            except Exception as exc:  # noqa: BLE001
                _log(f"  (onboarding step {path} skipped: {exc})")
        return access


async def _mint_llat(base: str, access_token: str, client_name: str) -> str:
    """Use the WebSocket API to mint a 10-year long-lived access token."""
    ws_url = base.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
    async with websockets.connect(ws_url, max_size=None) as ws:
        await ws.recv()  # auth_required
        await ws.send(json.dumps({"type": "auth", "access_token": access_token}))
        auth_result = json.loads(await ws.recv())
        if auth_result.get("type") != "auth_ok":
            raise RuntimeError(f"WS auth failed: {auth_result}")
        await ws.send(json.dumps({
            "id": 1,
            "type": "auth/long_lived_access_token",
            "client_name": client_name,
            "lifespan": 3650,  # days
        }))
        result = json.loads(await ws.recv())
        if not result.get("success"):
            raise RuntimeError(f"LLAT mint failed: {json.dumps(result)[:300]}")
        return result["result"]


async def main() -> int:
    ap = argparse.ArgumentParser(description="Onboard HA + mint an LLAT.")
    ap.add_argument("--url", default="http://localhost:8124", help="HA base URL")
    ap.add_argument("--user", default="aloha", help="owner username")
    ap.add_argument("--pass", dest="password", default="aloha-test", help="owner password")
    ap.add_argument("--name", default="Aloha Test", help="owner full name")
    ap.add_argument("--client-name", default="aloha-test-fixture", help="LLAT client name")
    args = ap.parse_args()

    base = args.url.rstrip("/")

    try:
        access = await _onboard(base, args.user, args.password, args.name)
        _log("Onboarded fresh HA owner.")
    except RuntimeError as exc:
        _log(f"Onboarding not available ({exc}); trying password login…")
        access = await _exchange_password(base, args.user, args.password)
        _log("Logged in to already-onboarded HA.")

    llat = await _mint_llat(base, access, args.client_name)
    _log("Minted long-lived access token.")
    print(llat)  # ONLY the token on stdout
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
