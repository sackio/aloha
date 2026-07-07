# Aloha tests

## Test suite

```bash
pip install -e ".[dev]"      # pytest + pytest-asyncio
pytest                       # unit + integration (fast, no HA, no network)
./test/smoke.sh              # end-to-end against a real box process + stub HA
```

- **`unit/`** — pure logic: config encryption round-trips, MCP auth (key+secret,
  token endpoint, lifecycle), skill loader, tool registry (no duplicate names),
  environment detection, public-URL manager, relay-tunnel client.
- **`integration/`** — the FastAPI app in-process (Starlette TestClient, no live
  HA): health, skills CRUD, MCP-key lifecycle + `/mcp` auth enforcement, the
  OAuth2 token endpoint, public-URL + relay status, MCP server construction.
- **`smoke.sh`** — boots the **real** box process against a stub HA and drives
  the whole surface with curl, including the SSE `/mcp` endpoint with key+secret
  auth (which the in-process suite can't reach). Also serves as a demo routine.

## Fixtures

Reproducible throwaway environments for testing Aloha against the two install
types it supports. Aloha is **environment-aware**: it detects whether it's on
HAOS (Supervisor available), plain Docker (Docker socket), or bare Core, and
exposes the right system-management tools for each. These fixtures let us
exercise both paths on real Home Assistant, not mocks.

| Fixture | Environment | What it proves |
|---|---|---|
| [`fixtures/docker/`](fixtures/docker/) | **HA Container** (plain Docker, no Supervisor) | `kind="docker"` detection, the `docker_*` tools, and the standalone agent talking to a real HA. |
| [`fixtures/haos/`](fixtures/haos/) | **HAOS** (appliance OS + Supervisor) | `kind="haos"` detection, the 22 `supervisor.py` tools (Core/OS/Supervisor updates, add-on management, backups), and the `haos-addon/` local add-on. |

Shared helper: [`fixtures/onboard_ha.py`](fixtures/onboard_ha.py) drives a fresh
HA through onboarding and mints a long-lived access token (LLAT) over the
REST + WebSocket API — used by both fixtures (HA Core and HAOS onboard the same
way).

## Quick start — Docker (fast, no VM)

```bash
./fixtures/docker/setup.sh        # scratch HA Core on :8124, onboarded, token minted
./fixtures/docker/run-aloha.sh    # run Aloha (standalone) against it
./fixtures/docker/teardown.sh     # remove it
```

## Quick start — HAOS (real Supervisor, needs KVM)

```bash
./fixtures/haos/boot-vm.sh        # boot a throwaway HAOS VM, HA on :8125
# → onboard, install the add-on, then:
docker exec addon_local_aloha python3 validate_supervisor.py
./fixtures/haos/teardown.sh
```

See [`fixtures/haos/README.md`](fixtures/haos/README.md) for the full HAOS
walkthrough (onboarding, installing Aloha as a local add-on, validating the
Supervisor toolset).

## Why two fixtures

The Docker and HAOS paths are genuinely different: plain Docker has **no
Supervisor**, so there's no add-on store, no `create_backup`, no `update_core`
— Aloha falls back to the `docker_*` tools (pull image, recreate container).
HAOS has the Supervisor, so Aloha administers the whole box. The skills
(`upgrade-home-assistant`, `manage-addons`, `system-backup`, `update-os`) all
call `get_environment` first and branch accordingly. These fixtures are how we
keep both branches honest.
