#!/usr/bin/env python3
"""
validate_supervisor.py — exercise the Supervisor toolset against a real HAOS.

Run this INSIDE the HAOS environment where a SUPERVISOR_TOKEN is available —
i.e. from within the Aloha add-on container (`docker exec` into it) or any
context that has the token. It calls every read-only supervisor tool and a
safe subset of writes, printing pass/fail so we can confirm supervisor.py works
against a live Supervisor API (not just the built-to-spec assumption).

    # inside the add-on container:
    python3 validate_supervisor.py

    # or point it at a token explicitly:
    SUPERVISOR_TOKEN=xxxx python3 validate_supervisor.py

By default it runs ONLY read tools (safe). Pass --with-backup to also create a
test backup (a real, but harmless, write) and list it back.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

# Allow running from the repo without installing.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from aloha.ha.environment import detect_environment, has_supervisor  # noqa: E402
from aloha.mcp.tools.supervisor import execute_supervisor_tool  # noqa: E402

READ_TOOLS = [
    ("get_environment", {}),
    ("get_supervisor_info", {}),
    ("get_core_info", {}),
    ("get_os_info", {}),
    ("check_updates", {}),
    ("list_addons", {}),
    ("search_addons", {"query": "terminal"}),
    ("list_backups", {}),
]


async def _run(name: str, args: dict) -> bool:
    try:
        out = await execute_supervisor_tool(name, args)
    except Exception as exc:  # noqa: BLE001
        print(f"  ✗ {name}: raised {type(exc).__name__}: {exc}")
        return False
    snippet = out.replace("\n", " ")[:120]
    ok = not out.lower().startswith("error")
    print(f"  {'✓' if ok else '✗'} {name}: {snippet}")
    return ok


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-backup", action="store_true", help="also create+list a real backup")
    args = ap.parse_args()

    env = detect_environment()
    print(f"Environment: kind={env['kind']} supervisor={env['supervisor']} "
          f"can_manage_system={env['can_manage_system']}")
    if not has_supervisor():
        print("!! No SUPERVISOR_TOKEN / Supervisor found. Run this inside the HAOS "
              "add-on container, or set SUPERVISOR_TOKEN. Only get_environment will pass.")

    print("\n== Read tools ==")
    results = []
    for name, a in READ_TOOLS:
        results.append(await _run(name, a))

    # Drill into the first installed add-on for the by-slug read tools.
    if has_supervisor():
        addons_json = await execute_supervisor_tool("list_addons", {})
        import json
        try:
            addons = json.loads(addons_json)
        except Exception:
            addons = []
        if addons:
            slug = addons[0]["slug"]
            print(f"\n== By-slug read tools (using '{slug}') ==")
            results.append(await _run("get_addon_info", {"slug": slug}))
            results.append(await _run("get_addon_logs", {"slug": slug}))

        if args.with_backup:
            print("\n== Write: create_backup (real) ==")
            results.append(await _run("create_backup", {"name": "aloha-fixture-test"}))
            results.append(await _run("list_backups", {}))

    passed = sum(1 for r in results if r)
    print(f"\n{passed}/{len(results)} tool calls succeeded.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
