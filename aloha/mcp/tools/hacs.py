"""
aloha/mcp/tools/hacs.py

MCP tool definitions and dispatcher for HACS (Home Assistant Community Store) operations.

Exports:
    TOOLS       — list[ToolDef]
    TOOL_NAMES  — set[str]
    execute_hacs_tool(name, args, ha_client) — async dispatcher

All tools handle 404 (HACS not installed) gracefully.
"""

from __future__ import annotations

from typing import Any

import httpx

from aloha.agent.types import SafetyLevel, ToolDef
from aloha.ha.client import HAClient

_HACS_NOT_INSTALLED = (
    "HACS is not installed — install HACS first. "
    "See https://hacs.xyz/docs/setup/download for installation instructions."
)

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[ToolDef] = [
    ToolDef(
        name="hacs_is_installed",
        description="Check whether HACS is installed and accessible in Home Assistant.",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.READ,
        returns="String indicating whether HACS is installed",
    ),
    ToolDef(
        name="hacs_list_installed",
        description="List all repositories currently installed via HACS.",
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": (
                        "Filter by category: 'integration', 'plugin', 'theme', "
                        "'python_script', 'appdaemon', 'netdaemon'. "
                        "Omit to list all."
                    ),
                },
            },
        },
        safety=SafetyLevel.READ,
        returns="Table of installed HACS repositories",
    ),
    ToolDef(
        name="hacs_list_available",
        description="Search available HACS repositories by keyword and optional category.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string matched against repository name and description.",
                },
                "category": {
                    "type": "string",
                    "description": "Category filter: 'integration', 'plugin', 'theme', etc. (default: 'integration').",
                    "default": "integration",
                },
            },
            "required": ["query"],
        },
        safety=SafetyLevel.READ,
        returns="Table of matching available repositories",
    ),
    ToolDef(
        name="hacs_get_repository_info",
        description="Get detailed information for a specific HACS repository.",
        parameters={
            "type": "object",
            "properties": {
                "repository": {
                    "type": "string",
                    "description": "Repository full name, e.g. 'hacs-integrations/pyscript'.",
                },
            },
            "required": ["repository"],
        },
        safety=SafetyLevel.READ,
        returns="Repository detail as formatted string",
    ),
    ToolDef(
        name="hacs_install_repository",
        description=(
            "Install a HACS repository. "
            "This is a DESTRUCTIVE action that may require a Home Assistant restart."
        ),
        parameters={
            "type": "object",
            "properties": {
                "repository": {
                    "type": "string",
                    "description": "Repository full name, e.g. 'custom-components/hacs'.",
                },
                "category": {
                    "type": "string",
                    "description": "Category: 'integration', 'plugin', 'theme', etc. (default: 'integration').",
                    "default": "integration",
                },
            },
            "required": ["repository"],
        },
        safety=SafetyLevel.DESTRUCTIVE,
        returns="Confirmation string",
    ),
    ToolDef(
        name="hacs_uninstall_repository",
        description=(
            "Uninstall a HACS repository. "
            "This is a DESTRUCTIVE action that may require a Home Assistant restart."
        ),
        parameters={
            "type": "object",
            "properties": {
                "repository": {
                    "type": "string",
                    "description": "Repository full name to uninstall.",
                },
            },
            "required": ["repository"],
        },
        safety=SafetyLevel.DESTRUCTIVE,
        returns="Confirmation string",
    ),
    ToolDef(
        name="hacs_update_repository",
        description="Update a HACS repository to the latest available version.",
        parameters={
            "type": "object",
            "properties": {
                "repository": {
                    "type": "string",
                    "description": "Repository full name to update.",
                },
            },
            "required": ["repository"],
        },
        safety=SafetyLevel.WRITE_CONFIG,
        returns="Confirmation string",
    ),
    ToolDef(
        name="hacs_list_pending_updates",
        description="List all HACS repositories that have available updates.",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.READ,
        returns="Table of repositories with pending updates",
    ),
]

TOOL_NAMES: set[str] = {t.name for t in TOOLS}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _hacs_get(ha_client: HAClient, path: str) -> tuple[int, Any]:
    """
    Make a GET request to a HACS API endpoint.
    Returns (status_code, body). Body is parsed JSON or None.
    """
    try:
        client = await ha_client._get_client()
        r = await client.get(path)
        if r.status_code == 404:
            return 404, None
        r.raise_for_status()
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return 404, None
        raise


async def _hacs_post(ha_client: HAClient, path: str, data: dict[str, Any] | None = None) -> tuple[int, Any]:
    """POST to a HACS API endpoint. Returns (status_code, body)."""
    try:
        client = await ha_client._get_client()
        r = await client.post(path, json=data or {})
        if r.status_code == 404:
            return 404, None
        r.raise_for_status()
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return 404, None
        raise


