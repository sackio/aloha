"""
aloha/bootstrap.py

bootstrap(config) — bring up the HA connection at startup.

Flow
----
1. Poll GET /api/ every 2 s until HA responds (timeout 120 s).
2. If config.ha_token is set, validate it and return an HAClient.
3. Otherwise attempt trusted-network token creation:
     a. POST /auth/login_flow  (homeassistant provider)
     b. POST /auth/login_flow/{flow_id}  (trusted network step)
     c. POST /auth/token  (exchange for short-lived access token)
     d. POST /api/auth/long_lived_access_token (permanent LLAT via REST)
4. Persist the new token to config.
5. Return init_ha_client(url, token).

Raises
------
RuntimeError
    If HA is unreachable within the timeout, or if token creation fails
    and no token is configured.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from aloha.config import AlohaConfig
from aloha.ha.client import HAClient, init_ha_client

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def bootstrap(config: AlohaConfig) -> HAClient:
    """
    Ensure HA is reachable, acquire a valid token, and return an HAClient.

    Parameters
    ----------
    config : AlohaConfig
        Loaded config object.  If ``config.ha_token`` is set it will be
        tested first.  If token creation succeeds, the new token is saved
        back to *config* and ``config.save()`` is called.

    Returns
    -------
    HAClient
        A ready-to-use, token-authenticated async HA client (singleton).
    """
    ha_url = config.ha_url.rstrip("/")

    # Step 1: wait for HA to be reachable
    await _wait_for_ha(ha_url, timeout=120)

    # Step 2: if a stored token exists, test it
    existing_token = config.ha_token
    if existing_token:
        client = HAClient(base_url=ha_url, token=existing_token)
        if await client.ping():
            log.info("Existing HA token validated. Connected to %s", ha_url)
            return init_ha_client(ha_url, existing_token)
        else:
            log.warning(
                "Stored HA token failed validation; attempting trusted-network auth."
            )
        await client.close()

    # Step 3: attempt trusted-network token creation
    token = await _create_trusted_network_token(ha_url)
    if token is None:
        raise RuntimeError(
            "Could not obtain a Home Assistant token. "
            "Set ALOHA_HA_TOKEN or run Aloha from a trusted network."
        )

    # Step 4: persist the new token
    config.ha_token = token
    try:
        config.save()
    except Exception:
        log.warning("Could not save config after token creation", exc_info=True)

    log.info("Trusted-network token acquired and saved. Connected to %s", ha_url)
    return init_ha_client(ha_url, token)


# ---------------------------------------------------------------------------
# HA availability polling
# ---------------------------------------------------------------------------


async def _wait_for_ha(ha_url: str, timeout: int = 120) -> None:
    """
    Poll ``GET {ha_url}/api/`` every 2 s until HA responds with 2xx/401/403,
    or until *timeout* seconds have elapsed.

    Any HTTP response (even 401) is treated as "HA is up"; we just need the
    process to be accepting connections.

    Raises
    ------
    RuntimeError
        If HA is still unreachable after *timeout* seconds.
    """
    log.info("Waiting for Home Assistant at %s (timeout %ds)…", ha_url, timeout)
    deadline = asyncio.get_event_loop().time() + timeout

    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            try:
                r = await client.get(f"{ha_url}/api/")
                # Any HTTP response means HA is up (401 = token needed, still up)
                log.info("Home Assistant responded with HTTP %d.", r.status_code)
                return
            except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError):
                pass  # still starting

            if asyncio.get_event_loop().time() >= deadline:
                raise RuntimeError(
                    f"Home Assistant at {ha_url} did not become available within {timeout}s."
                )

            await asyncio.sleep(2)


# ---------------------------------------------------------------------------
# Trusted-network authentication flow
# ---------------------------------------------------------------------------


async def _create_trusted_network_token(ha_url: str) -> Optional[str]:
    """
    Attempt to obtain a long-lived access token via the HA trusted-network
    auth provider.

    Returns the token string on success, or None on failure.

    HA trusted-network auth flow (REST):
        POST /auth/login_flow       — init flow
        POST /auth/login_flow/{id} — provide username (trusted-network step)
        POST /auth/token            — exchange flow result for access token
        WS   /api/websocket         — create a long-lived access token

    We fall back to a short-lived token if LLAT creation fails.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        # --- Step 3a: initialise login flow ---
        try:
            r = await client.post(
                f"{ha_url}/auth/login_flow",
                json={"client_id": ha_url + "/", "handler": ["homeassistant", None]},
            )
            r.raise_for_status()
            flow_data = r.json()
        except Exception as exc:
            log.debug("Could not start HA auth flow: %s", exc)
            return None

        flow_id = flow_data.get("flow_id")
        if not flow_id:
            log.debug("No flow_id in auth response: %s", flow_data)
            return None

        # --- Step 3b: submit credentials for trusted-network provider ---
        # For the trusted-network provider the step type is "form" with
        # a "username" field.  We use "homeassistant" as the username.
        try:
            r2 = await client.post(
                f"{ha_url}/auth/login_flow/{flow_id}",
                json={"client_id": ha_url + "/", "username": "homeassistant"},
            )
            r2.raise_for_status()
            step_data = r2.json()
        except Exception as exc:
            log.debug("Auth flow step failed: %s", exc)
            return None

        # result should be {"type": "create_entry", "result": "<auth_code>"}
        if step_data.get("type") != "create_entry":
            log.debug("Auth flow step returned: %s", step_data)
            return None

        auth_code: Optional[str] = step_data.get("result")
        if not auth_code:
            log.debug("No auth code in flow result: %s", step_data)
            return None

        # --- Step 3c: exchange auth code for access token ---
        try:
            r3 = await client.post(
                f"{ha_url}/auth/token",
                data={
                    "client_id": ha_url + "/",
                    "grant_type": "authorization_code",
                    "code": auth_code,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            r3.raise_for_status()
            token_data = r3.json()
        except Exception as exc:
            log.debug("Token exchange failed: %s", exc)
            return None

        access_token: Optional[str] = token_data.get("access_token")
        if not access_token:
            log.debug("No access_token in token response: %s", token_data)
            return None

        # --- Step 3d: create a permanent long-lived access token ---
        # The REST endpoint POST /api/auth/long_lived_access_token is
        # available in some HA versions; fall back to the short-lived token
        # if it is not available.
        llat = await _create_llat_via_rest(ha_url, access_token, client)
        return llat if llat else access_token


async def _create_llat_via_rest(
    ha_url: str,
    access_token: str,
    client: httpx.AsyncClient,
) -> Optional[str]:
    """
    Attempt to create a long-lived access token via the HA REST API.

    POST /api/auth/long_lived_access_token
    Authorization: Bearer <access_token>
    {"client_name": "Aloha", "lifespan": 3650}

    Returns the long-lived token string, or None if the endpoint is
    unavailable or the call fails.
    """
    try:
        r = await client.post(
            f"{ha_url}/api/auth/long_lived_access_token",
            json={"client_name": "Aloha", "lifespan": 3650},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        if r.status_code == 200:
            body = r.json()
            # Some HA versions return the token directly as a string
            if isinstance(body, str):
                return body
            return body.get("token") or body.get("access_token")
        log.debug("LLAT endpoint returned %d: %s", r.status_code, r.text[:200])
        return None
    except Exception as exc:
        log.debug("LLAT creation failed: %s", exc)
        return None
