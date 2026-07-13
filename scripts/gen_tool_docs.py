#!/usr/bin/env python3
"""
Regenerate docs/MCP_TOOLS.md from the live tool registry.

    python3 scripts/gen_tool_docs.py

Keeps the published tool reference in lockstep with the code — run it whenever
tools are added, removed, or re-described.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aloha.mcp.registry import ALL_TOOLS
from aloha.mcp.tools import (
    automations,
    config as cfgmod,
    dashboards,
    docker_ops,
    entities,
    hacs,
    skills,
    supervisor,
    system,
)

GROUPS = [
    ("Entities & devices", entities.TOOLS),
    ("Automations, scripts & scenes", automations.TOOLS),
    ("Configuration files", cfgmod.TOOLS),
    ("Dashboards", dashboards.TOOLS),
    ("HACS", hacs.TOOLS),
    ("System & diagnostics", system.TOOLS),
    ("Skills", skills.TOOLS),
    ("Supervisor (HAOS/Supervised)", supervisor.TOOLS),
    ("Docker", docker_ops.TOOLS),
]


def main() -> None:
    lines = ["# MCP tool reference\n"]
    lines.append(
        f"Aloha exposes **{len(ALL_TOOLS)} tools** over the Model Context Protocol "
        "(and to its own agent). Each tool has a *safety level* — reads are always "
        "allowed; writes are shown as a diff for your approval (in `supervised` "
        "safety mode) before anything is written.\n"
    )
    lines.append("> Auto-generated from the tool registry. Regenerate: `python3 scripts/gen_tool_docs.py`.\n")
    seen = set()
    for title, tools in GROUPS:
        if not tools:
            continue
        lines.append(f"\n## {title}\n")
        lines.append("| Tool | Safety | Description |")
        lines.append("|---|---|---|")
        for t in tools:
            seen.add(t.name)
            safe = getattr(t.safety, "value", str(t.safety))
            desc = (t.description or "").replace("\n", " ").replace("|", "\\|")
            lines.append(f"| `{t.name}` | {safe} | {desc} |")

    out = Path(__file__).resolve().parent.parent / "docs" / "MCP_TOOLS.md"
    out.write_text("\n".join(lines) + "\n")
    missing = {t.name for t in ALL_TOOLS} - seen
    print(f"wrote {out} — {len(seen)}/{len(ALL_TOOLS)} tools", f"(ungrouped: {missing})" if missing else "")


if __name__ == "__main__":
    main()
