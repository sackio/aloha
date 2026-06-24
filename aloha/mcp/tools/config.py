"""
aloha/mcp/tools/config.py

MCP tool definitions and dispatcher for Home Assistant config file operations.

Exports:
    TOOLS       — list[ToolDef]
    TOOL_NAMES  — set[str]
    execute_config_tool(name, args, ha_client, ha_config_dir) — async dispatcher

Security rules:
  - Paths to secrets.yaml and .storage/ are always denied for read and write.
  - write_config_file NEVER writes directly — it returns a DiffEvent dict.
"""

from __future__ import annotations

import fnmatch
import uuid
from pathlib import Path
from typing import Any

import yaml

from aloha.agent.types import SafetyLevel, ToolDef
from aloha.ha.client import HAClient

# ---------------------------------------------------------------------------
# Denied path patterns (relative to ha_config_dir)
# ---------------------------------------------------------------------------

_DENIED_PATTERNS = [
    "secrets.yaml",
    "secrets.yml",
    ".storage/*",
    ".storage",
]


def _is_denied(rel_path: str) -> bool:
    """Return True if the relative path matches a denied pattern."""
    for pattern in _DENIED_PATTERNS:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        if rel_path == pattern:
            return True
    return False


def _resolve_safe(ha_config_dir: Path, path: str) -> tuple[Path | None, str]:
    """
    Resolve ``path`` relative to ``ha_config_dir`` and validate it.

    Returns (resolved_path, error_message). If error_message is non-empty
    the path is rejected and resolved_path is None.
    """
    # Strip leading slashes so Path("..") tricks don't escape
    clean = path.lstrip("/")
    resolved = (ha_config_dir / clean).resolve()

    # Must stay inside ha_config_dir
    try:
        resolved.relative_to(ha_config_dir.resolve())
    except ValueError:
        return None, f"Access denied: path '{path}' is outside the HA config directory."

    rel = str(resolved.relative_to(ha_config_dir.resolve()))
    if _is_denied(rel):
        return None, f"Access denied: '{path}' is a protected file."

    return resolved, ""


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[ToolDef] = [
    ToolDef(
        name="read_config_file",
        description="Read the contents of a file from the Home Assistant configuration directory.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Path relative to the HA config directory, e.g. "
                        "'automations.yaml' or 'packages/lights.yaml'."
                    ),
                },
            },
            "required": ["path"],
        },
        safety=SafetyLevel.READ,
        returns="File contents as a string",
    ),
    ToolDef(
        name="list_config_files",
        description=(
            "List files in the Home Assistant configuration directory. "
            "Optionally filter by glob pattern (e.g. '*.yaml')."
        ),
        parameters={
            "type": "object",
            "properties": {
                "subdirectory": {
                    "type": "string",
                    "description": "Subdirectory relative to HA config dir to list (default: root).",
                },
                "glob": {
                    "type": "string",
                    "description": "Glob pattern to filter files, e.g. '*.yaml'.",
                },
            },
        },
        safety=SafetyLevel.READ,
        returns="Newline-separated list of file paths",
    ),
    ToolDef(
        name="write_config_file",
        description=(
            "Propose writing or overwriting a file in the HA configuration directory. "
            "Returns a DiffEvent dict for user approval — never writes directly. "
            "Access to secrets.yaml and .storage/ is denied."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to the HA config directory.",
                },
                "content": {
                    "type": "string",
                    "description": "New file content.",
                },
            },
            "required": ["path", "content"],
        },
        safety=SafetyLevel.WRITE_CONFIG,
        returns="DiffEvent dict",
    ),
    ToolDef(
        name="append_config_file",
        description=(
            "Propose appending content to a config file. "
            "Returns a DiffEvent dict for user approval — never writes directly."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to the HA config directory.",
                },
                "content": {
                    "type": "string",
                    "description": "Content to append.",
                },
            },
            "required": ["path", "content"],
        },
        safety=SafetyLevel.WRITE_CONFIG,
        returns="DiffEvent dict",
    ),
    ToolDef(
        name="delete_config_file",
        description=(
            "Permanently delete a file from the HA configuration directory. "
            "This action is irreversible."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to the HA config directory.",
                },
            },
            "required": ["path"],
        },
        safety=SafetyLevel.DESTRUCTIVE,
        returns="Confirmation string",
    ),
    ToolDef(
        name="check_config",
        description="Run Home Assistant's built-in configuration check and return the result.",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.READ,
        returns="Config check result string (valid or invalid with errors)",
    ),
    ToolDef(
        name="get_config_entry_list",
        description="List all Home Assistant config entries (loaded integrations).",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.READ,
        returns="Table of integration entries",
    ),
    ToolDef(
        name="reload_config_entry",
        description="Reload a specific integration config entry by domain name.",
        parameters={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Integration domain to reload, e.g. 'mqtt', 'zwave_js'.",
                },
            },
            "required": ["domain"],
        },
        safety=SafetyLevel.WRITE_SOFT,
        returns="Confirmation string",
    ),
    ToolDef(
        name="get_ha_config",
        description="Get the Home Assistant core configuration (location, units, components, etc.).",
        parameters={"type": "object", "properties": {}},
        safety=SafetyLevel.READ,
        returns="YAML-like formatted HA config",
    ),
    ToolDef(
        name="render_template",
        description="Render a Jinja2 template string using Home Assistant's template engine.",
        parameters={
            "type": "object",
            "properties": {
                "template": {
                    "type": "string",
                    "description": "Jinja2 template string to render.",
                },
            },
            "required": ["template"],
        },
        safety=SafetyLevel.READ,
        returns="Rendered template output string",
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


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


async def execute_config_tool(
    name: str,
    args: dict[str, Any],
    ha_client: HAClient,
    ha_config_dir: Path,
) -> Any:
    """Route to the correct config tool implementation."""

    # --- READ tools ---

    if name == "read_config_file":
        path_arg = args["path"]
        resolved, err = _resolve_safe(ha_config_dir, path_arg)
        if err:
            return err
        if not resolved.exists():
            return f"File not found: '{path_arg}'"
        if not resolved.is_file():
            return f"'{path_arg}' is a directory, not a file."
        return resolved.read_text(encoding="utf-8")

    if name == "list_config_files":
        subdir_arg = args.get("subdirectory") or ""
        glob_arg = args.get("glob") or "*"

        if subdir_arg:
            base, err = _resolve_safe(ha_config_dir, subdir_arg)
            if err:
                return err
        else:
            base = ha_config_dir.resolve()

        if not base.exists():
            return f"Directory not found: '{subdir_arg or '.'}'"
        if not base.is_dir():
            return f"'{subdir_arg}' is not a directory."

        files = sorted(base.glob(glob_arg))
        lines = []
        for f in files:
            rel = f.relative_to(ha_config_dir.resolve())
            rel_str = str(rel)
            if _is_denied(rel_str):
                continue
            lines.append(rel_str)

        if not lines:
            return "No files found."
        return "\n".join(lines)

    if name == "check_config":
        result = await ha_client.check_config()
        outcome = result.get("result", "unknown")
        errors = result.get("errors", "")
        if outcome == "valid":
            return "Configuration check passed: valid."
        return f"Configuration check FAILED: {outcome}\nErrors:\n{errors}"

    if name == "get_config_entry_list":
        entries = await ha_client.list_config_entries()
        if not entries:
            return "No config entries found."

        entries = sorted(entries, key=lambda e: e.get("domain", ""))
        w_domain = max(len("domain"), *(len(e.get("domain", "")) for e in entries))
        w_title = max(len("title"), *(len(e.get("title", "")) for e in entries))
        w_state = max(len("state"), *(len(e.get("state", "")) for e in entries))

        sep = f"+{'-'*(w_domain+2)}+{'-'*(w_title+2)}+{'-'*(w_state+2)}+"
        header = f"| {'domain':<{w_domain}} | {'title':<{w_title}} | {'state':<{w_state}} |"
        lines = [sep, header, sep]
        for e in entries:
            domain = e.get("domain", "")
            title = e.get("title", "")
            state = e.get("state", "")
            lines.append(f"| {domain:<{w_domain}} | {title:<{w_title}} | {state:<{w_state}} |")
        lines.append(sep)
        return "\n".join(lines)

    if name == "get_ha_config":
        config = await ha_client.get_config()
        lines = []
        for key, val in sorted(config.items()):
            if isinstance(val, (dict, list)):
                import json as _json
                lines.append(f"{key}: {_json.dumps(val)}")
            else:
                lines.append(f"{key}: {val}")
        return "\n".join(lines)

    if name == "render_template":
        template = args["template"]
        result = await ha_client.get_template(template)
        return result

    # --- WRITE_SOFT tools ---

    if name == "reload_config_entry":
        domain = args["domain"]
        await ha_client.reload_config(domain=domain)
        return f"Reloaded config entry for domain '{domain}'."

    # --- WRITE_CONFIG tools ---

    if name == "write_config_file":
        path_arg = args["path"]
        content = args["content"]
        resolved, err = _resolve_safe(ha_config_dir, path_arg)
        if err:
            return err

        before = ""
        if resolved.exists() and resolved.is_file():
            before = resolved.read_text(encoding="utf-8")

        abs_path = str(resolved)
        diff_id = f"diff_{uuid.uuid4().hex[:12]}"
        return _diff_event(
            diff_id=diff_id,
            path=abs_path,
            before=before,
            after=content,
        )

    if name == "append_config_file":
        path_arg = args["path"]
        content = args["content"]
        resolved, err = _resolve_safe(ha_config_dir, path_arg)
        if err:
            return err

        before = ""
        if resolved.exists() and resolved.is_file():
            before = resolved.read_text(encoding="utf-8")

        # Ensure a newline separator between existing content and appended content
        if before and not before.endswith("\n"):
            after = before + "\n" + content
        else:
            after = before + content

        abs_path = str(resolved)
        diff_id = f"diff_{uuid.uuid4().hex[:12]}"
        return _diff_event(
            diff_id=diff_id,
            path=abs_path,
            before=before,
            after=after,
        )

    # --- DESTRUCTIVE tools ---

    if name == "delete_config_file":
        path_arg = args["path"]
        resolved, err = _resolve_safe(ha_config_dir, path_arg)
        if err:
            return err
        if not resolved.exists():
            return f"File not found: '{path_arg}'"
        if not resolved.is_file():
            return f"'{path_arg}' is not a file."
        resolved.unlink()
        return f"Deleted '{path_arg}'."

    raise ValueError(f"Unknown config tool: {name!r}")
