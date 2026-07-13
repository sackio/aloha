# Architecture

A map of how Aloha is put together, for contributors. For *using* Aloha see the
[user guide](USER_GUIDE.md).

## The big picture

Aloha is one Python service (FastAPI + a React SPA) that sits next to Home
Assistant and drives it through an AI agent loop.

```
┌──────────────────────── one deployment ───────────────────────┐
│  Home Assistant (:8123)  ◄── HTTP/WS ──  Aloha (:7123)         │
│                                          FastAPI + React SPA    │
│                                          agent loop → 104 tools │
│                                          context engine · skills│
│                                          MCP server + client    │
│   data_dir: config.json (encrypted creds) + sessions           │
└────────────────────────────────────────────────────────────────┘
        ▲ optional public MCP URL (relay / cloudflared / ngrok)
        ▼
   cloud chatbots (Claude, Cursor, ChatGPT) over MCP
```

## Runtime modes

Set by `ALOHA_MODE`:

- **bundled** — Aloha + a Home Assistant Core in one container (the Docker
  image). Aloha manages the container via the `docker_*` tools.
- **standalone** — Aloha points at an existing HA (`ALOHA_HA_URL`).
- **addon** — the HAOS add-on. The Supervisor injects the HA token and exposes
  the Supervisor API, so the `supervisor_*` tools (update Core/OS, manage
  add-ons, backups) light up.

## Startup sequence (`aloha/__main__.py`)

1. `AlohaConfig.load()` — defaults ← `config.json` ← `ALOHA_*` env (env wins).
2. Configure logging; `telemetry.init_error_reporting()` (no-op without a DSN).
3. `bootstrap(config)` — wait for HA, acquire/validate a token, return an
   `HAClient`. Degrades gracefully if HA isn't up yet.
4. `init_context_engine(...)` + `start()` — background refresh of HA state.
5. `init_mcp_manager(...)` — connect any external MCP servers (best-effort).
6. `create_app(config)` — assemble FastAPI.
7. Serve with uvicorn.

## Key modules (`aloha/`)

| Area | Where | Role |
|---|---|---|
| Config | `config.py` | Single source of truth. Credentials stored **encrypted** (`auth/crypto.py`, Fernet) — never plaintext. |
| App factory | `app.py` | Builds FastAPI, wires routers, the MCP auth middleware, the MCP SSE mount, and static SPA serving. |
| HA client | `ha/` | Async REST + WebSocket client for Home Assistant. |
| Context engine | `context/` | Periodically snapshots entities/automations/config so the agent has current state without re-fetching every turn. |
| Agent loop | `agent/` | Provider-agnostic multi-step tool-use loop with the diff→approve safety gate. |
| Backends | `backends/` | Provider adapters (Anthropic, OpenAI, Gemini, Ollama, Groq, OpenRouter, custom, Aloha managed). |
| Tools | `mcp/tools/`, `mcp/registry.py` | The 104 tools, grouped by domain, each with a safety level. `ALL_TOOLS` is the registry. |
| MCP server | `mcp/server.py`, `mcp/auth.py` | Exposes tools over MCP (SSE) with OAuth key+secret / Bearer auth. |
| MCP client | `mcp/client.py` | Consumes external MCP servers and surfaces their tools to the agent. |
| Skills | `skills/`, `skills/library/*.md` | Markdown playbooks the agent follows for real tasks. |
| Public URL | `public_url.py`, `relay_tunnel.py` | Gives `/mcp` a public URL via relay / cloudflared / ngrok. |
| Telemetry | `telemetry.py` | Opt-in error reporting + secrets-free diagnostics. |
| Routes | `routes/` | `/health`, `/api/settings`, `/api/chat` (SSE), `/api/skills`, `/api/public-url`, `/api/relay`, `/api/mcp-keys`, `/api/report/*`. |
| UI | `ui/` → built into `aloha/static/` | React + Vite SPA (wizard, chat, skills, settings). |

## The agent loop & safety gate

The agent receives your message plus a compact view of HA state (from the
context engine) and the tool schemas. It plans, calls tools, and iterates.
**Reads** run freely. **Writes** (creating an automation, editing config, a
Supervisor action) are gated: in `strict`/`normal` safety mode the proposed
change is returned to the UI as a **diff** and applied only after you approve.
`permissive` skips the prompt for routine writes. Safety level per tool lives in
the tool definition; the registry is the enforcement surface.

## Auth & secrets

- **Credentials** (`api_key`, `ha_token`, MCP secrets, ngrok/relay tokens) are
  Fernet-encrypted in `config.json`; the key file is `{data_dir}/.keyfile`
  (0600). Plaintext is never written and never returned by an API route.
- **MCP endpoint** — once any MCP key exists, a middleware in `app.py` requires
  HTTP Basic `base64(key:secret)`, a Bearer token from `POST /mcp/token`, or
  `X-Api-Key`/`X-Api-Secret`. No keys → open (local-only) for first-run
  convenience.
- **Diagnostics/telemetry** — everything leaving the box passes through
  `telemetry.scrub()`.

## The managed relay (separate service)

The `aloha-server` repo is the hosted relay: an OpenAI-compatible proxy in front
of OpenRouter for the "Aloha managed" tier, plus the MCP reverse-tunnel that
backs the $1/mo public URL, plus the landing/skills/download site. The box talks
to it as just another OpenAI-compatible provider (`managed_relay_url`).

## Distribution

- CI (`.github/workflows/`) runs tests on every PR and, on a `v*` tag, publishes
  the multi-arch Docker image and the per-arch HAOS add-on images to
  `ghcr.io/sackio`.
- `packaging/` holds reproducible recipes + confirm scripts (including
  `packaging/vm/confirm.sh`, which installs the add-on on a throwaway HAOS VM
  end-to-end). See the packaging README.

## Tests

`test/` — unit (`test/unit/`) and route-level integration (`test/integration/`)
run fully in-process against a temp data dir and a stubbed HA (no network).
`test/smoke.sh` is an 18-check end-to-end pass. See [CONTRIBUTING.md](../CONTRIBUTING.md).
