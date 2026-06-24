"""
aloha/routes/context_route.py

HA context snapshot endpoints:
  GET  /api/context         — return latest context snapshot fields
  POST /api/context/refresh — trigger immediate snapshot rebuild
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/context")
async def get_context() -> JSONResponse:
    """
    Return the latest HA context snapshot.

    Fields returned: timestamp, entity_count, entities_by_domain,
    areas, automation_summaries, integrations, recent_events, summary.
    """
    try:
        from aloha.context.engine import get_context_engine
        engine = get_context_engine()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Context engine not initialised")

    snapshot = engine.get_snapshot()
    if snapshot is None:
        return JSONResponse(
            {
                "summary": "Context not yet available — initialising.",
                "entity_count": 0,
                "automation_count": 0,
                "last_refreshed": None,
            }
        )

    return JSONResponse(
        {
            "timestamp": snapshot.timestamp,
            "entity_count": snapshot.entity_count,
            "entities_by_domain": {
                domain: [
                    {
                        "entity_id": s.get("entity_id"),
                        "state": s.get("state"),
                        "attributes": s.get("attributes", {}),
                    }
                    for s in states
                ]
                for domain, states in snapshot.entities_by_domain.items()
            },
            "areas": snapshot.areas,
            "automation_summaries": snapshot.automation_summaries,
            "integrations": snapshot.integrations,
            "recent_events": snapshot.recent_events,
            "summary": snapshot.compressed_summary,
            "automation_count": snapshot.automation_count,
            "last_refreshed": snapshot.timestamp,
        }
    )


@router.post("/api/context/refresh")
async def refresh_context() -> JSONResponse:
    """Trigger an immediate context snapshot rebuild."""
    try:
        from aloha.context.engine import get_context_engine
        engine = get_context_engine()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Context engine not initialised")

    try:
        snapshot = await engine.build_snapshot()
        # Update the engine's internal snapshot so future reads see the fresh one.
        engine._snapshot = snapshot  # noqa: SLF001
        return JSONResponse({"ok": True, "last_refreshed": snapshot.timestamp})
    except Exception as exc:
        log.exception("Context refresh failed")
        raise HTTPException(status_code=500, detail=f"Refresh failed: {exc}") from exc
