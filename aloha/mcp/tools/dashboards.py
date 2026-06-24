"""
aloha/mcp/tools/dashboards.py

MCP tool definitions and dispatcher for Home Assistant Lovelace dashboard operations.

Exports:
    TOOLS       — list[ToolDef]
    TOOL_NAMES  — set[str]
    execute_dashboards_tool(name, args, ha_client) — async dispatcher
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
        name="list_dashboards",
        description="List all Lovelace dashboards configured in Home Assistant.",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.READ,
        returns="Table of dashboard url_path | title | mode",
    ),
    ToolDef(
        name="get_dashboard",
        description="Get the full YAML configuration for a Lovelace dashboard.",
        parameters={
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "Dashboard url_path identifier (default: 'lovelace' for the main dashboard).",
                    "default": "lovelace",
                },
            },
        },
        safety=SafetyLevel.READ,
        returns="Dashboard YAML configuration as string",
    ),
    ToolDef(
        name="get_dashboard_view",
        description="Get the configuration for a single view within a dashboard.",
        parameters={
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "Dashboard url_path identifier (default: 'lovelace').",
                    "default": "lovelace",
                },
                "view_index": {
                    "type": "integer",
                    "description": "Zero-based index of the view to retrieve.",
                    "default": 0,
                },
            },
        },
        safety=SafetyLevel.READ,
        returns="View YAML configuration as string",
    ),
    ToolDef(
        name="create_dashboard",
        description=(
            "Create a new Lovelace dashboard. "
            "Returns a DiffEvent dict for user approval — does not write directly."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url_path": {
                    "type": "string",
                    "description": "URL path for the new dashboard (e.g. 'energy').",
                },
                "title": {
                    "type": "string",
                    "description": "Human-readable title.",
                },
                "config_yaml": {
                    "type": "string",
                    "description": "Full Lovelace YAML configuration for the dashboard.",
                },
            },
            "required": ["url_path", "title", "config_yaml"],
        },
        safety=SafetyLevel.WRITE_CONFIG,
        returns="DiffEvent dict",
    ),
    ToolDef(
        name="update_dashboard",
        description=(
            "Update the configuration of an existing Lovelace dashboard. "
            "Returns a DiffEvent dict for user approval — does not write directly."
        ),
        parameters={
            "type": "object",
            "properties": {
                "config_yaml": {
                    "type": "string",
                    "description": "New full Lovelace YAML configuration.",
                },
                "dashboard_id": {
                    "type": "string",
                    "description": "Dashboard url_path to update (default: 'lovelace').",
                    "default": "lovelace",
                },
            },
            "required": ["config_yaml"],
        },
        safety=SafetyLevel.WRITE_CONFIG,
        returns="DiffEvent dict",
    ),
    ToolDef(
        name="delete_dashboard",
        description="Permanently delete a Lovelace dashboard. This action is irreversible.",
        parameters={
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "Dashboard url_path to delete.",
                },
            },
            "required": ["dashboard_id"],
        },
        safety=SafetyLevel.DESTRUCTIVE,
        returns="Confirmation string",
    ),
    ToolDef(
        name="add_card_to_view",
        description=(
            "Add a card to a specific view in a dashboard. "
            "Returns a DiffEvent dict for user approval."
        ),
        parameters={
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "Dashboard url_path (default: 'lovelace').",
                    "default": "lovelace",
                },
                "view_index": {
                    "type": "integer",
                    "description": "Zero-based index of the view to add the card to.",
                    "default": 0,
                },
                "card_yaml": {
                    "type": "string",
                    "description": "YAML definition of the card to add.",
                },
            },
            "required": ["card_yaml"],
        },
        safety=SafetyLevel.WRITE_CONFIG,
        returns="DiffEvent dict",
    ),
    ToolDef(
        name="update_card",
        description=(
            "Update an existing card in a dashboard view. "
            "Returns a DiffEvent dict for user approval."
        ),
        parameters={
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "Dashboard url_path (default: 'lovelace').",
                    "default": "lovelace",
                },
                "view_index": {
                    "type": "integer",
                    "description": "Zero-based view index.",
                    "default": 0,
                },
                "card_index": {
                    "type": "integer",
                    "description": "Zero-based card index within the view.",
                },
                "card_yaml": {
                    "type": "string",
                    "description": "New YAML definition for the card.",
                },
            },
            "required": ["card_index", "card_yaml"],
        },
        safety=SafetyLevel.WRITE_CONFIG,
        returns="DiffEvent dict",
    ),
    ToolDef(
        name="remove_card",
        description="Remove a card from a dashboard view. This action is irreversible.",
        parameters={
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "Dashboard url_path (default: 'lovelace').",
                    "default": "lovelace",
                },
                "view_index": {
                    "type": "integer",
                    "description": "Zero-based view index.",
                    "default": 0,
                },
                "card_index": {
                    "type": "integer",
                    "description": "Zero-based card index within the view.",
                },
            },
            "required": ["card_index"],
        },
        safety=SafetyLevel.DESTRUCTIVE,
        returns="Confirmation string",
    ),
]

TOOL_NAMES: set[str] = {t.name for t in TOOLS}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _diff_event(
    *,
    diff_id: str,
    path: str,
    before: str,
    after: str,
) -> dict[str, Any]:
    return {
        "type": "diff",
        "id": diff_id,
        "path": path,
        "before": before,
        "after": after,
        "content": after,
    }


async def _get_lovelace_config(
    ha_client: HAClient,
    dashboard_id: str = "lovelace",
) -> dict[str, Any] | None:
    """Fetch raw Lovelace config dict from HA."""
    try:
        client = await ha_client._get_client()
        # Try storage-based Lovelace API
        path = f"/api/lovelace/config"
        if dashboard_id and dashboard_id != "lovelace":
            path = f"/api/lovelace/config/{dashboard_id}"
        r = await client.get(path)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


async def execute_dashboards_tool(
    name: str,
    args: dict[str, Any],
    ha_client: HAClient,
) -> Any:
    """Route to the correct dashboards tool implementation."""

    # --- READ tools ---

    if name == "list_dashboards":
        try:
            client = await ha_client._get_client()
            r = await client.get("/api/lovelace/dashboards")
            if r.status_code == 200:
                dashboards = r.json()
                if not dashboards:
                    return "Only the default Lovelace dashboard is configured."

                # Always include default
                rows = [("lovelace", "Home", "storage")]
                for d in dashboards:
                    rows.append((
                        d.get("url_path", ""),
                        d.get("title", ""),
                        d.get("mode", ""),
                    ))

                w_path = max(len("url_path"), *(len(r[0]) for r in rows))
                w_title = max(len("title"), *(len(r[1]) for r in rows))
                w_mode = max(len("mode"), *(len(r[2]) for r in rows))
                sep = f"+{'-'*(w_path+2)}+{'-'*(w_title+2)}+{'-'*(w_mode+2)}+"
                header = f"| {'url_path':<{w_path}} | {'title':<{w_title}} | {'mode':<{w_mode}} |"
                lines = [sep, header, sep]
                for path_val, title, mode in rows:
                    lines.append(f"| {path_val:<{w_path}} | {title:<{w_title}} | {mode:<{w_mode}} |")
                lines.append(sep)
                return "\n".join(lines)
        except Exception:
            pass
        return "lovelace (default dashboard)"

    if name == "get_dashboard":
        dashboard_id = args.get("dashboard_id") or "lovelace"
        config = await _get_lovelace_config(ha_client, dashboard_id)
        if config is None:
            return f"Could not retrieve dashboard '{dashboard_id}'. It may not exist or may use yaml mode."
        return yaml.dump(config, default_flow_style=False, allow_unicode=True)

    if name == "get_dashboard_view":
        dashboard_id = args.get("dashboard_id") or "lovelace"
        view_index = int(args.get("view_index", 0))
        config = await _get_lovelace_config(ha_client, dashboard_id)
        if config is None:
            return f"Could not retrieve dashboard '{dashboard_id}'."
        views = config.get("views", [])
        if not views:
            return f"Dashboard '{dashboard_id}' has no views."
        if view_index >= len(views):
            return f"Dashboard '{dashboard_id}' only has {len(views)} view(s) (index {view_index} out of range)."
        return yaml.dump(views[view_index], default_flow_style=False, allow_unicode=True)

    # --- WRITE_CONFIG tools ---

    if name == "create_dashboard":
        url_path = args["url_path"]
        title = args["title"]
        config_yaml = args["config_yaml"]

        try:
            yaml.safe_load(config_yaml)
        except yaml.YAMLError as exc:
            return f"YAML syntax error: {exc}"

        diff_id = f"diff_{uuid.uuid4().hex[:12]}"
        return _diff_event(
            diff_id=diff_id,
            path=f"lovelace/{url_path}",
            before="",
            after=config_yaml,
        )

    if name == "update_dashboard":
        config_yaml = args["config_yaml"]
        dashboard_id = args.get("dashboard_id") or "lovelace"

        try:
            yaml.safe_load(config_yaml)
        except yaml.YAMLError as exc:
            return f"YAML syntax error: {exc}"

        # Get current config as "before"
        before = ""
        current = await _get_lovelace_config(ha_client, dashboard_id)
        if current is not None:
            before = yaml.dump(current, default_flow_style=False, allow_unicode=True)

        diff_id = f"diff_{uuid.uuid4().hex[:12]}"
        return _diff_event(
            diff_id=diff_id,
            path=f"lovelace/{dashboard_id}",
            before=before,
            after=config_yaml,
        )

    if name == "add_card_to_view":
        dashboard_id = args.get("dashboard_id") or "lovelace"
        view_index = int(args.get("view_index", 0))
        card_yaml = args["card_yaml"]

        try:
            card = yaml.safe_load(card_yaml)
        except yaml.YAMLError as exc:
            return f"YAML syntax error in card definition: {exc}"

        config = await _get_lovelace_config(ha_client, dashboard_id)
        if config is None:
            return f"Could not retrieve dashboard '{dashboard_id}'."

        before = yaml.dump(config, default_flow_style=False, allow_unicode=True)

        views = config.get("views", [])
        if view_index >= len(views):
            return f"View index {view_index} out of range (dashboard has {len(views)} view(s))."

        cards = views[view_index].get("cards", [])
        cards.append(card)
        views[view_index]["cards"] = cards
        config["views"] = views

        after = yaml.dump(config, default_flow_style=False, allow_unicode=True)
        diff_id = f"diff_{uuid.uuid4().hex[:12]}"
        return _diff_event(
            diff_id=diff_id,
            path=f"lovelace/{dashboard_id}",
            before=before,
            after=after,
        )

    if name == "update_card":
        dashboard_id = args.get("dashboard_id") or "lovelace"
        view_index = int(args.get("view_index", 0))
        card_index = int(args["card_index"])
        card_yaml = args["card_yaml"]

        try:
            new_card = yaml.safe_load(card_yaml)
        except yaml.YAMLError as exc:
            return f"YAML syntax error in card definition: {exc}"

        config = await _get_lovelace_config(ha_client, dashboard_id)
        if config is None:
            return f"Could not retrieve dashboard '{dashboard_id}'."

        before = yaml.dump(config, default_flow_style=False, allow_unicode=True)

        views = config.get("views", [])
        if view_index >= len(views):
            return f"View index {view_index} out of range."
        cards = views[view_index].get("cards", [])
        if card_index >= len(cards):
            return f"Card index {card_index} out of range (view has {len(cards)} card(s))."

        cards[card_index] = new_card
        views[view_index]["cards"] = cards
        config["views"] = views

        after = yaml.dump(config, default_flow_style=False, allow_unicode=True)
        diff_id = f"diff_{uuid.uuid4().hex[:12]}"
        return _diff_event(
            diff_id=diff_id,
            path=f"lovelace/{dashboard_id}",
            before=before,
            after=after,
        )

    # --- DESTRUCTIVE tools ---

    if name == "delete_dashboard":
        dashboard_id = args["dashboard_id"]
        try:
            client = await ha_client._get_client()
            r = await client.delete(f"/api/lovelace/dashboards/{dashboard_id}")
            r.raise_for_status()
            return f"Deleted dashboard '{dashboard_id}'."
        except Exception as exc:
            return f"Failed to delete dashboard '{dashboard_id}': {exc}"

    if name == "remove_card":
        dashboard_id = args.get("dashboard_id") or "lovelace"
        view_index = int(args.get("view_index", 0))
        card_index = int(args["card_index"])

        config = await _get_lovelace_config(ha_client, dashboard_id)
        if config is None:
            return f"Could not retrieve dashboard '{dashboard_id}'."

        views = config.get("views", [])
        if view_index >= len(views):
            return f"View index {view_index} out of range."
        cards = views[view_index].get("cards", [])
        if card_index >= len(cards):
            return f"Card index {card_index} out of range (view has {len(cards)} card(s))."

        removed = cards.pop(card_index)
        views[view_index]["cards"] = cards
        config["views"] = views

        # Write the updated config directly (DESTRUCTIVE — no diff gate)
        try:
            client = await ha_client._get_client()
            url = "/api/lovelace/config"
            if dashboard_id != "lovelace":
                url = f"/api/lovelace/config/{dashboard_id}"
            r = await client.post(url, json=config)
            r.raise_for_status()
        except Exception as exc:
            return f"Removed card from local config but failed to save: {exc}"

        removed_type = removed.get("type", "unknown") if isinstance(removed, dict) else "unknown"
        return f"Removed card (type: {removed_type}) at index {card_index} from view {view_index} of '{dashboard_id}'."

    raise ValueError(f"Unknown dashboards tool: {name!r}")
