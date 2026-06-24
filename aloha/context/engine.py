"""
aloha/context/engine.py

ContextEngine — periodically snapshots the Home Assistant state and composes
a compressed natural-language summary that is injected into the AI system
prompt.

Usage
-----
Module singleton (preferred):

    from aloha.context.engine import init_context_engine, get_context_engine
    engine = init_context_engine(ha_client, ha_config_dir, refresh_minutes=5)
    await engine.start()

    # Later:
    prompt = get_context_engine().get_system_prompt()

Direct instantiation:

    engine = ContextEngine(ha_client, ha_config_dir, refresh_minutes=5)
    snapshot = await engine.build_snapshot()
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from aloha.ha.client import HAClient

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Snapshot dataclass
# ---------------------------------------------------------------------------


@dataclass
class ContextSnapshot:
    """
    A point-in-time view of the Home Assistant installation.

    Fields
    ------
    timestamp               ISO-8601 UTC string of when the snapshot was taken.
    ha_version              HA version string, e.g. "2024.6.0".
    entity_count            Total number of entities.
    entities_by_domain      Mapping of domain → list of entity state dicts.
    areas                   List of area dicts from HA (name, area_id, …).
    automation_count        Total automations.
    enabled_automation_count  Automations with state != "off".
    automation_summaries    First 50 automation alias strings.
    integrations            List of integration/platform strings.
    config_files            List of relative filenames in ha_config_dir.
    recent_events           Last 20 logbook entries (dicts).
    compressed_summary      Pre-rendered summary string for the AI system prompt.
    """

    timestamp: str
    ha_version: str
    entity_count: int
    entities_by_domain: dict[str, list[dict[str, Any]]]
    areas: list[dict[str, Any]]
    automation_count: int
    enabled_automation_count: int
    automation_summaries: list[str]
    integrations: list[str]
    config_files: list[str]
    recent_events: list[dict[str, Any]]
    compressed_summary: str


# ---------------------------------------------------------------------------
# ContextEngine
# ---------------------------------------------------------------------------


class ContextEngine:
    """
    Maintains a fresh ContextSnapshot of the Home Assistant installation.

    The snapshot is rebuilt in the background every *refresh_minutes*
    minutes.  Callers should use ``get_snapshot()`` for the latest cached
    value and ``get_system_prompt()`` to obtain a ready-to-use string.
    """

    def __init__(
        self,
        ha_client: HAClient,
        ha_config_dir: Path | str,
        refresh_minutes: int = 5,
    ) -> None:
        self._ha = ha_client
        self._ha_config_dir = Path(ha_config_dir)
        self._refresh_interval = refresh_minutes * 60  # seconds
        self._snapshot: Optional[ContextSnapshot] = None
        self._task: Optional[asyncio.Task] = None  # type: ignore[type-arg]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background refresh loop (idempotent)."""
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._refresh_loop(), name="context-engine")

    async def stop(self) -> None:
        """Cancel the background refresh task."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def get_snapshot(self) -> Optional[ContextSnapshot]:
        """Return the most recent snapshot, or None if not yet built."""
        return self._snapshot

    def get_system_prompt(self) -> str:
        """
        Return the compressed_summary from the latest snapshot, or a
        minimal default string if no snapshot is available yet.
        """
        snap = self._snapshot
        if snap is None:
            return (
                "Home Assistant context not yet available. "
                "The context engine is initialising — please retry shortly."
            )
        return snap.compressed_summary

    # ------------------------------------------------------------------
    # Background loop
    # ------------------------------------------------------------------

    async def _refresh_loop(self) -> None:
        """Build a snapshot immediately, then repeat every refresh_interval seconds."""
        while True:
            try:
                self._snapshot = await self.build_snapshot()
                log.debug(
                    "Context snapshot refreshed: %d entities, %d automations",
                    self._snapshot.entity_count,
                    self._snapshot.automation_count,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Failed to build HA context snapshot")
            try:
                await asyncio.sleep(self._refresh_interval)
            except asyncio.CancelledError:
                raise

    # ------------------------------------------------------------------
    # Snapshot builder
    # ------------------------------------------------------------------

    async def build_snapshot(self) -> ContextSnapshot:
        """
        Query HA and compose a full ContextSnapshot.

        This is a coroutine; callers may also invoke it directly (e.g. for
        a forced refresh on POST /api/context/refresh).
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Fire independent HA calls concurrently where possible.
        (
            ha_version,
            all_states,
            areas,
            config_entries,
            recent_logbook,
        ) = await asyncio.gather(
            self._safe_get_version(),
            self._safe_get_states(),
            self._safe_get_areas(),
            self._safe_list_config_entries(),
            self._safe_get_logbook(),
        )

        # --- Entities by domain ---
        entities_by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for state in all_states:
            eid = state.get("entity_id", "")
            domain = eid.split(".")[0] if "." in eid else "unknown"
            entities_by_domain[domain].append(state)

        entity_count = len(all_states)

        # --- Areas ---
        # areas is a list of dicts like [{"area_id": "...", "name": "..."}]

        # --- Automations ---
        automation_states = entities_by_domain.get("automation", [])
        automation_count = len(automation_states)
        enabled_automation_count = sum(
            1 for s in automation_states if s.get("state") != "off"
        )
        automation_summaries: list[str] = []
        for s in automation_states[:50]:
            attrs = s.get("attributes") or {}
            alias = attrs.get("friendly_name") or s.get("entity_id", "")
            automation_summaries.append(alias)

        # --- Integrations ---
        integrations = sorted(
            {
                entry.get("domain", "")
                for entry in config_entries
                if entry.get("domain")
            }
        )

        # --- Config files ---
        config_files = self._list_config_files()

        # --- Recent events (last 20 logbook entries) ---
        recent_events = recent_logbook[:20]

        # --- Compressed summary ---
        compressed_summary = self._build_compressed_summary(
            ha_version=ha_version,
            entity_count=entity_count,
            entities_by_domain=entities_by_domain,
            areas=areas,
            automation_count=automation_count,
            enabled_automation_count=enabled_automation_count,
            automation_summaries=automation_summaries,
            integrations=integrations,
            recent_events=recent_events,
        )

        return ContextSnapshot(
            timestamp=timestamp,
            ha_version=ha_version,
            entity_count=entity_count,
            entities_by_domain=dict(entities_by_domain),
            areas=areas,
            automation_count=automation_count,
            enabled_automation_count=enabled_automation_count,
            automation_summaries=automation_summaries,
            integrations=integrations,
            config_files=config_files,
            recent_events=recent_events,
            compressed_summary=compressed_summary,
        )

    # ------------------------------------------------------------------
    # Summary builder
    # ------------------------------------------------------------------

    def _build_compressed_summary(
        self,
        *,
        ha_version: str,
        entity_count: int,
        entities_by_domain: dict[str, list[dict[str, Any]]],
        areas: list[dict[str, Any]],
        automation_count: int,
        enabled_automation_count: int,
        automation_summaries: list[str],
        integrations: list[str],
        recent_events: list[dict[str, Any]],
    ) -> str:
        """
        Build the compressed_summary string.

        Format:
            Home Assistant v{ver} — {n} entities across {area_n} areas
            Domains: light×n, switch×n... (top 8)
            Areas: name (n entities), ...
            Automations: {enabled}/{total} enabled
              Active: alias1, alias2... (first 15)
            Integrations: int1, int2...
            Recent: entity → state (Xm ago), ...
        """
        lines: list[str] = []

        # Header
        area_n = len(areas)
        lines.append(
            f"Home Assistant v{ha_version} — {entity_count} entities across {area_n} areas"
        )

        # Top 8 domains by entity count
        domain_counts = Counter({d: len(v) for d, v in entities_by_domain.items()})
        top_domains = domain_counts.most_common(8)
        if top_domains:
            domain_str = ", ".join(f"{d}×{n}" for d, n in top_domains)
            lines.append(f"Domains: {domain_str}")

        # Areas with entity counts
        if areas:
            area_parts: list[str] = []
            for area in areas:
                aname = area.get("name", "?")
                aid = area.get("area_id", "")
                # Count entities whose area_id matches (not available in REST states,
                # so we do a best-effort name-prefix match on friendly_name)
                n_in_area = sum(
                    1
                    for states in entities_by_domain.values()
                    for s in states
                    if (s.get("attributes") or {}).get("area_id") == aid
                )
                area_parts.append(f"{aname} ({n_in_area} entities)")
            lines.append("Areas: " + ", ".join(area_parts))

        # Automations
        lines.append(f"Automations: {enabled_automation_count}/{automation_count} enabled")
        if automation_summaries:
            active = [a for a in automation_summaries[:15]]
            lines.append("  Active: " + ", ".join(active))

        # Integrations
        if integrations:
            lines.append("Integrations: " + ", ".join(integrations[:30]))

        # Recent events
        if recent_events:
            now = datetime.now(timezone.utc)
            event_parts: list[str] = []
            for ev in recent_events[:10]:
                entity = ev.get("entity_id") or ev.get("name", "?")
                state = ev.get("message") or ev.get("state", "?")
                when_str = ev.get("when", "")
                age_str = ""
                if when_str:
                    try:
                        when_dt = datetime.fromisoformat(when_str.replace("Z", "+00:00"))
                        delta = now - when_dt
                        minutes = int(delta.total_seconds() / 60)
                        age_str = f" ({minutes}m ago)"
                    except ValueError:
                        pass
                event_parts.append(f"{entity} → {state}{age_str}")
            lines.append("Recent: " + "; ".join(event_parts))

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Config file listing
    # ------------------------------------------------------------------

    def _list_config_files(self) -> list[str]:
        """Return relative filenames of YAML/JSON files in ha_config_dir."""
        if not self._ha_config_dir.exists():
            return []
        result: list[str] = []
        try:
            for p in sorted(self._ha_config_dir.rglob("*")):
                if p.is_file() and p.suffix in {".yaml", ".yml", ".json"}:
                    try:
                        result.append(str(p.relative_to(self._ha_config_dir)))
                    except ValueError:
                        result.append(str(p))
        except PermissionError:
            pass
        return result

    # ------------------------------------------------------------------
    # Safe HA call wrappers (return sensible defaults on failure)
    # ------------------------------------------------------------------

    async def _safe_get_version(self) -> str:
        try:
            return await self._ha.get_version()
        except Exception:
            return "unknown"

    async def _safe_get_states(self) -> list[dict[str, Any]]:
        try:
            return await self._ha.get_states()
        except Exception:
            return []

    async def _safe_get_areas(self) -> list[dict[str, Any]]:
        """HA areas via /api/config/area_registry/list (template workaround)."""
        try:
            # HA REST API does not expose area registry directly; use a template.
            tmpl = (
                "{{ areas() | map('string') | list | tojson }}"
            )
            raw = await self._ha.get_template(tmpl)
            import json
            area_ids = json.loads(raw)
            areas = []
            for aid in area_ids:
                name_tmpl = f"{{{{ area_name('{aid}') }}}}"
                try:
                    name = (await self._ha.get_template(name_tmpl)).strip()
                except Exception:
                    name = aid
                areas.append({"area_id": aid, "name": name})
            return areas
        except Exception:
            return []

    async def _safe_list_config_entries(self) -> list[dict[str, Any]]:
        try:
            return await self._ha.list_config_entries()
        except Exception:
            return []

    async def _safe_get_logbook(self) -> list[dict[str, Any]]:
        try:
            return await self._ha.get_logbook()
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_engine: Optional[ContextEngine] = None


def init_context_engine(
    ha_client: HAClient,
    ha_config_dir: Path | str,
    refresh_minutes: int = 5,
) -> ContextEngine:
    """
    Initialise (or replace) the module-level ContextEngine singleton.
    Call once at application startup.
    """
    global _engine
    _engine = ContextEngine(ha_client, ha_config_dir, refresh_minutes)
    return _engine


def get_context_engine() -> ContextEngine:
    """
    Return the module-level singleton.

    Raises RuntimeError if init_context_engine() has not been called.
    """
    if _engine is None:
        raise RuntimeError(
            "ContextEngine not initialised. Call init_context_engine() at startup."
        )
    return _engine
