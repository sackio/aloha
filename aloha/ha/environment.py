"""
aloha/ha/environment.py

Detect which Home Assistant environment the box is running in, so the agent can
pick the right system-management mechanism:

  - HAOS / Supervised  → the Supervisor API is available (add-ons, OS/Core
    updates, system backups). Detected via the SUPERVISOR_TOKEN env var (injected
    into HA OS add-ons) and/or reachability of http://supervisor.
  - Docker             → a Docker socket is mounted; the agent manages the HA
    container directly (update/restart, container + config backups).
  - Core               → plain HA Core (no Supervisor, no socket) — system
    management is not available; only HA-Core operations.

The Supervisor toolset and the Docker toolset both consult this so their tools
fail with a clear, actionable message when the mechanism isn't present.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

SUPERVISOR_URL = "http://supervisor"
DOCKER_SOCK = os.environ.get("DOCKER_HOST", "").removeprefix("unix://") or "/var/run/docker.sock"


def supervisor_token() -> str | None:
    """The Supervisor bearer token, injected into HAOS/Supervised add-ons."""
    return os.environ.get("SUPERVISOR_TOKEN") or None


def has_supervisor() -> bool:
    return bool(supervisor_token())


def has_docker_socket() -> bool:
    try:
        return Path(DOCKER_SOCK).exists()
    except Exception:
        return False


@lru_cache(maxsize=1)
def detect_environment() -> dict:
    """Return a summary of the runtime environment + available capabilities."""
    supervisor = has_supervisor()
    docker = has_docker_socket()
    if supervisor:
        kind = "haos"  # HAOS or Supervised — both expose the Supervisor
    elif docker:
        kind = "docker"
    else:
        kind = "core"
    return {
        "kind": kind,
        "supervisor": supervisor,
        "docker_socket": docker if not supervisor else False,  # prefer Supervisor when both
        "supervisor_url": SUPERVISOR_URL,
        "docker_sock": DOCKER_SOCK,
        "can_manage_system": supervisor or docker,
    }
