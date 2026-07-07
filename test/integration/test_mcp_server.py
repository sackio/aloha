"""The MCP server exposes the tool registry (list) and can format a call."""

from aloha.config import AlohaConfig
from aloha.mcp.registry import ALL_TOOLS


def test_registry_covers_all_toolsets(data_dir):
    # Sanity: the aggregate registry is what the MCP server advertises.
    names = {t.name for t in ALL_TOOLS}
    assert len(names) == len(ALL_TOOLS)
    assert "get_environment" in names


def test_mcp_server_builds(data_dir):
    from aloha.mcp.server import create_mcp_server
    cfg = AlohaConfig.load()
    server, transport = create_mcp_server(cfg)
    assert server is not None
    assert transport is not None
