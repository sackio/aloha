"""Tool registry: no duplicate names, dispatch map integrity."""

from aloha.mcp.registry import ALL_TOOLS, TOOL_MAP


def test_no_duplicate_tool_names():
    names = [t.name for t in ALL_TOOLS]
    assert len(names) == len(set(names)), "duplicate tool names in registry"


def test_expected_tool_surface():
    # Core + supervisor + docker toolsets are all registered.
    assert len(ALL_TOOLS) >= 100
    for expected in ("get_environment", "get_all_states", "docker_list_containers",
                     "list_addons", "create_backup"):
        assert expected in TOOL_MAP, f"{expected} missing from registry"


def test_every_tool_has_schema():
    for t in ALL_TOOLS:
        assert t.name
        assert isinstance(t.parameters, dict)
        assert t.parameters.get("type") == "object"
