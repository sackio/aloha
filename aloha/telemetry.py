"""
aloha/telemetry.py

Opt-in error reporting + safe diagnostics.

Privacy first: Aloha phones nothing home by default. Error reporting is OFF
unless the operator sets an error-reporting DSN (config `error_reporting_dsn`
or env `ALOHA_ERROR_REPORTING_DSN`). With no DSN, `init_error_reporting()` is a
no-op and no network calls are ever made.

When enabled it uses Sentry. We force `send_default_pii=False` and run a
`before_send` scrubber that redacts anything that looks like a token, key, or
Authorization header before an event leaves the box.

The `build_diagnostics()` helper assembles a *safe* snapshot (versions, mode,
provider name — never the key, HA reachability, recent log tail) for the in-app
"report a problem" flow. It is designed so the bundle can be pasted straight
into a GitHub issue without leaking secrets.
"""

from __future__ import annotations

import logging
import platform
import re
import sys
from collections import deque
from typing import Any, Optional

log = logging.getLogger(__name__)

# Aloha's release string — kept in one place so Sentry events + diagnostics agree.
VERSION = "0.1.0"

_active = False  # set True once Sentry is successfully initialised

# ---------------------------------------------------------------------------
# In-memory ring buffer of recent log records, so "report a problem" can attach
# the tail of the log without reading files off disk (works in every mode).
# ---------------------------------------------------------------------------
_LOG_RING: "deque[str]" = deque(maxlen=400)


class _RingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            _LOG_RING.append(self.format(record))
        except Exception:
            pass


def install_log_ring() -> None:
    """Attach the ring-buffer handler to the root logger (idempotent)."""
    root = logging.getLogger()
    if any(isinstance(h, _RingHandler) for h in root.handlers):
        return
    h = _RingHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    h.setLevel(logging.INFO)
    root.addHandler(h)


# ---------------------------------------------------------------------------
# Secret scrubbing — applied both to Sentry events and diagnostics bundles.
# ---------------------------------------------------------------------------
# Patterns that should never leave the box. Order matters (longest first).
_SECRET_PATTERNS = [
    re.compile(r"(?i)\b(sk-[A-Za-z0-9_-]{8,})"),                 # OpenAI-style
    re.compile(r"(?i)\b(sk-ant-[A-Za-z0-9_-]{8,})"),            # Anthropic
    re.compile(r"(?i)\b(am[ks]_[A-Za-z0-9_-]{8,})"),           # Aloha MCP key/secret
    re.compile(r"(?i)\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_.-]+"),  # JWT / LLAT
    re.compile(r"(?i)(authorization\"?\s*[:=]\s*\"?)(bearer\s+|basic\s+)?[A-Za-z0-9._:+/=-]{8,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password|authtoken)(\"?\s*[:=]\s*\"?)([^\s\"',}]{6,})"),
]

_REDACTED = "«redacted»"


def scrub(text: str) -> str:
    """Redact anything that looks like a credential from a string."""
    if not text:
        return text
    out = text
    for pat in _SECRET_PATTERNS:
        # Keep any labelled prefix (group up to the value) and redact the value.
        def _repl(m: "re.Match[str]") -> str:
            groups = m.groups()
            if len(groups) >= 2 and groups[0] and any(c in (groups[0] or "") for c in ":="):
                return f"{groups[0]}{_REDACTED}"
            return _REDACTED
        out = pat.sub(_repl, out)
    return out


def _scrub_event(event: Any, _hint: Any = None) -> Any:
    """Sentry before_send hook: deep-scrub string values."""
    try:
        def walk(o: Any) -> Any:
            if isinstance(o, str):
                return scrub(o)
            if isinstance(o, dict):
                return {k: walk(v) for k, v in o.items()}
            if isinstance(o, (list, tuple)):
                return [walk(v) for v in o]
            return o
        return walk(event)
    except Exception:
        return event


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
def init_error_reporting(config: Any) -> bool:
    """
    Initialise Sentry error reporting IF the operator opted in via a DSN.

    Returns True if reporting is now active, False otherwise (no DSN, SDK not
    installed, or init failed). Safe to call once at startup.
    """
    global _active
    install_log_ring()

    dsn = (getattr(config, "error_reporting_dsn", "") or "").strip()
    if not dsn:
        log.debug("Error reporting disabled (no DSN) — nothing is sent off-box.")
        return False

    try:
        import sentry_sdk
    except ImportError:
        log.warning("error_reporting_dsn is set but sentry-sdk is not installed; "
                    "run `pip install sentry-sdk` to enable error reporting.")
        return False

    try:
        sentry_sdk.init(
            dsn=dsn,
            release=f"aloha@{VERSION}",
            environment=getattr(config, "mode", "unknown"),
            send_default_pii=False,          # never attach request bodies / user data
            traces_sample_rate=0.0,          # errors only, no perf tracing
            before_send=_scrub_event,
            max_breadcrumbs=25,
        )
        # A stable-but-anonymous install fingerprint (hash of the data_dir path),
        # so recurring issues from one install group together without identifying it.
        try:
            import hashlib
            fp = hashlib.sha256(str(getattr(config, "data_dir", "")).encode()).hexdigest()[:12]
            sentry_sdk.set_tag("install", fp)
            sentry_sdk.set_tag("ai_provider", getattr(config, "ai_provider", "?"))
            sentry_sdk.set_tag("run_mode", getattr(config, "mode", "?"))
        except Exception:
            pass
        _active = True
        log.info("Error reporting enabled (opt-in) — events are scrubbed of secrets before send.")
        return True
    except Exception as exc:
        log.warning("Failed to initialise error reporting: %s", exc)
        return False


def is_active() -> bool:
    return _active


# ---------------------------------------------------------------------------
# Diagnostics bundle — safe by construction, for "report a problem".
# ---------------------------------------------------------------------------
def build_diagnostics(config: Any, note: str = "", ha_connected: Optional[bool] = None) -> dict:
    """
    Assemble a secrets-free diagnostics snapshot suitable for a GitHub issue.

    Includes: Aloha version, run mode, AI provider *name* (never the key),
    public-URL provider, Python/platform, HA reachability, and the tail of the
    in-memory log ring — all scrubbed.
    """
    log_tail = [scrub(line) for line in list(_LOG_RING)[-120:]]
    info = {
        "aloha_version": VERSION,
        "run_mode": getattr(config, "mode", "?"),
        "ai_provider": getattr(config, "ai_provider", "?"),
        "model": getattr(config, "model", "?"),
        "safety_mode": getattr(config, "safety_mode", "?"),
        "public_url_provider": getattr(config, "public_url_provider", "?"),
        "ha_url": getattr(config, "ha_url", "?"),
        "ha_connected": ha_connected,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "error_reporting_active": _active,
        "note": scrub(note or ""),
        "log_tail": log_tail,
    }
    return info


def capture_report(config: Any, note: str, ha_connected: Optional[bool] = None) -> dict:
    """
    Send a user-initiated problem report to Sentry (if active) and return the
    diagnostics bundle either way, so the UI can offer it for a GitHub issue.
    """
    diag = build_diagnostics(config, note=note, ha_connected=ha_connected)
    if _active:
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_context("diagnostics", {k: v for k, v in diag.items() if k != "log_tail"})
                scope.set_extra("log_tail", "\n".join(diag["log_tail"]))
                sentry_sdk.capture_message(
                    f"[report-a-problem] {scrub(note)[:200] or '(no note)'}",
                    level="info",
                )
            diag["reported"] = True
        except Exception as exc:
            log.warning("capture_report failed: %s", exc)
            diag["reported"] = False
    else:
        diag["reported"] = False
    return diag
