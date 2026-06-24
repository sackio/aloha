"""
aloha/mcp/tools/automations.py

MCP tool definitions and dispatcher for Home Assistant automation operations.

Exports:
    TOOLS       — list[ToolDef]
    TOOL_NAMES  — set[str]
    execute_automations_tool(name, args, ha_client) — async dispatcher
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import yaml

from aloha.agent.types import SafetyLevel, ToolDef
from aloha.ha.client import HAClient

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[ToolDef] = [
    ToolDef(
        name="list_automations",
        description="List all automations with their id, alias, and enabled state.",
        parameters={
            "type": "object",
            "properties": {
                "enabled_only": {
                    "type": "boolean",
                    "description": "When true, only return enabled automations (default false).",
                    "default": False,
                },
                "search": {
                    "type": "string",
                    "description": "Optional filter string matched against alias.",
                },
            },
        },
        safety=SafetyLevel.READ,
        returns="Table of automation_id | alias | state | last_triggered",
    ),
    ToolDef(
        name="get_automation",
        description="Get the full YAML definition of a single automation.",
        parameters={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "The automation entity_id (e.g. 'automation.my_automation') or unique id.",
                },
            },
            "required": ["automation_id"],
        },
        safety=SafetyLevel.READ,
        returns="YAML definition of the automation",
    ),
    ToolDef(
        name="trigger_automation",
        description="Manually trigger an automation to run immediately.",
        parameters={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "The automation entity_id to trigger.",
                },
            },
            "required": ["automation_id"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="enable_automation",
        description="Enable a currently disabled automation.",
        parameters={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "The automation entity_id to enable.",
                },
            },
            "required": ["automation_id"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="disable_automation",
        description="Disable a currently enabled automation.",
        parameters={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "The automation entity_id to disable.",
                },
            },
            "required": ["automation_id"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="create_automation",
        description=(
            "Create a new automation by providing its YAML configuration. "
            "Returns a DiffEvent dict for user approval — does NOT write directly."
        ),
        parameters={
            "type": "object",
            "properties": {
                "alias": {
                    "type": "string",
                    "description": "Human-readable name for the automation.",
                },
                "config_yaml": {
                    "type": "string",
                    "description": "Full automation YAML (single automation block, not a list).",
                },
            },
            "required": ["alias", "config_yaml"],
        },
        safety=SafetyLevel.WRITE_CONFIG,
        returns="DiffEvent dict",
    ),
    ToolDef(
        name="update_automation",
        description=(
            "Update an existing automation's YAML configuration. "
            "Returns a DiffEvent dict for user approval — does NOT write directly."
        ),
        parameters={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "The automation entity_id or unique id to update.",
                },
                "config_yaml": {
                    "type": "string",
                    "description": "Full updated automation YAML.",
                },
            },
            "required": ["automation_id", "config_yaml"],
        },
        safety=SafetyLevel.WRITE_CONFIG,
        returns="DiffEvent dict",
    ),
    ToolDef(
        name="delete_automation",
        description="Permanently delete an automation. This action is irreversible.",
        parameters={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "The automation entity_id to delete.",
                },
            },
            "required": ["automation_id"],
        },
        safety=SafetyLevel.DESTRUCTIVE,
        returns="Confirmation string",
    ),
    ToolDef(
        name="reload_automations",
        description="Reload all automations from disk by calling the automation.reload service.",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="validate_automation_yaml",
        description="Validate automation YAML syntax without saving it to disk.",
        parameters={
            "type": "object",
            "properties": {
                "config_yaml": {
                    "type": "string",
                    "description": "The automation YAML to validate.",
                },
            },
            "required": ["config_yaml"],
        },
        safety=SafetyLevel.READ,
        returns="Validation result string",
    ),
]

TOOL_NAMES: set[str] = {t.name for t in TOOLS}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _automation_entity_id(automation_id: str) -> str:
    """Normalise to entity_id form."""
    if not automation_id.startswith("automation."):
        return f"automation.{automation_id}"
    return automation_id


def _diff_event(
    *,
    diff_id: str,
    path: str,
    before: str,
    after: str,
) -> dict[str, Any]:
    """Build a DiffEvent-compatible dict."""
    return {
        "type": "diff",
        "id": diff_id,
        "path": path,
        "before": before,
        "after": after,
        "content": after,
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


async def execute_automations_tool(
    name: str,
    args: dict[str, Any],
    ha_client: HAClient,
) -> Any:
    """Route to the correct automation tool implementation."""

    # --- READ tools ---

    if name == "list_automations":
        enabled_only = bool(args.get("enabled_only", False))
        search = (args.get("search") or "").lower()

        states = await ha_client.get_states()
        automations = [s for s in states if s.get("entity_id", "").startswith("automation.")]

        if enabled_only:
            automations = [a for a in automations if a.get("state") != "off"]
        if search:
            automations = [
                a for a in automations
                if search in (a.get("attributes") or {}).get("friendly_name", "").lower()
                or search in a.get("entity_id", "").lower()
            ]

        if not automations:
            return "No automations found."

        automations = sorted(automations, key=lambda a: a.get("entity_id", ""))

        # Build table
        w_id = max(len("automation_id"), *(len(a.get("entity_id", "")) for a in automations))
        w_alias = max(len("alias"), *(len((a.get("attributes") or {}).get("friendly_name", "")) for a in automations))
        w_state = max(len("state"), *(len(a.get("state", "")) for a in automations))
        w_ts = 24

        sep = f"+{'-'*(w_id+2)}+{'-'*(w_alias+2)}+{'-'*(w_state+2)}+{'-'*(w_ts+2)}+"
        header = (
            f"| {'automation_id':<{w_id}} | {'alias':<{w_alias}} "
            f"| {'state':<{w_state}} | {'last_triggered':<{w_ts}} |"
        )
        lines = [sep, header, sep]
        for a in automations:
            eid = a.get("entity_id", "")
            alias = (a.get("attributes") or {}).get("friendly_name", "")
            state = a.get("state", "")
            last_trig = (a.get("attributes") or {}).get("last_triggered", "")
            lines.append(
                f"| {eid:<{w_id}} | {alias:<{w_alias}} | {state:<{w_state}} | {str(last_trig):<{w_ts}} |"
            )
        lines.append(sep)
        return "\n".join(lines)

    if name == "get_automation":
        automation_id = _automation_entity_id(args["automation_id"])
        state = await ha_client.get_state(automation_id)
        attrs = state.get("attributes") or {}
        # Attempt to get config via /api/config/automation/config
        uid = attrs.get("id") or automation_id.removeprefix("automation.")
        try:
            client = await ha_client._get_client()
            r = await client.get(f"/api/config/automation/config/{uid}")
            if r.status_code == 200:
                config = r.json()
                return yaml.dump(config, default_flow_style=False, allow_unicode=True)
        except Exception:
            pass
        # Fallback: return state + attributes
        return yaml.dump(
            {"entity_id": automation_id, "state": state.get("state"), "attributes": attrs},
            default_flow_style=False,
            allow_unicode=True,
        )

    if name == "validate_automation_yaml":
        config_yaml = args["config_yaml"]
        try:
            parsed = yaml.safe_load(config_yaml)
        except yaml.YAMLError as exc:
            return f"YAML syntax error: {exc}"
        if not isinstance(parsed, dict):
            return "Validation error: automation config must be a YAML mapping (dict), not a list or scalar."
        required_keys = {"alias", "trigger", "action"}
        missing = required_keys - set(parsed.keys())
        if missing:
            return f"Validation warning: the following recommended top-level keys are missing: {', '.join(sorted(missing))}. YAML parsed successfully."
        return "YAML is valid. Required keys (alias, trigger, action) are present."

    # --- WRITE_SOFT tools ---

    if name == "trigger_automation":
        automation_id = _automation_entity_id(args["automation_id"])
        await ha_client.call_service(
            "automation", "trigger",
            target={"entity_id": automation_id},
        )
        return f"Triggered automation '{automation_id}'."

    if name == "enable_automation":
        automation_id = _automation_entity_id(args["automation_id"])
        await ha_client.call_service(
            "automation", "turn_on",
            target={"entity_id": automation_id},
        )
        return f"Enabled automation '{automation_id}'."

    if name == "disable_automation":
        automation_id = _automation_entity_id(args["automation_id"])
        await ha_client.call_service(
            "automation", "turn_off",
            target={"entity_id": automation_id},
        )
        return f"Disabled automation '{automation_id}'."

    if name == "reload_automations":
        await ha_client.call_service("automation", "reload")
        return "Automation reload triggered."

    # --- WRITE_CONFIG tools ---

    if name == "create_automation":
        alias = args["alias"]
        config_yaml = args["config_yaml"]

        # Validate YAML first
        try:
            parsed = yaml.safe_load(config_yaml)
        except yaml.YAMLError as exc:
            return f"YAML syntax error — automation not created: {exc}"

        # Generate a slug-style id from alias
        auto_id = alias.lower().replace(" ", "_").replace("-", "_")
        # Ensure id is in the parsed config
        if isinstance(parsed, dict) and "id" not in parsed:
            parsed["id"] = auto_id
            config_yaml = yaml.dump(parsed, default_flow_style=False, allow_unicode=True)

        diff_id = f"diff_{uuid.uuid4().hex[:12]}"
        path = f"automations/{auto_id}.yaml"
        return _diff_event(
            diff_id=diff_id,
            path=path,
            before="",
            after=config_yaml,
        )

    if name == "update_automation":
        automation_id = args["automation_id"]
        config_yaml = args["config_yaml"]

        # Validate YAML first
        try:
            yaml.safe_load(config_yaml)
        except yaml.YAMLError as exc:
            return f"YAML syntax error — automation not updated: {exc}"

        # Get existing config as "before"
        before = ""
        uid = automation_id.removeprefix("automation.")
        try:
            client = await ha_client._get_client()
            r = await client.get(f"/api/config/automation/config/{uid}")
            if r.status_code == 200:
                before = yaml.dump(r.json(), default_flow_style=False, allow_unicode=True)
        except Exception:
            pass

        diff_id = f"diff_{uuid.uuid4().hex[:12]}"
        path = f"automations/{uid}.yaml"
        return _diff_event(
            diff_id=diff_id,
            path=path,
            before=before,
            after=config_yaml,
        )

    # --- DESTRUCTIVE tools ---

    if name == "delete_automation":
        automation_id = args["automation_id"]
        uid = automation_id.removeprefix("automation.")
        try:
            client = await ha_client._get_client()
            r = await client.delete(f"/api/config/automation/config/{uid}")
            r.raise_for_status()
            return f"Deleted automation '{automation_id}'."
        except Exception as exc:
            return f"Failed to delete automation '{automation_id}': {exc}"

    raise ValueError(f"Unknown automations tool: {name!r}")
