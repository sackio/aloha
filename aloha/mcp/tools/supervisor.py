"""
aloha/mcp/tools/supervisor.py

Home Assistant *Supervisor* tools — available on HAOS / Supervised installs
(where a SUPERVISOR_TOKEN is injected). These let the agent manage the SYSTEM:
update HA Core / OS / Supervisor, manage add-ons, and take/restore backups.

Every tool returns a clear "not available" message when there's no Supervisor
(e.g. plain-Docker installs), so the agent can fall back to the Docker toolset.

Exports: TOOLS, TOOL_NAMES, execute_supervisor_tool(name, args)
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from aloha.agent.types import SafetyLevel, ToolDef
from aloha.ha.environment import SUPERVISOR_URL, detect_environment, has_supervisor, supervisor_token

TOOLS: list[ToolDef] = [
    ToolDef(name="get_environment", description="Detect the HA environment (haos / docker / core) and which system-management path is available. Call this BEFORE upgrading/backing up so you use the right tools.",
            parameters={"type": "object", "properties": {}}, safety=SafetyLevel.READ),
    ToolDef(name="get_supervisor_info", description="Get Supervisor info (version, channel, healthy state). HAOS/Supervised only.",
            parameters={"type": "object", "properties": {}}, safety=SafetyLevel.READ),
    ToolDef(name="get_core_info", description="Get HA Core info: current version and whether an update is available. HAOS/Supervised only.",
            parameters={"type": "object", "properties": {}}, safety=SafetyLevel.READ),
    ToolDef(name="get_os_info", description="Get Home Assistant OS info: version and available OS update. HAOS only.",
            parameters={"type": "object", "properties": {}}, safety=SafetyLevel.READ),
    ToolDef(name="check_updates", description="Check for available Core / OS / Supervisor updates in one call. HAOS/Supervised only.",
            parameters={"type": "object", "properties": {}}, safety=SafetyLevel.READ),
    ToolDef(name="list_addons", description="List installed add-ons (slug, name, version, state, update available). HAOS/Supervised only.",
            parameters={"type": "object", "properties": {}}, safety=SafetyLevel.READ),
    ToolDef(name="search_addons", description="Search the add-on store for available add-ons by name/description.",
            parameters={"type": "object", "properties": {"query": {"type": "string", "description": "Optional filter."}}}, safety=SafetyLevel.READ),
    ToolDef(name="get_addon_info", description="Get details for one add-on by slug.",
            parameters={"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}, safety=SafetyLevel.READ),
    ToolDef(name="get_addon_logs", description="Get recent logs for an add-on by slug.",
            parameters={"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}, safety=SafetyLevel.READ),
    ToolDef(name="list_backups", description="List system backups (slug, name, date, size). HAOS/Supervised only.",
            parameters={"type": "object", "properties": {}}, safety=SafetyLevel.READ),
    # writes
    ToolDef(name="start_addon", description="Start an add-on by slug.",
            parameters={"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}, safety=SafetyLevel.WRITE_SOFT),
    ToolDef(name="stop_addon", description="Stop an add-on by slug.",
            parameters={"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}, safety=SafetyLevel.WRITE_SOFT),
    ToolDef(name="restart_addon", description="Restart an add-on by slug.",
            parameters={"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}, safety=SafetyLevel.WRITE_SOFT),
    ToolDef(name="install_addon", description="Install an add-on from the store by slug.",
            parameters={"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}, safety=SafetyLevel.WRITE_CONFIG),
    ToolDef(name="update_addon", description="Update an installed add-on to the latest version by slug.",
            parameters={"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}, safety=SafetyLevel.WRITE_CONFIG),
    ToolDef(name="create_backup", description="Create a full system backup. HAOS/Supervised only.",
            parameters={"type": "object", "properties": {"name": {"type": "string", "description": "Backup name."}}}, safety=SafetyLevel.WRITE_SOFT),
    ToolDef(name="update_core", description="Update Home Assistant Core to the latest version. Restarts HA. HAOS/Supervised only.",
            parameters={"type": "object", "properties": {}}, safety=SafetyLevel.DESTRUCTIVE),
    ToolDef(name="update_supervisor", description="Update the Supervisor to the latest version. HAOS/Supervised only.",
            parameters={"type": "object", "properties": {}}, safety=SafetyLevel.DESTRUCTIVE),
    ToolDef(name="update_os", description="Update Home Assistant OS to the latest version. Reboots the host. HAOS only.",
            parameters={"type": "object", "properties": {}}, safety=SafetyLevel.DESTRUCTIVE),
    ToolDef(name="uninstall_addon", description="Uninstall an add-on by slug (removes it).",
            parameters={"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}, safety=SafetyLevel.DESTRUCTIVE),
    ToolDef(name="restore_backup", description="Restore a full system backup by slug. Overwrites current state. HAOS/Supervised only.",
            parameters={"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}, safety=SafetyLevel.DESTRUCTIVE),
    ToolDef(name="reboot_host", description="Reboot the host machine. HAOS only.",
            parameters={"type": "object", "properties": {}}, safety=SafetyLevel.DESTRUCTIVE),
]

TOOL_NAMES: set[str] = {t.name for t in TOOLS}


async def _sup(method: str, path: str, json_body: dict | None = None) -> dict:
    """Call the Supervisor API. Raises RuntimeError with a clean message on failure."""
    token = supervisor_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.request(method, f"{SUPERVISOR_URL}{path}", headers=headers, json=json_body)
    if r.status_code >= 400:
        raise RuntimeError(f"Supervisor {method} {path} -> HTTP {r.status_code}: {r.text[:200]}")
    try:
        return r.json()
    except Exception:
        return {"raw": r.text}


def _data(resp: dict) -> Any:
    """Supervisor responses wrap payloads in {'result': 'ok', 'data': {...}}."""
    return resp.get("data", resp)


async def execute_supervisor_tool(name: str, args: dict[str, Any]) -> str:
    if name == "get_environment":
        return json.dumps(detect_environment(), indent=2)

    if not has_supervisor():
        return ("This is a Supervisor tool, but no Supervisor was found (not a HAOS/Supervised "
                "install). On plain Docker, use the docker_* tools to manage the HA container instead.")

    try:
        if name == "get_supervisor_info":
            return json.dumps(_data(await _sup("GET", "/supervisor/info")), indent=2)[:4000]
        if name == "get_core_info":
            return json.dumps(_data(await _sup("GET", "/core/info")), indent=2)[:4000]
        if name == "get_os_info":
            return json.dumps(_data(await _sup("GET", "/os/info")), indent=2)[:4000]
        if name == "check_updates":
            core = _data(await _sup("GET", "/core/info"))
            out = {"core": {"version": core.get("version"), "latest": core.get("version_latest"),
                            "update_available": core.get("update_available")}}
            try:
                osi = _data(await _sup("GET", "/os/info"))
                out["os"] = {"version": osi.get("version"), "latest": osi.get("version_latest"),
                             "update_available": osi.get("update_available")}
            except Exception:
                pass
            sup = _data(await _sup("GET", "/supervisor/info"))
            out["supervisor"] = {"version": sup.get("version"), "latest": sup.get("version_latest"),
                                 "update_available": sup.get("update_available")}
            return json.dumps(out, indent=2)
        if name == "list_addons":
            data = _data(await _sup("GET", "/addons"))
            addons = data.get("addons", data) if isinstance(data, dict) else data
            rows = [{"slug": a.get("slug"), "name": a.get("name"), "version": a.get("version"),
                     "state": a.get("state"), "update_available": a.get("update_available")} for a in addons]
            return json.dumps(rows, indent=2)[:4000] or "No add-ons installed."
        if name == "search_addons":
            q = (args.get("query") or "").lower()
            data = _data(await _sup("GET", "/store"))
            addons = data.get("addons", []) if isinstance(data, dict) else data
            rows = [{"slug": a.get("slug"), "name": a.get("name"), "description": a.get("description")}
                    for a in addons if not q or q in (a.get("name", "") + a.get("description", "")).lower()]
            return json.dumps(rows[:40], indent=2)[:4000] or "No matching add-ons."
        if name == "get_addon_info":
            return json.dumps(_data(await _sup("GET", f"/addons/{args['slug']}/info")), indent=2)[:4000]
        if name == "get_addon_logs":
            resp = await _sup("GET", f"/addons/{args['slug']}/logs")
            return str(resp.get("raw", resp))[:4000]
        if name == "list_backups":
            data = _data(await _sup("GET", "/backups"))
            backups = data.get("backups", data) if isinstance(data, dict) else data
            return json.dumps(backups, indent=2)[:4000] or "No backups."
        if name in ("start_addon", "stop_addon", "restart_addon"):
            action = name.split("_")[0]
            await _sup("POST", f"/addons/{args['slug']}/{action}")
            return f"{action.capitalize()}ed add-on '{args['slug']}'."
        if name == "install_addon":
            await _sup("POST", f"/store/addons/{args['slug']}/install")
            return f"Installed add-on '{args['slug']}'."
        if name == "update_addon":
            await _sup("POST", f"/addons/{args['slug']}/update")
            return f"Updated add-on '{args['slug']}'."
        if name == "uninstall_addon":
            await _sup("POST", f"/addons/{args['slug']}/uninstall")
            return f"Uninstalled add-on '{args['slug']}'."
        if name == "create_backup":
            body = {"name": args.get("name") or "Aloha backup"}
            resp = _data(await _sup("POST", "/backups/new/full", body))
            return f"Backup created: {resp.get('slug', 'ok')}"
        if name == "restore_backup":
            await _sup("POST", f"/backups/{args['slug']}/restore/full")
            return f"Restore of backup '{args['slug']}' started."
        if name == "update_core":
            await _sup("POST", "/core/update")
            return "HA Core update started (HA will restart)."
        if name == "update_supervisor":
            await _sup("POST", "/supervisor/update")
            return "Supervisor update started."
        if name == "update_os":
            await _sup("POST", "/os/update")
            return "HA OS update started (host will reboot)."
        if name == "reboot_host":
            await _sup("POST", "/host/reboot")
            return "Host reboot started."
    except RuntimeError as exc:
        return f"Error: {exc}"

    raise ValueError(f"Unknown supervisor tool: {name!r}")
