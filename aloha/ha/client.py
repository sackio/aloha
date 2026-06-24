"""
aloha/ha/client.py

Async HTTP client for the Home Assistant REST API.

Singleton usage:
    from aloha.ha.client import get_ha_client
    client = get_ha_client()

Initialisation (call once at startup):
    from aloha.ha.client import init_ha_client
    init_ha_client(ha_url="http://localhost:8123", ha_token="Bearer ...")
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional
from urllib.parse import urlparse

import httpx
import websockets
import websockets.exceptions

logger = logging.getLogger(__name__)


class HAConnectionError(Exception):
    """Raised when a connection to Home Assistant cannot be established."""


class HAClient:
    """
    Async wrapper around the Home Assistant REST API.

    All methods raise httpx.HTTPStatusError on 4xx/5xx responses unless
    otherwise documented. The caller is responsible for handling those errors.
    """

    def __init__(self, base_url: str, token: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._headers,
                timeout=self._timeout,
            )
        return self._client

    def _ws_url(self) -> str:
        """Convert http(s)://host to ws(s)://host for the WebSocket endpoint."""
        parsed = urlparse(self._base_url)
        if parsed.scheme == "https":
            ws_scheme = "wss"
        else:
            ws_scheme = "ws"
        return f"{ws_scheme}://{parsed.netloc}/api/websocket"

    # ---------------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------------

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ---------------------------------------------------------------------------
    # Health / discovery
    # ---------------------------------------------------------------------------

    async def ping(self) -> bool:
        """Return True if HA is reachable and the token is valid."""
        try:
            c = await self._get_client()
            r = await c.get("/api/")
            r.raise_for_status()
            return True
        except Exception:
            return False

    async def get_version(self) -> str:
        """Return the HA version string."""
        c = await self._get_client()
        r = await c.get("/api/")
        r.raise_for_status()
        return r.json().get("version", "unknown")

    async def get_system_health(self) -> dict[str, Any]:
        """Return the /api/system_health payload."""
        c = await self._get_client()
        r = await c.get("/api/system_health")
        r.raise_for_status()
        return r.json()

    # ---------------------------------------------------------------------------
    # States
    # ---------------------------------------------------------------------------

    async def get_states(self) -> list[dict[str, Any]]:
        """Return all entity states."""
        c = await self._get_client()
        r = await c.get("/api/states")
        r.raise_for_status()
        return r.json()

    async def get_state(self, entity_id: str) -> dict[str, Any]:
        """Return state for a single entity."""
        c = await self._get_client()
        r = await c.get(f"/api/states/{entity_id}")
        r.raise_for_status()
        return r.json()

    async def subscribe_state_changes(
        self,
        callback: Callable[[dict[str, Any]], Any],
        entity_ids: Optional[list[str]] = None,
    ) -> None:
        """
        Open a WebSocket to the HA WebSocket API and call `callback` for each
        state_changed event.  Reconnects automatically on disconnect using
        exponential back-off (1 s, 2 s, 4 s, 8 s … capped at 30 s).

        entity_ids=None subscribes to all entities.

        This coroutine runs indefinitely; cancel the enclosing task to stop it.
        """
        ws_url = self._ws_url()
        backoff = 1.0

        while True:
            try:
                async with websockets.connect(ws_url) as ws:
                    # 1. Receive the auth_required challenge
                    raw = await ws.recv()
                    msg = json.loads(raw)
                    if msg.get("type") != "auth_required":
                        raise HAConnectionError(
                            f"Expected auth_required, got: {msg.get('type')}"
                        )

                    # 2. Authenticate
                    await ws.send(
                        json.dumps({"type": "auth", "access_token": self._token})
                    )
                    raw = await ws.recv()
                    auth_result = json.loads(raw)
                    if auth_result.get("type") == "auth_invalid":
                        raise HAConnectionError(
                            "WebSocket authentication failed: invalid token"
                        )
                    if auth_result.get("type") != "auth_ok":
                        raise HAConnectionError(
                            f"Unexpected auth response: {auth_result}"
                        )

                    # 3. Subscribe to state_changed events
                    sub_id = 1
                    subscribe_msg: dict[str, Any] = {
                        "id": sub_id,
                        "type": "subscribe_events",
                        "event_type": "state_changed",
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    raw = await ws.recv()
                    sub_result = json.loads(raw)
                    if sub_result.get("success") is False:
                        raise HAConnectionError(
                            f"Failed to subscribe to state_changed: {sub_result}"
                        )

                    logger.info("HA WebSocket: subscribed to state_changed events")
                    # Successful connection resets backoff
                    backoff = 1.0

                    # 4. Process incoming events
                    async for raw_event in ws:
                        event_msg = json.loads(raw_event)
                        if event_msg.get("type") != "event":
                            continue
                        event_data: dict[str, Any] = event_msg.get("event", {})
                        if event_data.get("event_type") != "state_changed":
                            continue
                        data = event_data.get("data", {})
                        # Apply entity_id filter if requested
                        if entity_ids is not None:
                            eid = data.get("entity_id", "")
                            if eid not in entity_ids:
                                continue
                        result = callback(data)
                        if asyncio.iscoroutine(result):
                            await result

            except asyncio.CancelledError:
                logger.info("HA WebSocket subscription cancelled")
                return
            except HAConnectionError:
                raise
            except (
                websockets.exceptions.ConnectionClosed,
                OSError,
                Exception,
            ) as exc:
                logger.warning(
                    "HA WebSocket disconnected (%s); reconnecting in %.0f s",
                    exc,
                    backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    # ---------------------------------------------------------------------------
    # Services
    # ---------------------------------------------------------------------------

    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: Optional[dict[str, Any]] = None,
        target: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Call a HA service.

        Returns the list of affected entity state dicts.
        """
        payload: dict[str, Any] = {}
        if service_data:
            payload.update(service_data)
        if target:
            payload["target"] = target

        c = await self._get_client()
        r = await c.post(f"/api/services/{domain}/{service}", json=payload)
        r.raise_for_status()
        return r.json()

    # ---------------------------------------------------------------------------
    # Configuration
    # ---------------------------------------------------------------------------

    async def get_config(self) -> dict[str, Any]:
        """Return the /api/config payload (location, unit system, etc.)."""
        c = await self._get_client()
        r = await c.get("/api/config")
        r.raise_for_status()
        return r.json()

    async def check_config(self) -> dict[str, Any]:
        """
        Trigger a HA config check.

        Returns {"result": "valid"} or {"result": "invalid", "errors": str}.
        """
        c = await self._get_client()
        r = await c.post("/api/config/core/check_config")
        r.raise_for_status()
        return r.json()

    async def list_config_entries(self) -> list[dict[str, Any]]:
        """Return all config entries (integrations)."""
        c = await self._get_client()
        r = await c.get("/api/config/config_entries/entry")
        r.raise_for_status()
        return r.json()

    async def reload_config(self, domain: Optional[str] = None) -> None:
        """
        Reload HA configuration.

        domain=None reloads core config; otherwise calls
        POST /api/services/{domain}/reload for that integration.
        """
        c = await self._get_client()
        if domain:
            r = await c.post(f"/api/services/{domain}/reload")
        else:
            r = await c.post("/api/config/core/reload")
        r.raise_for_status()

    async def restart(self) -> None:
        """Restart Home Assistant (DESTRUCTIVE)."""
        c = await self._get_client()
        r = await c.post("/api/config/core/restart")
        r.raise_for_status()

    # ---------------------------------------------------------------------------
    # History / logs
    # ---------------------------------------------------------------------------

    async def get_history(
        self,
        entity_ids: Optional[list[str]] = None,
        hours: float = 24.0,
        end_time: Optional[str] = None,
    ) -> list[list[dict[str, Any]]]:
        """
        Return entity state history.

        start_iso is computed as (now - hours) in ISO 8601 format.
        entity_ids=None returns history for all entities.
        end_time is an optional ISO 8601 string.
        """
        start_dt = datetime.now(tz=timezone.utc) - timedelta(
            hours=hours
        )
        start_iso = start_dt.isoformat()

        params: dict[str, Any] = {}
        if entity_ids:
            params["filter_entity_id"] = ",".join(entity_ids)
        if end_time:
            params["end_time"] = end_time

        path = f"/api/history/period/{start_iso}"

        c = await self._get_client()
        r = await c.get(path, params=params)
        r.raise_for_status()
        return r.json()

    async def get_history_range(
        self,
        start_time: str,
        entity_ids: Optional[list[str]] = None,
        end_time: Optional[str] = None,
    ) -> list[list[dict[str, Any]]]:
        """
        Return entity history for an explicit start_time ISO string.

        Prefer get_history() for the common hours-based use case.
        """
        params: dict[str, Any] = {}
        if entity_ids:
            params["filter_entity_id"] = ",".join(entity_ids)
        if end_time:
            params["end_time"] = end_time

        path = f"/api/history/period/{start_time}"
        c = await self._get_client()
        r = await c.get(path, params=params)
        r.raise_for_status()
        return r.json()

    async def get_logbook(
        self,
        entity_id: Optional[str] = None,
        hours: float = 24.0,
        end_time: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Return logbook entries.

        start_iso is computed as (now - hours) in ISO 8601 format.
        entity_id=None returns entries for all entities.
        end_time is an optional ISO 8601 string.
        """
        start_dt = datetime.now(tz=timezone.utc) - timedelta(
            hours=hours
        )
        start_iso = start_dt.isoformat()

        params: dict[str, Any] = {}
        if entity_id:
            params["entity_id"] = entity_id
        if end_time:
            params["end_time"] = end_time

        path = f"/api/logbook/{start_iso}"

        c = await self._get_client()
        r = await c.get(path, params=params)
        r.raise_for_status()
        return r.json()

    async def get_error_log(self) -> str:
        """Return the HA error log as a plain-text string."""
        c = await self._get_client()
        r = await c.get("/api/error_log")
        r.raise_for_status()
        return r.text

    # ---------------------------------------------------------------------------
    # Templates
    # ---------------------------------------------------------------------------

    async def get_template(self, template_str: str) -> str:
        """Render a Jinja2 template string via HA and return the result."""
        c = await self._get_client()
        r = await c.post("/api/template", json={"template": template_str})
        r.raise_for_status()
        return r.text

    # ---------------------------------------------------------------------------
    # Devices / areas / floors
    # ---------------------------------------------------------------------------

    async def list_devices(self) -> list[dict[str, Any]]:
        """Return all registered devices."""
        c = await self._get_client()
        r = await c.get("/api/config/device_registry/list")
        r.raise_for_status()
        return r.json()

    async def list_areas(self) -> list[dict[str, Any]]:
        """Return all area registry entries."""
        c = await self._get_client()
        r = await c.get("/api/config/area_registry/list")
        r.raise_for_status()
        return r.json()

    async def list_floors(self) -> list[dict[str, Any]]:
        """Return all floor registry entries."""
        c = await self._get_client()
        r = await c.get("/api/config/floor_registry/list")
        r.raise_for_status()
        return r.json()

    # ---------------------------------------------------------------------------
    # Long-lived access tokens (WebSocket-based)
    # ---------------------------------------------------------------------------

    async def create_long_lived_token(
        self,
        client_name: str,
        lifespan_days: int = 3650,
    ) -> str:
        """
        Create a long-lived access token for the current user via the
        HA WebSocket API (the REST endpoint is not available for this operation).

        Returns the new token string.
        Raises HAConnectionError on authentication failure.
        """
        ws_url = self._ws_url()

        try:
            async with websockets.connect(ws_url) as ws:
                # Auth handshake
                raw = await ws.recv()
                msg = json.loads(raw)
                if msg.get("type") != "auth_required":
                    raise HAConnectionError(
                        f"Expected auth_required, got: {msg.get('type')}"
                    )

                await ws.send(
                    json.dumps({"type": "auth", "access_token": self._token})
                )
                raw = await ws.recv()
                auth_result = json.loads(raw)
                if auth_result.get("type") == "auth_invalid":
                    raise HAConnectionError(
                        "WebSocket authentication failed: invalid token"
                    )
                if auth_result.get("type") != "auth_ok":
                    raise HAConnectionError(
                        f"Unexpected auth response: {auth_result}"
                    )

                # Request token creation
                call_id = 1
                await ws.send(
                    json.dumps(
                        {
                            "id": call_id,
                            "type": "auth/long_lived_access_token",
                            "client_name": client_name,
                            "lifespan": lifespan_days,
                        }
                    )
                )
                raw = await ws.recv()
                result = json.loads(raw)

                if not result.get("success"):
                    error = result.get("error", {})
                    raise HAConnectionError(
                        f"Failed to create long-lived token: {error.get('message', result)}"
                    )

                token: str = result["result"]
                return token

        except HAConnectionError:
            raise
        except Exception as exc:
            raise HAConnectionError(
                f"WebSocket error while creating long-lived token: {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_client: Optional[HAClient] = None


def init_ha_client(ha_url: str, ha_token: str) -> HAClient:
    """
    Initialise (or replace) the module-level singleton.

    Call once at application startup from the FastAPI lifespan handler.
    The ha_token should be the raw token value (without "Bearer " prefix);
    the client adds the prefix internally.
    """
    global _client
    _client = HAClient(base_url=ha_url, token=ha_token)
    return _client


def get_ha_client() -> HAClient:
    """
    Return the module-level singleton.

    Raises RuntimeError if init_ha_client() has not been called.
    """
    if _client is None:
        raise RuntimeError(
            "HAClient not initialised. Call init_ha_client() at startup."
        )
    return _client