def _repo_table(repos: list[dict[str, Any]]) -> str:
    """Format a list of HACS repository dicts as a table."""
    if not repos:
        return "No repositories found."

    rows = [(
        r.get("name", r.get("full_name", "")),
        r.get("category", ""),
        r.get("installed_version", r.get("version", "")),
        r.get("available_version", ""),
        r.get("description", "")[:60],
    ) for r in repos]

    w_name = max(len("name"), *(len(r[0]) for r in rows))
    w_cat = max(len("category"), *(len(r[1]) for r in rows))
    w_iv = max(len("installed"), *(len(r[2]) for r in rows))
    w_av = max(len("available"), *(len(r[3]) for r in rows))
    w_desc = max(len("description"), *(len(r[4]) for r in rows))

    sep = f"+{'-'*(w_name+2)}+{'-'*(w_cat+2)}+{'-'*(w_iv+2)}+{'-'*(w_av+2)}+{'-'*(w_desc+2)}+"
    header = (
        f"| {'name':<{w_name}} | {'category':<{w_cat}} "
        f"| {'installed':<{w_iv}} | {'available':<{w_av}} | {'description':<{w_desc}} |"
    )
    lines = [sep, header, sep]
    for name, cat, iv, av, desc in rows:
        lines.append(
            f"| {name:<{w_name}} | {cat:<{w_cat}} | {iv:<{w_iv}} | {av:<{w_av}} | {desc:<{w_desc}} |"
        )
    lines.append(sep)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


async def execute_hacs_tool(
    name: str,
    args: dict[str, Any],
    ha_client: HAClient,
) -> Any:
    """Route to the correct HACS tool implementation."""

    if name == "hacs_is_installed":
        status, body = await _hacs_get(ha_client, "/api/hacs/info")
        if status == 404:
            return _HACS_NOT_INSTALLED
        if body:
            version = body.get("version", "unknown") if isinstance(body, dict) else "unknown"
            return f"HACS is installed (version {version})."
        return "HACS appears to be installed."

    if name == "hacs_list_installed":
        category = args.get("category", "")
        path = "/api/hacs/repositories"
        if category:
            path = f"/api/hacs/repositories?category={category}"
        status, body = await _hacs_get(ha_client, path)
        if status == 404:
            return _HACS_NOT_INSTALLED
        if not body:
            return "No installed HACS repositories found."
        installed = [r for r in body if r.get("installed")] if isinstance(body, list) else []
        if not installed:
            return "No installed repositories found."
        return _repo_table(installed)

    if name == "hacs_list_available":
        query = args["query"].lower()
        category = args.get("category") or "integration"
        status, body = await _hacs_get(ha_client, f"/api/hacs/repositories?category={category}")
        if status == 404:
            return _HACS_NOT_INSTALLED
        if not body or not isinstance(body, list):
            return f"No repositories found for category '{category}'."
        matched = [
            r for r in body
            if query in r.get("name", "").lower()
            or query in r.get("full_name", "").lower()
            or query in r.get("description", "").lower()
        ]
        if not matched:
            return f"No repositories matched '{query}' in category '{category}'."
        return _repo_table(matched[:50])  # cap at 50 results

    if name == "hacs_get_repository_info":
        repository = args["repository"]
        status, body = await _hacs_get(ha_client, "/api/hacs/repositories")
        if status == 404:
            return _HACS_NOT_INSTALLED
        if not body or not isinstance(body, list):
            return "Could not retrieve HACS repository list."
        repo_name_lower = repository.lower()
        match = next(
            (r for r in body
             if r.get("full_name", "").lower() == repo_name_lower
             or r.get("name", "").lower() == repo_name_lower),
            None,
        )
        if match is None:
            return f"Repository '{repository}' not found in HACS."
        lines = []
        for key, val in sorted(match.items()):
            lines.append(f"{key}: {val}")
        return "\n".join(lines)

    if name == "hacs_install_repository":
        repository = args["repository"]
        category = args.get("category") or "integration"
        status, body = await _hacs_post(
            ha_client,
            "/api/hacs/repository/install",
            {"repository": repository, "category": category},
        )
        if status == 404:
            return _HACS_NOT_INSTALLED
        return f"Installed HACS repository '{repository}' (category: {category}). A Home Assistant restart may be required."

    if name == "hacs_uninstall_repository":
        repository = args["repository"]
        status, body = await _hacs_post(
            ha_client,
            "/api/hacs/repository/remove",
            {"repository": repository},
        )
        if status == 404:
            return _HACS_NOT_INSTALLED
        return f"Uninstalled HACS repository '{repository}'. A Home Assistant restart may be required."

    if name == "hacs_update_repository":
        repository = args["repository"]
        status, body = await _hacs_post(
            ha_client,
            "/api/hacs/repository/update",
            {"repository": repository},
        )
        if status == 404:
            return _HACS_NOT_INSTALLED
        return f"Updated HACS repository '{repository}' to the latest version."

    if name == "hacs_list_pending_updates":
        status, body = await _hacs_get(ha_client, "/api/hacs/repositories")
        if status == 404:
            return _HACS_NOT_INSTALLED
        if not body or not isinstance(body, list):
            return "Could not retrieve HACS repository list."
        pending = [
            r for r in body
            if r.get("installed")
            and r.get("available_version")
            and r.get("installed_version") != r.get("available_version")
        ]
        if not pending:
            return "All installed HACS repositories are up to date."
        return _repo_table(pending)

    raise ValueError(f"Unknown HACS tool: {name!r}")
