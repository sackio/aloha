# Aloha user guide

Aloha is an AI agent for Home Assistant — chat with your home in plain English
and it reads your entities, writes automations, edits config, debugs what's
broken, and operates HA for you. This guide walks the whole flow: install →
first run → everyday use → skills → public MCP URL → connecting an IDE.

> New here? The five-minute version: install (below), open the UI, finish the
> wizard, and start asking questions.

---

## 1. Install

Pick the path that fits your setup — full recipes on the
[download page](https://aloha.pushbuild.com/download).

### Appliance (recommended): Home Assistant OS + the Aloha add-on
For a VM (Proxmox / VirtualBox / VMware) or a Raspberry Pi / arm64 SBC. This
gives Aloha full run of the box — it can update Core/OS/Supervisor, manage
add-ons, and take backups.

1. Install **Home Assistant OS** from
   [home-assistant.io/installation](https://www.home-assistant.io/installation/)
   and finish onboarding.
2. Settings → Add-ons → Add-on store → ⋮ → **Repositories**, add
   `https://github.com/sackio/aloha`.
3. Install **Aloha** from the store, **Start** it, open it from the sidebar.

### Docker (bring your own host)
Bundles Home Assistant + the agent in one container:

```bash
docker run -d --name aloha \
  -p 8123:8123 -p 7123:7123 \
  -v aloha-data:/data \
  ghcr.io/sackio/aloha:latest
```

Home Assistant → `:8123`, Aloha → `:7123`. Already run HA? Point Aloha at it
and drop the `8123` mapping:

```bash
docker run -d --name aloha -p 7123:7123 \
  -e ALOHA_MODE=standalone -e ALOHA_HA_URL=http://your-ha:8123 \
  -v aloha-data:/data ghcr.io/sackio/aloha:latest
```

---

## 2. First run — the setup wizard

Open the Aloha UI (`:7123`, or the sidebar panel on HAOS). The wizard covers two
things:

1. **Choose your AI.** Either:
   - **Bring your own key** — pick a provider (Anthropic, OpenAI, Gemini, Ollama
     for local/offline, Groq, OpenRouter, or any OpenAI-compatible endpoint) and
     paste your key. Keys are encrypted at rest and never leave the box except to
     the provider you chose.
   - **Aloha managed** — sign in to the hosted relay; no key, flat monthly.
2. **Connect Home Assistant.** On the HAOS add-on this is automatic (the
   Supervisor injects a token). On Docker/standalone, Aloha guides you through a
   long-lived access token if it can't connect on its own.

When both are green, the wizard finishes and you're in the chat.

---

## 3. Everyday use — just ask

Aloha understands your actual entities and config. Try:

> *"What lights are on right now?"*
> *"Create a bedtime routine that locks the doors and turns off the lights at 11pm."*
> *"Why didn't my away-mode automation fire yesterday?"*
> *"Set up motion-activated lighting in the hallway."*
> *"Which of my entities are unavailable, and why?"*

**The safety gate.** In the default safety mode, any change that writes to your
setup (a new automation, a config edit, an add-on action) is shown to you as a
**diff first**. Nothing is written until you approve it. You can loosen this
(`permissive`) or tighten it (`strict`) in settings — see
[safety modes](#safety-modes).

---

## 4. Skills

Skills are curated playbooks the agent follows for real tasks — motion lighting,
debugging why an automation didn't fire, triaging unavailable entities, running
a health check, making safe config changes. Aloha picks the right skill for what
you ask; you don't invoke them manually.

Browse the library and add your own right in the UI (**Skills** tab). A skill is
just a markdown file — see
[CONTRIBUTING.md](../CONTRIBUTING.md#quickest-possible-contribution-a-skill) to
write one.

---

## 5. Public MCP URL (optional)

Want a cloud chatbot (Claude, ChatGPT, Cursor) to reach your home from outside
your network? Aloha can give its `/mcp` endpoint a public URL out of the box.
In **Settings → Public URL**, pick one:

- **Cloudflare tunnel** — free, no account, a random `*.trycloudflare.com` URL.
- **ngrok** — bring your own ngrok authtoken for a stable URL.
- **Aloha relay** — a stable `aloha.pushbuild.com/...` URL, $1/mo.

Whichever you pick, **protect the endpoint first** (next section) — a public MCP
URL without a key is an open door to your home.

---

## 6. Connect an IDE / chatbot over MCP

Aloha exposes its full tool suite over the Model Context Protocol (SSE):

```bash
claude mcp add --transport sse aloha http://your-host:7123/mcp
```

The setup UI generates the exact command/JSON for you, including your public URL
and auth header.

**Secure it.** In **Settings → MCP keys**, mint an OAuth **key + secret**. Once
any key exists, `/mcp` requires auth. Clients send it either as:

- HTTP Basic: `base64(key:secret)` in the `Authorization` header, or
- a Bearer token exchanged at `POST /mcp/token`
  (`grant_type=client_credentials`).

You can mint, regenerate, or terminate keys at any time.

The full list of tools an MCP client gets is in
[docs/MCP_TOOLS.md](MCP_TOOLS.md).

---

## Safety modes

| Mode | Behaviour |
|---|---|
| `strict` | Every write requires approval; the agent is most conservative. |
| `normal` (default) | Writes are shown as a diff for approval before applying. |
| `permissive` | The agent applies routine changes without prompting; use only if you trust it on your setup. |

Set it in **Settings**, or at deploy time with `ALOHA_SAFETY_MODE`.

---

## Configuration reference

Aloha reads config from `{data_dir}/config.json`, overlaid by `ALOHA_*` env
vars (env wins). Common ones:

| Env var | Meaning |
|---|---|
| `ALOHA_AI_PROVIDER` | `anthropic` / `openai` / `gemini` / `ollama` / `groq` / `openrouter` / `custom` / `aloha` |
| `ALOHA_MODEL` | Model id, or `auto` |
| `ALOHA_SAFETY_MODE` | `strict` / `normal` / `permissive` |
| `ALOHA_MODE` | `bundled` / `standalone` / `addon` |
| `ALOHA_HA_URL` | Home Assistant base URL (standalone) |
| `ALOHA_DATA_DIR` | Where config + sessions live |
| `ALOHA_PORT` | Aloha UI/API port (default 7123) |
| `ALOHA_ERROR_REPORTING_DSN` | Opt-in error reporting; empty = off |

Credentials (`api_key`, `ha_token`, MCP secrets) are set through the UI or
`ALOHA_API_KEY` / `ALOHA_HA_TOKEN`, and are always stored encrypted.

---

Stuck? See [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md), or use the in-app
**Report a problem** button.
