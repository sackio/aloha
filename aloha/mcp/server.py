"""
aloha/mcp/server.py

MCP (Model Context Protocol) server for Aloha.

External AI clients (e.g. Claude Desktop, Cursor, Continue) can connect to
the /mcp SSE endpoint exposed by the FastAPI app to use all 74 Aloha tools
directly without going through the chat interface.

Usage (from the FastAPI lifespan or router)
-------------------------------------------
    from aloha.mcp.server import create_mcp_server

    mcp_server, sse_transport = create_mcp_server(config)

    # Mount SSE transport inside FastAPI app:
    @app.get("/mcp")
    async def mcp_sse_endpoint(request: Request):
        return await sse_transport.handle_sse(request, mcp_server)

    @app.post("/mcp/messages")
    async def mcp_messages_endpoint(request: Request):
        return await sse_transport.handle_post_message(request, mcp_server)

The server is stateless: each SSE connection gets a fresh session.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
)

from aloha.config import AlohaConfig
from aloha.ha.client import get_ha_client
from aloha.mcp.registry import ALL_TOOLS, TOOL_MAP, execute_tool

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_mcp_server(config: AlohaConfig) -> tuple[Server, SseServerTransport]:
    """
    Create and configure the MCP server and its SSE transport.

    Parameters
    ----------
    config : AlohaConfig
        Runtime configuration (used for server metadata and safety_mode).

    Returns
    -------
    (server, sse_transport)
        *server* — the configured mcp.server.Server instance.
        *sse_transport* — the SSE transport; mount at /mcp in FastAPI.
    """
    server = Server("aloha")
    sse_transport = SseServerTransport("/mcp/messages/")

    # ------------------------------------------------------------------
    # list_tools handler
    # ------------------------------------------------------------------

    @server.list_tools()
    async def handle_list_tools() -> ListToolsResult:
        """Return all registered Aloha tools in MCP Tool format."""
        mcp_tools: list[Tool] = []
        for tool_def in ALL_TOOLS:
            mcp_tools.append(
                Tool(
                    name=tool_def.name,
                    description=_annotate_description(tool_def.description, tool_def.safety.value),
                    inputSchema=tool_def.parameters or {"type": "object", "properties": {}},
                )
            )
        return ListToolsResult(tools=mcp_tools)

    # ------------------------------------------------------------------
    # call_tool handler
    # ------------------------------------------------------------------

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
        """
        Dispatch a tool call from an external MCP client.

        DiffEvent results (proposed file writes) are returned as text
        describing the proposed change — external MCP clients are not part
        of the Aloha approval flow, so they see the diff content as plain
        text and must apply it themselves.
        """
        if name not in TOOL_MAP:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name!r}")],
                isError=True,
            )

        tool_def = TOOL_MAP[name]

        # Safety gate: in strict mode, refuse WRITE_SOFT / WRITE_CONFIG /
        # DESTRUCTIVE from external MCP clients.
        if config.safety_mode == "strict" and tool_def.safety.value != "read":
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=(
                            f"Tool '{name}' is not available in strict safety mode "
                            f"for external MCP clients. Change ALOHA_SAFETY_MODE to "
                            f"'normal' or 'permissive' to allow write operations."
                        ),
                    )
                ],
                isError=True,
            )

        try:
            ha_client = get_ha_client()
        except RuntimeError as exc:
            return CallToolResult(
                content=[TextContent(type="text", text=f"HA client not ready: {exc}")],
                isError=True,
            )

        try:
            result = await execute_tool(name, arguments, ha_client, config.ha_config_dir)
        except Exception as exc:
            log.warning("MCP tool %r raised: %s", name, exc)
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {exc}")],
                isError=True,
            )

        # DiffEvent dict — return the proposed content as text for MCP clients
        if isinstance(result, dict) and result.get("type") == "diff":
            text = (
                f"Proposed change to {result.get('path', '?')}:\n\n"
                f"--- before ---\n{result.get('before', '')}\n\n"
                f"+++ after +++\n{result.get('after', '')}"
            )
            return CallToolResult(
                content=[TextContent(type="text", text=text)],
                isError=False,
            )

        # Plain string result
        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
            isError=False,
        )

    return server, sse_transport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _annotate_description(description: str, safety: str) -> str:
    """
    Append a safety-level annotation to the tool description so that
    external MCP clients understand the risk level.
    """
    badges = {
        "read": "[READ-ONLY]",
        "write_soft": "[WRITE: runtime state]",
        "write_config": "[WRITE: config files — requires approval]",
        "destructive": "[DESTRUCTIVE — requires approval]",
    }
    badge = badges.get(safety, "")
    if badge:
        return f"{description} {badge}"
    return description
