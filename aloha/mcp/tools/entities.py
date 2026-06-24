"""
aloha/mcp/tools/entities.py

MCP tool definitions and dispatcher for Home Assistant entity operations.

Exports:
    TOOLS       — list[ToolDef]
    TOOL_NAMES  — set[str]
    execute_entities_tool(name, args, ha_client) — async dispatcher
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from aloha.agent.types import SafetyLevel, ToolDef
from aloha.ha.client import HAClient

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[ToolDef] = [
    ToolDef(
        name="get_entity_state",
        description="Get the current state and all attributes of a single entity.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity_id to look up, e.g. 'light.kitchen_main'.",
                },
            },
            "required": ["entity_id"],
        },
        safety=SafetyLevel.READ,
        returns="YAML-like formatted string of entity state and attributes",
    ),
    ToolDef(
        name="get_all_states",
        description="Get states for all entities in Home Assistant.",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.READ,
        returns="Table of entity_id | domain | state for all entities",
    ),
    ToolDef(
        name="get_entities_by_domain",
        description="Get all entities belonging to a specific domain (e.g. 'light', 'switch', 'sensor').",
        parameters={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain name, e.g. 'light', 'switch', 'climate'.",
                },
            },
            "required": ["domain"],
        },
        safety=SafetyLevel.READ,
        returns="Table of entity_id | name | state for the domain",
    ),
    ToolDef(
        name="get_entities_by_area",
        description="Get all entities assigned to a named area.",
        parameters={
            "type": "object",
            "properties": {
                "area_name": {
                    "type": "string",
                    "description": "The area name (case-insensitive), e.g. 'Kitchen'.",
                },
            },
            "required": ["area_name"],
        },
        safety=SafetyLevel.READ,
        returns="Table of entity_id | name | state for the area",
    ),
    ToolDef(
        name="search_entities",
        description="Full-text search entities by entity_id or friendly name.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search string matched against entity_id and friendly_name.",
                },
            },
            "required": ["query"],
        },
        safety=SafetyLevel.READ,
        returns="Table of matching entities",
    ),
    ToolDef(
        name="get_entity_history",
        description="Get state history for an entity over a time range.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity_id to look up.",
                },
                "hours": {
                    "type": "number",
                    "description": "How many hours of history to retrieve (default 24).",
                    "default": 24,
                },
            },
            "required": ["entity_id"],
        },
        safety=SafetyLevel.READ,
        returns="Chronological list of state changes",
    ),
    ToolDef(
        name="get_entity_logbook",
        description="Get logbook entries for an entity over a time range.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity_id to look up.",
                },
                "hours": {
                    "type": "number",
                    "description": "How many hours of logbook entries to retrieve (default 24).",
                    "default": 24,
                },
            },
            "required": ["entity_id"],
        },
        safety=SafetyLevel.READ,
        returns="Chronological logbook entries for the entity",
    ),
    ToolDef(
        name="turn_on",
        description="Turn on a light, switch, fan, or other entity.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity_id to turn on.",
                },
            },
            "required": ["entity_id"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="turn_off",
        description="Turn off a light, switch, fan, or other entity.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity_id to turn off.",
                },
            },
            "required": ["entity_id"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="toggle",
        description="Toggle a light, switch, or other entity between on and off.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity_id to toggle.",
                },
            },
            "required": ["entity_id"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="set_light_brightness",
        description="Set light brightness (0–255, where 255 is full brightness).",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The light entity_id.",
                },
                "brightness": {
                    "type": "integer",
                    "description": "Brightness level 0–255.",
                    "minimum": 0,
                    "maximum": 255,
                },
            },
            "required": ["entity_id", "brightness"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="set_light_color",
        description="Set light RGB color.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The light entity_id.",
                },
                "r": {"type": "integer", "description": "Red component 0–255.", "minimum": 0, "maximum": 255},
                "g": {"type": "integer", "description": "Green component 0–255.", "minimum": 0, "maximum": 255},
                "b": {"type": "integer", "description": "Blue component 0–255.", "minimum": 0, "maximum": 255},
            },
            "required": ["entity_id", "r", "g", "b"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="set_light_color_temp",
        description="Set light color temperature in mireds (lower = cooler/bluer, higher = warmer/yellower).",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The light entity_id.",
                },
                "color_temp": {
                    "type": "integer",
                    "description": "Color temperature in mireds (typically 153–500).",
                },
            },
            "required": ["entity_id", "color_temp"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="set_cover_position",
        description="Set cover or blind position (0 = fully closed, 100 = fully open).",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The cover entity_id.",
                },
                "position": {
                    "type": "integer",
                    "description": "Position 0–100.",
                    "minimum": 0,
                    "maximum": 100,
                },
            },
            "required": ["entity_id", "position"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="set_climate_temperature",
        description="Set thermostat target temperature.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The climate entity_id.",
                },
                "temperature": {
                    "type": "number",
                    "description": "Target temperature in the unit configured in HA.",
                },
            },
            "required": ["entity_id", "temperature"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="set_climate_hvac_mode",
        description="Set thermostat HVAC mode (e.g. 'heat', 'cool', 'auto', 'off').",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The climate entity_id.",
                },
                "hvac_mode": {
                    "type": "string",
                    "description": "HVAC mode: 'heat', 'cool', 'heat_cool', 'auto', 'dry', 'fan_only', 'off'.",
                },
            },
            "required": ["entity_id", "hvac_mode"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="set_fan_speed",
        description="Set fan speed as a percentage (0–100).",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The fan entity_id.",
                },
                "percentage": {
                    "type": "integer",
                    "description": "Speed percentage 0–100.",
                    "minimum": 0,
                    "maximum": 100,
                },
            },
            "required": ["entity_id", "percentage"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="lock_entity",
        description="Lock a lock entity.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The lock entity_id.",
                },
            },
            "required": ["entity_id"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="unlock_entity",
        description="Unlock a lock entity.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The lock entity_id.",
                },
            },
            "required": ["entity_id"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="run_script",
        description="Execute a Home Assistant script entity.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The script entity_id, e.g. 'script.goodnight'.",
                },
                "variables": {
                    "type": "object",
                    "description": "Optional variables to pass to the script.",
                },
            },
            "required": ["entity_id"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="call_service_raw",
        description="Call any Home Assistant service with arbitrary service data.",
        parameters={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Service domain, e.g. 'light', 'switch', 'homeassistant'.",
                },
                "service": {
                    "type": "string",
                    "description": "Service name, e.g. 'turn_on', 'toggle'.",
                },
                "entity_id": {
                    "type": "string",
                    "description": "Optional target entity_id.",
                },
                "area_id": {
                    "type": "string",
                    "description": "Optional target area_id.",
                },
                "data": {
                    "type": "object",
                    "description": "Optional additional service data.",
                },
            },
            "required": ["domain", "service"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="List of affected entity states as JSON",
    ),
]

TOOL_NAMES: set[str] = {t.name for t in TOOLS}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_entity_table(states: list[dict[str, Any]]) -> str:
    """Format a list of entity state dicts as a fixed-width table."""
    if not states:
        return "No entities found."

    rows: list[tuple[str, str, str, str]] = []
    for s in states:
        eid = s.get("entity_id", "")
        domain = eid.split(".")[0] if "." in eid else ""
        name = (s.get("attributes") or {}).get("friendly_name", "")
        state = s.get("state", "")
        rows.append((eid, name, state, domain))

    # Column widths
    w_eid = max(len("entity_id"), *(len(r[0]) for r in rows))
    w_name = max(len("name"), *(len(r[1]) for r in rows))
    w_state = max(len("state"), *(len(r[2]) for r in rows))
    w_domain = max(len("domain"), *(len(r[3]) for r in rows))

    sep = f"+{'-'*(w_eid+2)}+{'-'*(w_name+2)}+{'-'*(w_state+2)}+{'-'*(w_domain+2)}+"
    header = f"| {'entity_id':<{w_eid}} | {'name':<{w_name}} | {'state':<{w_state}} | {'domain':<{w_domain}} |"

    lines = [sep, header, sep]
    for eid, name, state, domain in rows:
        lines.append(f"| {eid:<{w_eid}} | {name:<{w_name}} | {state:<{w_state}} | {domain:<{w_domain}} |")
    lines.append(sep)
    return "\n".join(lines)


def _format_state_detail(state: dict[str, Any]) -> str:
    """Format a single entity state dict as a YAML-like string."""
    entity_id = state.get("entity_id", "unknown")
    current_state = state.get("state", "unknown")
    last_changed = state.get("last_changed", "")
    last_updated = state.get("last_updated", "")
    attrs = state.get("attributes") or {}

    lines = [
        f"entity_id: {entity_id}",
        f"state: {current_state}",
        f"last_changed: {last_changed}",
        f"last_updated: {last_updated}",
        "attributes:",
    ]
    for key, val in sorted(attrs.items()):
        if isinstance(val, (dict, list)):
            lines.append(f"  {key}: {json.dumps(val)}")
        else:
            lines.append(f"  {key}: {val}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


async def execute_entities_tool(
    name: str,
    args: dict[str, Any],
    ha_client: HAClient,
) -> Any:
    """Route to the correct entity tool implementation."""

    # --- READ tools ---

    if name == "get_entity_state":
        state = await ha_client.get_state(args["entity_id"])
        return _format_state_detail(state)

    if name == "get_all_states":
        states = await ha_client.get_states()
        states_sorted = sorted(states, key=lambda s: s.get("entity_id", ""))
        return _format_entity_table(states_sorted)

    if name == "get_entities_by_domain":
        domain = args["domain"].lower()
        states = await ha_client.get_states()
        filtered = [s for s in states if s.get("entity_id", "").split(".")[0] == domain]
        if not filtered:
            return f"No entities found in domain '{domain}'."
        return _format_entity_table(sorted(filtered, key=lambda s: s.get("entity_id", "")))

    if name == "get_entities_by_area":
        area_name = args["area_name"].lower()
        # HA REST API does not expose area membership on /api/states directly,
        # so we use /api/states and match friendly_name or entity_registry area.
        # Best effort: search entity registry via template.
        template = (
            "{% set ns = namespace(result=[]) %}"
            "{% for state in states %}"
            "{% set area = area_name(state.entity_id) %}"
            f"{{% if area and area | lower == '{area_name}' %}}"
            "{% set ns.result = ns.result + [state.entity_id + '|' + state.name + '|' + state.state] %}"
            "{% endif %}"
            "{% endfor %}"
            "{{ ns.result | join('\\n') }}"
        )
        try:
            result = await ha_client.get_template(template)
            result = result.strip()
            if not result:
                return f"No entities found in area '{args['area_name']}'."
            lines = [f"Entities in area '{args['area_name']}':", ""]
            w_eid = 40
            w_name = 30
            w_state = 20
            sep = f"+{'-'*(w_eid+2)}+{'-'*(w_name+2)}+{'-'*(w_state+2)}+"
            header = f"| {'entity_id':<{w_eid}} | {'name':<{w_name}} | {'state':<{w_state}} |"
            lines += [sep, header, sep]
            for row in result.split("\n"):
                parts = row.split("|")
                if len(parts) == 3:
                    eid, n, s = parts
                    lines.append(f"| {eid:<{w_eid}} | {n:<{w_name}} | {s:<{w_state}} |")
            lines.append(sep)
            return "\n".join(lines)
        except Exception:
            # Fallback: filter by name match in attributes
            states = await ha_client.get_states()
            filtered = [
                s for s in states
                if (s.get("attributes") or {}).get("friendly_name", "").lower().startswith(area_name)
            ]
            return _format_entity_table(filtered) if filtered else f"No entities found in area '{args['area_name']}'."

    if name == "search_entities":
        query = args["query"].lower()
        states = await ha_client.get_states()
        matched = [
            s for s in states
            if query in s.get("entity_id", "").lower()
            or query in (s.get("attributes") or {}).get("friendly_name", "").lower()
        ]
        if not matched:
            return f"No entities matched query '{args['query']}'."
        return _format_entity_table(sorted(matched, key=lambda s: s.get("entity_id", "")))

    if name == "get_entity_history":
        entity_id = args["entity_id"]
        hours = float(args.get("hours", 24))
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=hours)
        start_iso = start.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        history = await ha_client.get_history(
            entity_ids=[entity_id],
            start_time=start_iso,
        )
        if not history or not history[0]:
            return f"No history found for '{entity_id}' in the last {hours:.0f} hours."
        entries = history[0]
        lines = [f"History for {entity_id} (last {hours:.0f}h) — {len(entries)} state changes:", ""]
        for entry in entries:
            ts = entry.get("last_changed", entry.get("last_updated", ""))
            state = entry.get("state", "")
            lines.append(f"  {ts}  →  {state}")
        return "\n".join(lines)

    if name == "get_entity_logbook":
        entity_id = args["entity_id"]
        hours = float(args.get("hours", 24))
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=hours)
        start_iso = start.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        entries = await ha_client.get_logbook(
            entity_ids=[entity_id],
            start_time=start_iso,
        )
        if not entries:
            return f"No logbook entries found for '{entity_id}' in the last {hours:.0f} hours."
        lines = [f"Logbook for {entity_id} (last {hours:.0f}h) — {len(entries)} entries:", ""]
        for entry in entries:
            ts = entry.get("when", "")
            msg = entry.get("message", "")
            name_str = entry.get("name", "")
            lines.append(f"  {ts}  {name_str}: {msg}")
        return "\n".join(lines)

    # --- WRITE_SOFT tools ---

    if name == "turn_on":
        entity_id = args["entity_id"]
        domain = entity_id.split(".")[0]
        await ha_client.call_service(domain, "turn_on", target={"entity_id": entity_id})
        return f"Turned on {entity_id}."

    if name == "turn_off":
        entity_id = args["entity_id"]
        domain = entity_id.split(".")[0]
        await ha_client.call_service(domain, "turn_off", target={"entity_id": entity_id})
        return f"Turned off {entity_id}."

    if name == "toggle":
        entity_id = args["entity_id"]
        domain = entity_id.split(".")[0]
        await ha_client.call_service(domain, "toggle", target={"entity_id": entity_id})
        return f"Toggled {entity_id}."

    if name == "set_light_brightness":
        entity_id = args["entity_id"]
        brightness = int(args["brightness"])
        await ha_client.call_service(
            "light", "turn_on",
            service_data={"brightness": brightness},
            target={"entity_id": entity_id},
        )
        return f"Set brightness of {entity_id} to {brightness}."

    if name == "set_light_color":
        entity_id = args["entity_id"]
        r, g, b = int(args["r"]), int(args["g"]), int(args["b"])
        await ha_client.call_service(
            "light", "turn_on",
            service_data={"rgb_color": [r, g, b]},
            target={"entity_id": entity_id},
        )
        return f"Set color of {entity_id} to rgb({r}, {g}, {b})."

    if name == "set_light_color_temp":
        entity_id = args["entity_id"]
        color_temp = int(args["color_temp"])
        await ha_client.call_service(
            "light", "turn_on",
            service_data={"color_temp": color_temp},
            target={"entity_id": entity_id},
        )
        return f"Set color temperature of {entity_id} to {color_temp} mireds."

    if name == "set_cover_position":
        entity_id = args["entity_id"]
        position = int(args["position"])
        await ha_client.call_service(
            "cover", "set_cover_position",
            service_data={"position": position},
            target={"entity_id": entity_id},
        )
        return f"Set position of {entity_id} to {position}%."

    if name == "set_climate_temperature":
        entity_id = args["entity_id"]
        temperature = float(args["temperature"])
        await ha_client.call_service(
            "climate", "set_temperature",
            service_data={"temperature": temperature},
            target={"entity_id": entity_id},
        )
        return f"Set target temperature of {entity_id} to {temperature}."

    if name == "set_climate_hvac_mode":
        entity_id = args["entity_id"]
        hvac_mode = args["hvac_mode"]
        await ha_client.call_service(
            "climate", "set_hvac_mode",
            service_data={"hvac_mode": hvac_mode},
            target={"entity_id": entity_id},
        )
        return f"Set HVAC mode of {entity_id} to '{hvac_mode}'."

    if name == "set_fan_speed":
        entity_id = args["entity_id"]
        percentage = int(args["percentage"])
        await ha_client.call_service(
            "fan", "set_percentage",
            service_data={"percentage": percentage},
            target={"entity_id": entity_id},
        )
        return f"Set fan speed of {entity_id} to {percentage}%."

    if name == "lock_entity":
        entity_id = args["entity_id"]
        await ha_client.call_service("lock", "lock", target={"entity_id": entity_id})
        return f"Locked {entity_id}."

    if name == "unlock_entity":
        entity_id = args["entity_id"]
        await ha_client.call_service("lock", "unlock", target={"entity_id": entity_id})
        return f"Unlocked {entity_id}."

    if name == "run_script":
        entity_id = args["entity_id"]
        variables = args.get("variables") or {}
        script_id = entity_id.removeprefix("script.")
        await ha_client.call_service(
            "script", "turn_on",
            service_data={"variables": variables} if variables else None,
            target={"entity_id": entity_id},
        )
        return f"Executed script '{script_id}'."

    if name == "call_service_raw":
        domain = args["domain"]
        service = args["service"]
        entity_id = args.get("entity_id")
        area_id = args.get("area_id")
        data = args.get("data") or {}

        target: dict[str, Any] = {}
        if entity_id:
            target["entity_id"] = entity_id
        if area_id:
            target["area_id"] = area_id

        result = await ha_client.call_service(
            domain, service,
            service_data=data if data else None,
            target=target if target else None,
        )
        if result:
            return json.dumps(result, indent=2)
        return f"Called {domain}.{service} successfully."

    raise ValueError(f"Unknown entities tool: {name!r}")
