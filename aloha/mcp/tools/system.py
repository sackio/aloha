"""
aloha/mcp/tools/system.py

MCP tool definitions and dispatcher for Home Assistant system-level operations.

Exports:
    TOOLS       — list[ToolDef]
    TOOL_NAMES  — set[str]
    execute_system_tool(name, args, ha_client) — async dispatcher
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from aloha.agent.types import SafetyLevel, ToolDef
from aloha.ha.client import HAClient

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[ToolDef] = [
    ToolDef(
        name="get_system_health",
        description="Get the Home Assistant system health report.",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.READ,
        returns="System health report as formatted string",
    ),
    ToolDef(
        name="get_ha_version",
        description="Get the currently running Home Assistant version.",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.READ,
        returns="Version string",
    ),
    ToolDef(
        name="get_error_log",
        description="Retrieve the Home Assistant error log.",
        parameters={
            "type": "object",
            "properties": {
                "lines": {
                    "type": "integer",
                    "description": "Number of trailing log lines to return (default 100).",
                    "default": 100,
                },
            },
        },
        safety=SafetyLevel.READ,
        returns="Error log text",
    ),
    ToolDef(
        name="get_logbook",
        description="Get general Home Assistant logbook entries (not entity-specific).",
        parameters={
            "type": "object",
            "properties": {
                "hours": {
                    "type": "number",
                    "description": "How many hours of entries to retrieve (default 24).",
                    "default": 24,
                },
            },
        },
        safety=SafetyLevel.READ,
        returns="Chronological list of logbook entries",
    ),
    ToolDef(
        name="list_integrations",
        description="List all loaded integrations (config entries).",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.READ,
        returns="Table of domain | title | state",
    ),
    ToolDef(
        name="list_devices",
        description="List all Home Assistant devices.",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.READ,
        returns="Table of device id | name | manufacturer | model | area",
    ),
    ToolDef(
        name="list_areas",
        description="List all Home Assistant areas.",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.READ,
        returns="Table of area id | name",
    ),
    ToolDef(
        name="list_floors",
        description="List all Home Assistant floors.",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.READ,
        returns="Table of floor id | name",
    ),
    ToolDef(
        name="get_device_info",
        description="Get detailed information for a specific device.",
        parameters={
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The device id.",
                },
            },
            "required": ["device_id"],
        },
        safety=SafetyLevel.READ,
        returns="Device detail as YAML-like string",
    ),
    ToolDef(
        name="restart_ha",
        description=(
            "Restart Home Assistant. This is a DESTRUCTIVE action and will "
            "interrupt all running automations and connected clients."
        ),
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.DESTRUCTIVE,
        returns="DiffEvent-style confirmation dict requiring approval",
    ),
    ToolDef(
        name="reload_core_config",
        description="Reload the Home Assistant core configuration without restarting.",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.WRITE_CONFIG,
        returns="Confirmation string",
    ),
    ToolDef(
        name="reload_all_yaml",
        description=(
            "Reload all YAML-based domains: automations, scripts, scenes, groups, "
            "input_booleans, input_numbers, input_selects, and template entities."
        ),
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.WRITE_CONFIG,
        returns="Confirmation string listing reloaded domains",
    ),
    ToolDef(
        name="create_persistent_notification",
        description="Create a persistent notification visible in the Home Assistant UI.",
        parameters={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Notification message body.",
                },
                "title": {
                    "type": "string",
                    "description": "Optional notification title.",
                },
                "notification_id": {
                    "type": "string",
                    "description": "Optional ID (allows updating/dismissing by id).",
                },
            },
            "required": ["message"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="dismiss_persistent_notification",
        description="Dismiss a persistent notification from the Home Assistant UI.",
        parameters={
            "type": "object",
            "properties": {
                "notification_id": {
                    "type": "string",
                    "description": "The notification_id to dismiss.",
                },
            },
            "required": ["notification_id"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="send_notification",
        description="Send a notification via a notify service (e.g. mobile app, Pushover).",
        parameters={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Notify service name, e.g. 'mobile_app_iphone' or 'pushover'.",
                },
                "message": {
                    "type": "string",
                    "description": "Notification message body.",
                },
                "title": {
                    "type": "string",
                    "description": "Optional notification title.",
                },
                "target": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of notification targets.",
                },
            },
            "required": ["service", "message"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="fire_event",
        description="Fire a custom Home Assistant event on the event bus.",
        parameters={
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "description": "The event type string, e.g. 'my_custom_event'.",
                },
                "event_data": {
                    "type": "object",
                    "description": "Optional dict of event data to include.",
                },
            },
            "required": ["event_type"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
]

TOOL_NAMES: set[str] = {t.name for t in TOOLS}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _yaml_like(data: dict[str, Any], indent: int = 0) -> str:
    """Render a dict as a YAML-like string."""
    prefix = "  " * indent
    lines = []
    for key, val in sorted(data.items()):
        if isinstance(val, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_yaml_like(val, indent + 1))
        elif isinstance(val, list):
            lines.append(f"{prefix}{key}: {json.dumps(val)}")
        else:
            lines.append(f"{prefix}{key}: {val}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


async def execute_system_tool(
    name: str,
    args: dict[str, Any],
    ha_client: HAClient,
) -> Any:
    """Route to the correct system tool implementation."""

    # --- READ tools ---

    if name == "get_system_health":
        health = await ha_client.get_system_health()
        lines = ["Home Assistant System Health", ""]
        for section, data in (health.get("info") or {}).items():
            lines.append(f"[{section}]")
            if isinstance(data, dict):
                for k, v in data.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"  {data}")
            lines.append("")
        if not health.get("info"):
            lines.append(json.dumps(health, indent=2))
        return "\n".join(lines)

    if name == "get_ha_version":
        version = await ha_client.get_version()
        return f"Home Assistant version: {version}"

    if name == "get_error_log":
        lines_count = int(args.get("lines", 100))
        log_text = await ha_client.get_error_log()
        all_lines = log_text.splitlines()
        tail = all_lines[-lines_count:] if len(all_lines) > lines_count else all_lines
        header = f"HA Error Log (last {lines_count} lines, showing {len(tail)}):"
        return header + "\n" + "\n".join(tail)

    if name == "get_logbook":
        hours = float(args.get("hours", 24))
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=hours)
        start_iso = start.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        entries = await ha_client.get_logbook(start_time=start_iso)
        if not entries:
            return f"No logbook entries in the last {hours:.0f} hours."
        lines = [f"Logbook (last {hours:.0f}h) — {len(entries)} entries:", ""]
        for entry in entries:
            ts = entry.get("when", "")
            entity = entry.get("entity_id", "")
            msg = entry.get("message", "")
            n = entry.get("name", "")
            lines.append(f"  {ts}  {n} ({entity}): {msg}")
        return "\n".join(lines)

    if name == "list_integrations":
        entries = await ha_client.list_config_entries()
        if not entries:
            return "No integrations found."
        entries = sorted(entries, key=lambda e: e.get("domain", ""))
        w_d = max(len("domain"), *(len(e.get("domain", "")) for e in entries))
        w_t = max(len("title"), *(len(e.get("title", "")) for e in entries))
        w_s = max(len("state"), *(len(e.get("state", "")) for e in entries))
        sep = f"+{'-'*(w_d+2)}+{'-'*(w_t+2)}+{'-'*(w_s+2)}+"
        header = f"| {'domain':<{w_d}} | {'title':<{w_t}} | {'state':<{w_s}} |"
        lines = [sep, header, sep]
        for e in entries:
            lines.append(
                f"| {e.get('domain',''):<{w_d}} | {e.get('title',''):<{w_t}} | {e.get('state',''):<{w_s}} |"
            )
        lines.append(sep)
        return "\n".join(lines)

    if name == "list_devices":
        # Use template to get device registry info
        template = (
            "{% set devices = [] %}"
            "{% for device_id in device_entities('') %}"
            "{% endfor %}"
            "{{ devices | tojson }}"
        )
        # HA REST API doesn't expose device registry directly; use config/device_registry
        try:
            client = await ha_client._get_client()
            r = await client.get("/api/config/device_registry/entry")
            if r.status_code == 200:
                devices = r.json()
                if not devices:
                    return "No devices found."
                devices = sorted(devices, key=lambda d: d.get("name_by_user") or d.get("name", ""))
                w_id = min(20, max(len("id"), *(len(d.get("id", "")) for d in devices)))
                w_name = max(len("name"), *(len(d.get("name_by_user") or d.get("name", "")) for d in devices))
                w_mfr = max(len("manufacturer"), *(len(d.get("manufacturer") or "") for d in devices))
                w_model = max(len("model"), *(len(d.get("model") or "") for d in devices))
                sep = f"+{'-'*(w_id+2)}+{'-'*(w_name+2)}+{'-'*(w_mfr+2)}+{'-'*(w_model+2)}+"
                header = f"| {'id':<{w_id}} | {'name':<{w_name}} | {'manufacturer':<{w_mfr}} | {'model':<{w_model}} |"
                lines = [sep, header, sep]
                for d in devices:
                    did = d.get("id", "")[:w_id]
                    dname = d.get("name_by_user") or d.get("name", "")
                    dmfr = d.get("manufacturer") or ""
                    dmodel = d.get("model") or ""
                    lines.append(
                        f"| {did:<{w_id}} | {dname:<{w_name}} | {dmfr:<{w_mfr}} | {dmodel:<{w_model}} |"
                    )
                lines.append(sep)
                return "\n".join(lines)
        except Exception:
            pass
        return "Could not retrieve device list (device registry endpoint unavailable)."

    if name == "list_areas":
        try:
            client = await ha_client._get_client()
            r = await client.get("/api/config/area_registry/entry")
            if r.status_code == 200:
                areas = r.json()
                if not areas:
                    return "No areas defined."
                areas = sorted(areas, key=lambda a: a.get("name", ""))
                w_id = max(len("area_id"), *(len(a.get("area_id", "")) for a in areas))
                w_name = max(len("name"), *(len(a.get("name", "")) for a in areas))
                sep = f"+{'-'*(w_id+2)}+{'-'*(w_name+2)}+"
                header = f"| {'area_id':<{w_id}} | {'name':<{w_name}} |"
                lines = [sep, header, sep]
                for a in areas:
                    lines.append(f"| {a.get('area_id',''):<{w_id}} | {a.get('name',''):<{w_name}} |")
                lines.append(sep)
                return "\n".join(lines)
        except Exception:
            pass
        # Fallback via template
        result = await ha_client.get_template("{{ areas() | join('\\n') }}")
        return f"Areas:\n{result.strip()}" if result.strip() else "No areas found."

    if name == "list_floors":
        try:
            client = await ha_client._get_client()
            r = await client.get("/api/config/floor_registry/entry")
            if r.status_code == 200:
                floors = r.json()
                if not floors:
                    return "No floors defined."
                floors = sorted(floors, key=lambda f: f.get("name", ""))
                w_id = max(len("floor_id"), *(len(f.get("floor_id", "")) for f in floors))
                w_name = max(len("name"), *(len(f.get("name", "")) for f in floors))
                sep = f"+{'-'*(w_id+2)}+{'-'*(w_name+2)}+"
                header = f"| {'floor_id':<{w_id}} | {'name':<{w_name}} |"
                lines = [sep, header, sep]
                for f in floors:
                    lines.append(f"| {f.get('floor_id',''):<{w_id}} | {f.get('name',''):<{w_name}} |")
                lines.append(sep)
                return "\n".join(lines)
        except Exception:
            pass
        return "Floor registry endpoint unavailable or no floors defined."

    if name == "get_device_info":
        device_id = args["device_id"]
        try:
            client = await ha_client._get_client()
            r = await client.get(f"/api/config/device_registry/entry/{device_id}")
            if r.status_code == 200:
                device = r.json()
                return _yaml_like(device)
            return f"Device '{device_id}' not found."
        except Exception as exc:
            return f"Could not retrieve device info: {exc}"

    # --- WRITE_SOFT tools ---

    if name == "create_persistent_notification":
        message = args["message"]
        title = args.get("title", "")
        notification_id = args.get("notification_id", "")
        data: dict[str, Any] = {"message": message}
        if title:
            data["title"] = title
        if notification_id:
            data["notification_id"] = notification_id
        await ha_client.call_service("persistent_notification", "create", service_data=data)
        return f"Created persistent notification: '{title or message[:40]}'."

    if name == "dismiss_persistent_notification":
        notification_id = args["notification_id"]
        await ha_client.call_service(
            "persistent_notification", "dismiss",
            service_data={"notification_id": notification_id},
        )
        return f"Dismissed persistent notification '{notification_id}'."

    if name == "send_notification":
        service = args["service"]
        message = args["message"]
        title = args.get("title")
        target = args.get("target")
        data: dict[str, Any] = {"message": message}
        if title:
            data["title"] = title
        if target:
            data["target"] = target
        await ha_client.call_service("notify", service, service_data=data)
        return f"Sent notification via '{service}'."

    if name == "fire_event":
        event_type = args["event_type"]
        event_data = args.get("event_data") or {}
        try:
            client = await ha_client._get_client()
            r = await client.post(f"/api/events/{event_type}", json=event_data)
            r.raise_for_status()
        except Exception as exc:
            return f"Failed to fire event '{event_type}': {exc}"
        return f"Fired event '{event_type}'."

    # --- WRITE_CONFIG tools ---

    if name == "reload_core_config":
        await ha_client.reload_config(domain=None)
        return "Core configuration reloaded."

    if name == "reload_all_yaml":
        domains = [
            "automation",
            "script",
            "scene",
            "group",
            "input_boolean",
            "input_number",
            "input_select",
            "input_text",
            "input_datetime",
            "template",
            "timer",
            "counter",
        ]
        reloaded = []
        failed = []
        for domain in domains:
            try:
                await ha_client.call_service(domain, "reload")
                reloaded.append(domain)
            except Exception:
                failed.append(domain)
        result = f"Reloaded domains: {', '.join(reloaded)}."
        if failed:
            result += f"\nFailed to reload: {', '.join(failed)}."
        return result

    # --- DESTRUCTIVE tools ---

    if name == "restart_ha":
        diff_id = f"diff_{uuid.uuid4().hex[:12]}"
        return {
            "type": "diff",
            "id": diff_id,
            "path": "homeassistant/restart",
            "before": "Home Assistant is currently running.",
            "after": "Home Assistant will be restarted. All sessions will be interrupted.",
            "content": "Home Assistant will be restarted. All sessions will be interrupted.",
        }

    raise ValueError(f"Unknown system tool: {name!r}")
