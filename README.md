<div align="center">

# 🌺 Aloha

### An AI agent for Home Assistant — like Claude Code, for your smart home.

Chat with your home in plain English. Aloha reads your entities, writes
automations, edits config, debugs what's broken, and operates Home Assistant for
you — with a curated library of HA **skills** and full **MCP** tool access.

**Open source. Bring your own AI key — or use the managed [aloha.pushbuild.com](https://aloha.pushbuild.com).**

</div>

---

## What is Aloha?

Home Assistant is the most powerful smart-home platform there is — and almost
impossible for a non-technical person to configure. AI coding agents are fluent
in HA's YAML, its automations, its quirks. **Aloha glues them together:** a
baked-in agent that administers Home Assistant through a friendly chat UI.

- 🛠️ **100+ tools** — read/control entities, CRUD automations, edit config
  files, manage dashboards & HACS, read logs and traces. On Home Assistant OS it
  also manages the *system* (update Core/OS/Supervisor, add-ons, backups); on
  Docker it manages the container.
- 📚 **HA skills** — curated playbooks the agent follows for real tasks: set up
  motion lighting, debug why an automation didn't fire, triage unavailable
  entities, run a health check, make safe config changes. Browse and add your own
  right in the UI.
- 🔌 **MCP, both ways** — Aloha exposes its tools as an MCP server *and* can
  consume external MCP servers. Point Claude, Cursor, ChatGPT — any MCP chatbot —
  at it and it can run your home.
- 🌐 **Public MCP URL** — behind home NAT? Aloha can give your MCP endpoint a
  public URL out of the box: a free Cloudflare tunnel, your own ngrok, or the
  stable Aloha relay ($1/mo).
- 🔑 **Secure by key** — protect the MCP endpoint with an OAuth key + secret
  (mint / regenerate / terminate in the UI).
- 🤖 **Any AI** — Anthropic Claude, OpenAI, Gemini, Ollama (local/offline),
  Groq, OpenRouter, or any OpenAI-compatible endpoint. Bring your own key.
- 🛡️ **Safe by default** — every config change is shown as a diff for your
  approval before it's written. Nothing touches your setup without sign-off.

---

## Two ways to run it

### 1. Self-host (open source, free)

Bring your own AI provider key (or run a local model with Ollama — fully offline,
no account). You own everything; nothing phones home.

```bash
git clone https://github.com/sackio/aloha.git
cd aloha
docker compose up -d --build
```

- **Aloha UI:** http://your-host:7123  ·  **Home Assistant:** http://your-host:8123

Already running Home Assistant? Point Aloha at it instead of bundling one:

```bash
docker run -d --name aloha -p 7123:7123 \
  -e ALOHA_MODE=standalone -e ALOHA_HA_URL=http://your-ha:8123 \
  -v aloha-data:/data ghcr.io/sackio/aloha:latest   # prebuilt images coming soon
```

Also ships as a **Home Assistant OS add-on** (`haos-addon/`) — Supervisor injects
the HA token automatically.

### 2. Aloha managed (no setup, no API key)

Don't want to deal with API keys and billing? Use the hosted agent at
**[aloha.pushbuild.com](https://aloha.pushbuild.com)** — pick "Aloha managed" in
the setup wizard, sign in, and you're chatting with your home. Flat monthly with
generous usage. *(In active development.)*

---

## First run

Open the Aloha UI and the wizard walks you through picking an AI provider and
connecting to Home Assistant. Then just ask:

> *"What lights are on right now?"*
> *"Create a bedtime routine that locks the doors and turns off the lights at 11pm."*
> *"Why didn't my away-mode automation fire yesterday?"*
> *"Set up motion-activated lighting in the hallway."*

---

## Power users: connect your IDE over MCP

Aloha exposes its full tool suite over the Model Context Protocol:

```bash
claude mcp add --transport sse aloha http://your-host:7123/mcp
```

Use Claude Code, Cursor, or any MCP client to manage your home from your editor.
The setup UI generates the exact command/JSON for you — including your public URL
and access-key header once you've set those up.

Protect the endpoint with an OAuth key + secret (mint one in the UI), sent as
HTTP Basic or exchanged at the OAuth2 token endpoint (`POST /mcp/token`,
`grant_type=client_credentials`).

---

## How it works

```
┌──────────────────────── one container ────────────────────────┐
│  Home Assistant (:8123)  ◄──localhost──  Aloha agent (:7123)   │
│                                          FastAPI + React UI    │
│                                         agent loop → 100+ tools│
│                                          skills · MCP client   │
│   shared volume: /data  (HA config + Aloha settings/sessions)  │
└────────────────────────────────────────────────────────────────┘
```

Provider-agnostic agent loop, multi-step tool use, and a diff→approve safety gate.

---

## Status

Aloha is under active development. The agent, tools, skills, MCP support, and the
Docker/standalone/add-on paths work today; prebuilt multi-arch images, the
Raspberry Pi image, and the managed tier are in progress.

## Contributing

Issues and PRs welcome. Skills are just markdown files in `aloha/skills/library/` —
adding one is a great first contribution.

## Contact

Questions, feedback, or interested in the managed tier? Reach us through the
contact form at **[aloha.pushbuild.com](https://aloha.pushbuild.com)**, or open a
GitHub issue.

## License

MIT — see [LICENSE](LICENSE).
