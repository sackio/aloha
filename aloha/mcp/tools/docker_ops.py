"""
aloha/mcp/tools/docker_ops.py

Docker tools — the system-management path for plain-Docker installs (no
Supervisor). They talk to the Docker Engine API over the mounted socket
(/var/run/docker.sock) so the agent can inspect/restart/update the Home
Assistant container and pull images.

Requires the socket to be mounted into the Aloha container:
    -v /var/run/docker.sock:/var/run/docker.sock

Every tool returns a clear "not available" message when there's no socket, so
the agent can explain the limitation (or use the Supervisor tools on HAOS).

Exports: TOOLS, TOOL_NAMES, execute_docker_tool(name, args)
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from aloha.agent.types import SafetyLevel, ToolDef
from aloha.ha.environment import DOCKER_SOCK, has_docker_socket

TOOLS: list[ToolDef] = [
    ToolDef(name="docker_list_containers", description="List Docker containers (name, image, state). Docker installs only.",
            parameters={"type": "object", "properties": {"all": {"type": "boolean", "description": "Include stopped (default true)."}}},
            safety=SafetyLevel.READ),
    ToolDef(name="docker_container_info", description="Inspect a container by name or id (image, status, created).",
            parameters={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, safety=SafetyLevel.READ),
    ToolDef(name="docker_container_logs", description="Get recent logs for a container by name or id.",
            parameters={"type": "object", "properties": {"name": {"type": "string"}, "tail": {"type": "integer", "description": "Lines (default 100)."}}, "required": ["name"]},
            safety=SafetyLevel.READ),
    ToolDef(name="docker_restart_container", description="Restart a container by name or id.",
            parameters={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, safety=SafetyLevel.WRITE_SOFT),
    ToolDef(name="docker_pull_image", description="Pull a Docker image (e.g. 'ghcr.io/home-assistant/home-assistant:stable').",
            parameters={"type": "object", "properties": {"image": {"type": "string"}}, "required": ["image"]}, safety=SafetyLevel.WRITE_CONFIG),
    ToolDef(name="update_ha_docker", description="Upgrade the Home Assistant container on a Docker install: pull its latest image, then guide the recreate. Docker installs only.",
            parameters={"type": "object", "properties": {"container": {"type": "string", "description": "HA container name (default: autodetect 'homeassistant')."}}},
            safety=SafetyLevel.DESTRUCTIVE),
]

TOOL_NAMES: set[str] = {t.name for t in TOOLS}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(uds=DOCKER_SOCK),
                             base_url="http://docker", timeout=120)


async def _find_ha_container(client: httpx.AsyncClient, hint: str | None = None) -> dict | None:
    r = await client.get("/containers/json?all=1")
    r.raise_for_status()
    containers = r.json()
    for c in containers:
        names = [n.lstrip("/") for n in c.get("Names", [])]
        if hint and hint.lstrip("/") in names:
            return c
    if hint:
        return None
    # autodetect: name or image mentions home-assistant/homeassistant
    for c in containers:
        names = " ".join(c.get("Names", [])).lower()
        if "homeassistant" in names.replace("-", "") or "home-assistant" in (c.get("Image", "").lower()):
            return c
    return None


async def execute_docker_tool(name: str, args: dict[str, Any]) -> str:
    if not has_docker_socket():
        return (f"This is a Docker tool but no Docker socket is available at {DOCKER_SOCK}. "
                "Mount it (-v /var/run/docker.sock:/var/run/docker.sock) to let Aloha manage "
                "containers, or use the Supervisor tools on a HAOS/Supervised install.")

    try:
        async with _client() as client:
            if name == "docker_list_containers":
                all_ = args.get("all", True)
                r = await client.get(f"/containers/json?all={'1' if all_ else '0'}")
                r.raise_for_status()
                rows = [{"name": [n.lstrip("/") for n in c.get("Names", [])][0] if c.get("Names") else "?",
                         "image": c.get("Image"), "state": c.get("State"), "status": c.get("Status")}
                        for c in r.json()]
                return json.dumps(rows, indent=2)[:4000] or "No containers."

            if name == "docker_container_info":
                r = await client.get(f"/containers/{args['name']}/json")
                if r.status_code == 404:
                    return f"No container named '{args['name']}'."
                r.raise_for_status()
                d = r.json()
                return json.dumps({"name": d.get("Name", "").lstrip("/"), "image": d.get("Config", {}).get("Image"),
                                   "state": d.get("State", {}).get("Status"), "started": d.get("State", {}).get("StartedAt"),
                                   "created": d.get("Created")}, indent=2)

            if name == "docker_container_logs":
                tail = int(args.get("tail") or 100)
                r = await client.get(f"/containers/{args['name']}/logs?stdout=1&stderr=1&tail={tail}")
                if r.status_code == 404:
                    return f"No container named '{args['name']}'."
                r.raise_for_status()
                # Docker multiplexes logs with an 8-byte header per frame; strip them best-effort.
                raw = r.content
                out, i = [], 0
                while i + 8 <= len(raw):
                    ln = int.from_bytes(raw[i + 4:i + 8], "big")
                    out.append(raw[i + 8:i + 8 + ln].decode("utf-8", "ignore"))
                    i += 8 + ln
                text = "".join(out) if out else raw.decode("utf-8", "ignore")
                return text[-4000:]

            if name == "docker_restart_container":
                r = await client.post(f"/containers/{args['name']}/restart")
                if r.status_code == 404:
                    return f"No container named '{args['name']}'."
                r.raise_for_status()
                return f"Restarted container '{args['name']}'."

            if name == "docker_pull_image":
                image = args["image"]
                repo, _, tag = image.partition(":")
                tag = tag or "latest"
                r = await client.post(f"/images/create?fromImage={repo}&tag={tag}")
                r.raise_for_status()
                return f"Pulled {repo}:{tag}."

            if name == "update_ha_docker":
                c = await _find_ha_container(client, args.get("container"))
                if not c:
                    return ("Couldn't find the Home Assistant container. Pass its name explicitly, "
                            "or check `docker_list_containers`.")
                cname = [n.lstrip("/") for n in c.get("Names", [])][0]
                image = c.get("Image", "")
                repo, _, tag = image.partition(":")
                tag = tag or "stable"
                pr = await client.post(f"/images/create?fromImage={repo}&tag={tag}")
                pr.raise_for_status()
                return (f"Pulled the latest {repo}:{tag} for container '{cname}'. To finish the upgrade the "
                        f"container must be RECREATED on the new image (a plain restart keeps the old one). "
                        f"If it's managed by docker compose, run `docker compose up -d` on the host; otherwise "
                        f"recreate '{cname}' with the same volumes/env. I can restart it now with "
                        f"docker_restart_container, but that alone won't apply the new image.")
    except httpx.HTTPError as exc:
        return f"Docker error: {exc}"

    raise ValueError(f"Unknown docker tool: {name!r}")
