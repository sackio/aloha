# 🌺 Aloha — alo·HA
> AI Agent for Home Assistant — baked into one Docker image

[![Docker Pulls](https://img.shields.io/docker/pulls/ghcr.io/aloha-ha/aloha?label=Docker%20Pulls&logo=docker)](https://ghcr.io/aloha-ha/aloha)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![HAOS Add-on](https://img.shields.io/badge/HAOS-Add--on-41BDF5?logo=home-assistant)](https://www.home-assistant.io/addons/)

---

## Quick Start

```bash
docker run -d \
  --name aloha \
  -p 7123:7123 \
  -v aloha-data:/data \
  ghcr.io/aloha-ha/aloha:latest
```

Browse to **http://your-host:7123** to set up your AI provider.

---

## What is Aloha?

Aloha is an AI-powered agent that lives inside your Home Assistant setup and lets you control, configure, and automate your smart home using plain English. Ask it to turn off the lights, create an automation, update a dashboard, or dig into your error logs — it figures out how to make it happen. No scripting required.

Under the hood, Aloha ships as a single Docker image that bundles Home Assistant and the Aloha agent together. One `docker run` command and you have a fully working smart home platform with an AI assistant built in. If you already run Home Assistant, Aloha can connect to your existing instance instead, or install as a native HAOS add-on alongside the Supervisor.

---

## Features

- **Multi-provider AI** — choose from Anthropic Claude, OpenAI, Google Gemini, Ollama (local), or any OpenAI-compatible endpoint
- **74 Home Assistant tools** — read and control entities, manage automations, edit config files, update dashboards, interact with HACS, and more
- **Supervised and autonomous modes** — `strict` mode gates every write behind a human approval step; `normal` and `permissive` modes auto-approve safe actions
- **Diff review for config changes** — any change to YAML or config files is shown as a before/after diff before being applied; nothing is written without your sign-off
- **MCP server for power users** — connect Claude Code, Cursor, or VS Code directly to Aloha's tool layer over the Model Context Protocol
- **HAOS add-on option** — install from the add-on store if you already run Home Assistant OS
- **Pi image coming soon** — a ready-to-flash Raspberry Pi image with everything pre-installed

---

## Supported AI Providers

| Provider | Auth | Notes |
|---|---|---|
| Anthropic | API key | Claude Opus 4.5, Sonnet 4.5, Haiku 3.5 |
| OpenAI | API key | GPT-4o, GPT-4o-mini, GPT-4 Turbo |
| Google Gemini | API key | Gemini 2.0 Flash, 1.5 Pro, 1.5 Flash |
| Ollama | None | Runs locally; configure Ollama URL in settings |
| Custom (OpenAI-compatible) | Optional | Any endpoint that speaks the OpenAI API |
| Azure OpenAI | API key | Point `custom_base_url` at your Azure deployment |
| LM Studio | None | OpenAI-compatible local inference |

---

## Installation Options

### 1. Docker (all-in-one)

The simplest option. Starts Home Assistant and Aloha together in a single container.

```bash
docker run -d \
  --name aloha \
  -p 7123:7123 \
  -p 8123:8123 \
  -v aloha-data:/data \
  ghcr.io/aloha-ha/aloha:latest
```

- Aloha UI: **http://your-host:7123**
- Home Assistant: **http://your-host:8123**

If you already have a Home Assistant instance, run in standalone mode and point Aloha at it:

```bash
docker run -d \
  --name aloha \
  -p 7123:7123 \
  -e ALOHA_MODE=standalone \
  -e ALOHA_HA_URL=http://your-ha-host:8123 \
  -v aloha-data:/data \
  ghcr.io/aloha-ha/aloha:latest
```

### 2. HAOS Add-on

Add the Aloha repository to Home Assistant and install from the add-on store:

1. In Home Assistant, go to **Settings > Add-ons > Add-on Store**.
2. Click the three-dot menu (top right) and choose **Repositories**.
3. Add: `https://github.com/aloha-ha/aloha`
4. Find **Aloha** in the list and click **Install**.
5. Start the add-on and open the Web UI on port `7123`.

In add-on mode, Aloha connects to the Supervisor automatically — no token or URL configuration needed.

### 3. Synology NAS

Install using Container Manager (DSM 7.2+):

1. Open **Container Manager > Registry** and search for `ghcr.io/aloha-ha/aloha`.
2. Download the `latest` tag.
3. Go to **Container > Create**, select the image.
4. Under **Port Settings**, map host port `7123` to container port `7123`.
5. Under **Volume**, create a new volume and mount it at `/data`.
6. Apply and start the container.
7. Browse to **http://your-nas-ip:7123**.

---

## Architecture

Aloha uses [s6-overlay v3](https://github.com/just-containers/s6-overlay) to manage both services inside the container. The Aloha agent waits for Home Assistant to be ready before starting.

```
┌─────────────────────────────────────────────────────┐
│                Docker Container                      │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │              s6-overlay v3                   │   │
│  │                                              │   │
│  │   ┌─────────────────┐  ┌──────────────────┐  │   │
│  │   │  Home Assistant  │  │   Aloha Agent    │  │   │
│  │   │   port 8123      │  │   port 7123      │  │   │
│  │   │  (internal only) │  │  FastAPI + React │  │   │
│  │   └────────┬─────────┘  └────────┬─────────┘  │   │
│  │            │  localhost:8123      │            │   │
│  │            └────────────────────►┘            │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │            Volume: /data                     │   │
│  │   /data/homeassistant  — HA config dir       │   │
│  │   /data/aloha          — Aloha config,       │   │
│  │                          encrypted creds,    │   │
│  │                          sessions, diffs     │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
         │                        │
    port 8123                port 7123
  (HA, optional)           (Aloha UI — expose this)
```

Startup order: s6 starts `homeassistant` first; the `aloha` service declares a dependency and additionally polls `http://localhost:8123/api/` before launching uvicorn.

---

## Development

Clone the repo:

```bash
git clone https://github.com/aloha-ha/aloha.git
cd aloha
```

Set up the React frontend:

```bash
cd frontend
npm install
npm run dev        # vite dev server on :5173 (proxies API to :7123)
```

Set up the Python backend:

```bash
cd ..
pip install -r requirements.txt   # or: pip install -e ".[dev]"
```

Run both together:

```bash
# Terminal 1 — backend
ALOHA_MODE=standalone \
ALOHA_HA_URL=http://your-ha:8123 \
uvicorn aloha.main:app --reload --port 7123

# Terminal 2 — frontend
cd frontend && npm run dev
```

The frontend dev server proxies `/api` and `/health` to the backend, so you can work on both without rebuilding the Docker image.

---

## MCP External Clients

Aloha exposes its full tool suite over the Model Context Protocol at:

```
http://your-host:7123/mcp
```

This lets Claude Code, Cursor, VS Code, and other MCP-aware clients use Aloha's 74 Home Assistant tools directly from their editors.

### Connect with Claude Code

```bash
claude mcp add aloha http://your-host:7123/mcp
```

Then in any Claude Code session you can ask it to control your home, read entity states, create automations, and more — all through Aloha's approval-gated tool layer.

### Connect with Cursor or VS Code

Add the following to your MCP client configuration:

```json
{
  "mcpServers": {
    "aloha": {
      "url": "http://your-host:7123/mcp"
    }
  }
}
```

---

## License

MIT — see [LICENSE](LICENSE).
