"""
aloha/mcp/registry.py

Aggregates all MCP tool modules into a single registry and provides
a unified async dispatcher.

Exports:
    ALL_TOOLS   — list[ToolDef]  (all 74 tools in declaration order)
    TOOL_MAP    — dict[str, ToolDef]
    execute_tool(name, args, ha_client, ha_config_dir) — async dispatcher
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aloha.agent.types import ToolDef
from aloha.ha.client import HAClient

from aloha.mcp.tools.automations import (
    TOOLS as AUTOMATION_TOOLS,
    TOOL_NAMES as AUTOMATION_TOOL_NAMES,
    execute_automations_tool,
)
from aloha.mcp.tools.config import (
    TOOLS as CONFIG_TOOLS,
    TOOL_NAMES as CONFIG_TOOL_NAMES,
    execute_config_tool,
)
from aloha.mcp.tools.dashboards import (
    TOOLS as DASHBOARD_TOOLS,
    TOOL_NAMES as DASHBOARD_TOOL_NAMES,
    execute_dashboards_tool,
)
from aloha.mcp.tools.entities import (
    TOOLS as ENTITY_TOOLS,
    TOOL_NAMES as ENTITY_TOOL_NAMES,
    execute_entities_tool,
)
from aloha.mcp.tools.hacs import (
    TOOLS as HACS_TOOLS,
    TOOL_NAMES as HACS_TOOL_NAMES,
    execute_hacs_tool,
)
from aloha.mcp.tools.system import (
    TOOLS as SYSTEM_TOOLS,
    TOOL_NAMES as SYSTEM_TOOL_NAMES,
    execute_system_tool,
)
from aloha.mcp.tools.skills import (
    TOOLS as SKILL_TOOLS,
    TOOL_NAMES as SKILL_TOOL_NAMES,
    execute_skills_tool,
)

# ---------------------------------------------------------------------------
# Aggregate all tools
# ---------------------------------------------------------------------------

ALL_TOOLS: list[ToolDef] = [
    *ENTITY_TOOLS,
    *AUTOMATION_TOOLS,
    *CONFIG_TOOLS,
    *SYSTEM_TOOLS,
    *DASHBOARD_TOOLS,
    *HACS_TOOLS,
    *SKILL_TOOLS,
]

TOOL_MAP: dict[str, ToolDef] = {tool.name: tool for tool in ALL_TOOLS}

# Validate: no duplicate names across modules
_all_names = [tool.name for tool in ALL_TOOLS]
_unique_names = set(_all_names)
if len(_all_names) != len(_unique_names):
    _seen: set[str] = set()
    _dupes = [n for n in _all_names if n in _seen or _seen.add(n)]  # type: ignore[func-returns-value]
    raise RuntimeError(f"Duplicate tool names detected in registry: {_dupes}")

# ---------------------------------------------------------------------------
# Unified dispatcher
# ---------------------------------------------------------------------------


async def execute_tool(
    name: str,
    args: dict[str, Any],
    ha_client: HAClient,
    ha_config_dir: Path,
) -> Any:
    """
    Route a tool call to the correct module dispatcher.

    Parameters
    ----------
    name : str
        Tool name as registered in TOOL_MAP.
    args : dict[str, Any]
        Arguments for the tool call (validated by the caller).
    ha_client : HAClient
        Initialized Home Assistant client.
    ha_config_dir : Path
        Path to the HA configuration directory (used by config tools).

    Returns
    -------
    Any
        Tool result. Typically a string, but WRITE_CONFIG and DESTRUCTIVE tools
        may return a DiffEvent-compatible dict.

    Raises
    ------
    ValueError
        If the tool name is not registered.
    """
    if name not in TOOL_MAP:
        raise ValueError(
            f"Tool '{name}' is not registered. "
            f"Available tools: {sorted(TOOL_MAP.keys())}"
        )

    if name in ENTITY_TOOL_NAMES:
        return await execute_entities_tool(name, args, ha_client)

    if name in AUTOMATION_TOOL_NAMES:
        return await execute_automations_tool(name, args, ha_client, ha_config_dir)

    if name in CONFIG_TOOL_NAMES:
        return await execute_config_tool(name, args, ha_client, ha_config_dir)

    if name in SYSTEM_TOOL_NAMES:
        return await execute_system_tool(name, args, ha_client)

    if name in DASHBOARD_TOOL_NAMES:
        return await execute_dashboards_tool(name, args, ha_client)

    if name in HACS_TOOL_NAMES:
        return await execute_hacs_tool(name, args, ha_client)

    if name in SKILL_TOOL_NAMES:
        return await execute_skills_tool(name, args)

    # Should never reach here given the TOOL_MAP check above, but be defensive.
    raise ValueError(f"Tool '{name}' is registered but has no dispatcher.")
