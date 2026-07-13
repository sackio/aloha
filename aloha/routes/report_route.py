"""
aloha/routes/report_route.py

"Report a problem" — an in-app path that bundles a secrets-free diagnostics
snapshot the user can paste into a GitHub issue, and (if the operator opted in
to error reporting) also forwards it to Sentry.

  GET  /api/report/diagnostics   → the safe diagnostics bundle (for display)
  POST /api/report/problem       → {note} → bundle + a prefilled GitHub issue URL
"""

from __future__ import annotations

import json
import logging
import urllib.parse

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from aloha import telemetry

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/report", tags=["report"])

_ISSUE_BASE = "https://github.com/sackio/aloha/issues/new"


async def _ha_connected() -> bool:
    try:
        from aloha.ha.client import get_ha_client
        return bool(await get_ha_client().ping())
    except Exception:
        return False


def _issue_url(note: str, diag: dict) -> str:
    """Build a prefilled GitHub 'new issue' URL with the safe diagnostics."""
    # Scrub the user's own note too — they may have pasted a secret by accident.
    note = telemetry.scrub(note or "")
    env_lines = "\n".join(
        f"- **{k}**: {diag.get(k)}"
        for k in ("aloha_version", "run_mode", "ai_provider", "model",
                  "safety_mode", "public_url_provider", "ha_connected",
                  "python", "platform")
    )
    body = (
        f"**What happened?**\n{note or '(describe the problem)'}\n\n"
        f"**Environment**\n{env_lines}\n\n"
        "<details><summary>Recent log tail (auto-scrubbed)</summary>\n\n```\n"
        + "\n".join(diag.get("log_tail", [])[-60:])
        + "\n```\n</details>\n"
    )
    q = urllib.parse.urlencode({
        "title": f"[report] {(note or 'problem report')[:80]}",
        "body": body,
        "labels": "beta,needs-triage",
    })
    return f"{_ISSUE_BASE}?{q}"


@router.get("/diagnostics")
async def diagnostics(request: Request) -> JSONResponse:
    config = request.app.state.config
    diag = telemetry.build_diagnostics(config, ha_connected=await _ha_connected())
    return JSONResponse(diag)


@router.post("/problem")
async def report_problem(request: Request) -> JSONResponse:
    config = request.app.state.config
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    note = (payload or {}).get("note", "") if isinstance(payload, dict) else ""

    diag = telemetry.capture_report(config, note=note, ha_connected=await _ha_connected())
    return JSONResponse({
        "reported": diag.get("reported", False),
        "error_reporting_active": telemetry.is_active(),
        "diagnostics": diag,
        "github_issue_url": _issue_url(note, diag),
    })
