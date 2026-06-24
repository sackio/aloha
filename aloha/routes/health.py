"""
aloha/routes/health.py

GET /health — liveness and readiness probe.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from aloha.config import AlohaConfig
from aloha.ha.client import get_ha_client

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health(config: AlohaConfig = None) -> JSONResponse:
    """
    Return service health status.

    Tries ha_client.ping() to determine connectivity.
    Falls back gracefully if the client is not yet initialised.
    """
    ha_connected = False
    ha_version = "unknown"

    try:
        ha_client = get_ha_client()
        ha_connected = await ha_client.ping()
        if ha_connected:
            try:
                ha_version = await ha_client.get_version()
            except Exception:
                ha_version = "unknown"
    except RuntimeError:
        # HAClient not yet initialised
        ha_connected = False
    except Exception:
        log.debug("Health check HA ping failed", exc_info=True)
        ha_connected = False

    # Load config to read provider and setup_complete
    try:
        from aloha.config import AlohaConfig as _AlohaConfig
        cfg = _AlohaConfig.load()
        setup_complete = cfg.setup_complete
        provider = cfg.ai_provider
    except Exception:
        setup_complete = False
        provider = "unknown"

    return JSONResponse(
        {
            "status": "ok",
            "ha_connected": ha_connected,
            "ha_version": ha_version,
            "setup_complete": setup_complete,
            "provider": provider,
        }
    )
