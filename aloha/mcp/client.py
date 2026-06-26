"""
aloha/mcp/client.py

MCP *client* manager — lets the Aloha agent consume EXTERNAL MCP servers and
expose their tools alongside the built-in Home Assistant tools.

(Aloha also *exposes* its own tools as an MCP server in aloha/mcp/server.py; this
module is the other direction — Aloha as an MCP client.)

Configuration: a JSON file at ``{data_dir}/mcp_servers.json``:

    {
      "servers": [
        {"name": "websearch", "transport": "streamable_http",
         "url": "http://localhost:9100/mcp"},
        {"name": "filesystem", "transport": "stdio",
         "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/data"]}
      ]
    }

External tools are namespaced ``mcp__<server>__<tool>`` so they never collide with
built-in tools, and so the agent loop can route their execution here. A server
that fails to connect is skipped — it never breaks the agent.
"""

from __future__ import annotations

import json
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from aloha.agent.types import SafetyLevel, ToolDef

log = logging.getLogger(__name__)

_PREFIX = "mcp__"


@dataclass
class MCPServerConfig:
    name: str
    transport: str = "streamable_http"  # "streamable_http" | "sse" | "stdio"
    url: str = ""
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


def load_mcp_server_configs(data_dir: Path) -> list[MCPServerConfig]:
    """Read external MCP server definitions from {data_dir}/mcp_servers.json."""
    path = Path(data_dir) / "mcp_servers.json"
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        log.warning("Could not parse %s", path, exc_info=True)
        return []

    servers = raw.get("servers", raw if isinstance(raw, list) else [])
    configs: list[MCPServerConfig] = []
    for s in servers:
        try:
            configs.append(
                MCPServerConfig(
                    name=s["name"],
                    transport=s.get("transport", "streamable_http"),
                    url=s.get("url", ""),
                    command=s.get("command", ""),
                    args=list(s.get("args", [])),
                    env=dict(s.get("env", {})),
                )
            )
        except Exception:
            log.warning("Skipping malformed MCP server entry: %r", s, exc_info=True)
    return configs


def tool_name(server: str, tool: str) -> str:
    return f"{_PREFIX}{server}__{tool}"


def is_mcp_tool(name: str) -> bool:
    return name.startswith(_PREFIX)


class MCPClientManager:
    """
    Connects to configured external MCP servers, aggregates their tools, and
    dispatches tool calls to the owning server. Sessions are opened once at
    start() and reused; a failed server is skipped, not fatal.
    """

    def __init__(self, configs: list[MCPServerConfig]) -> None:
        self._configs = configs
        self._stack = AsyncExitStack()
        self._sessions: dict[str, Any] = {}          # server name -> ClientSession
        self._tools: list[ToolDef] = []              # aggregated external ToolDefs
        self._route: dict[str, tuple[str, str]] = {} # prefixed name -> (server, original)
        self._started = False

    # ------------------------------------------------------------------
    async def start(self) -> None:
        """Connect to every configured server (best-effort) and gather tools."""
        if self._started:
            return
        self._started = True
        for cfg in self._configs:
            try:
                await self._connect_one(cfg)
            except Exception:
                log.warning("MCP server %r failed to connect; skipping", cfg.name, exc_info=True)
        if self._tools:
            log.info(
                "MCP client: %d external tool(s) from %d server(s): %s",
                len(self._tools), len(self._sessions), ", ".join(sorted(self._sessions)),
            )

    async def _connect_one(self, cfg: MCPServerConfig) -> None:
        from mcp import ClientSession

        if cfg.transport in ("streamable_http", "http"):
            from mcp.client.streamable_http import streamablehttp_client
            read, write, *_ = await self._stack.enter_async_context(streamablehttp_client(cfg.url))
        elif cfg.transport == "sse":
            from mcp.client.sse import sse_client
            read, write = await self._stack.enter_async_context(sse_client(cfg.url))
        elif cfg.transport == "stdio":
            from mcp.client.stdio import StdioServerParameters, stdio_client
            params = StdioServerParameters(command=cfg.command, args=cfg.args, env=cfg.env or None)
            read, write = await self._stack.enter_async_context(stdio_client(params))
        else:
            raise ValueError(f"Unknown MCP transport: {cfg.transport!r}")

        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._sessions[cfg.name] = session

        listed = await session.list_tools()
        for t in listed.tools:
            pname = tool_name(cfg.name, t.name)
            self._tools.append(
                ToolDef(
                    name=pname,
                    description=f"[{cfg.name}] {t.description or t.name}",
                    parameters=t.inputSchema or {"type": "object", "properties": {}},
                    safety=SafetyLevel.WRITE_SOFT,  # external; not config-diff gated
                    returns="str",
                )
            )
            self._route[pname] = (cfg.name, t.name)

    # ------------------------------------------------------------------
    def tools(self) -> list[ToolDef]:
        return list(self._tools)

    def owns(self, name: str) -> bool:
        return name in self._route

    async def call_tool(self, name: str, args: dict[str, Any]) -> str:
        """Dispatch a prefixed tool call to the owning external server."""
        if name not in self._route:
            raise ValueError(f"Unknown MCP tool: {name!r}")
        server, original = self._route[name]
        session = self._sessions[server]
        result = await session.call_tool(original, args or {})

        # Flatten content blocks (TextContent etc.) into a string.
        parts: list[str] = []
        for block in getattr(result, "content", []) or []:
            text = getattr(block, "text", None)
            parts.append(text if text is not None else str(block))
        out = "\n".join(parts) if parts else "(no content)"
        if getattr(result, "isError", False):
            return f"Error from {server}: {out}"
        return out

    async def stop(self) -> None:
        try:
            await self._stack.aclose()
        except Exception:
            log.debug("Error closing MCP client sessions", exc_info=True)
        self._sessions.clear()
        self._started = False


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_manager: Optional[MCPClientManager] = None


def init_mcp_manager(data_dir: Path) -> MCPClientManager:
    """Create (not yet started) the singleton from {data_dir}/mcp_servers.json."""
    global _manager
    _manager = MCPClientManager(load_mcp_server_configs(data_dir))
    return _manager


def get_mcp_manager() -> Optional[MCPClientManager]:
    """Return the singleton, or None if external MCP support isn't initialised."""
    return _manager
