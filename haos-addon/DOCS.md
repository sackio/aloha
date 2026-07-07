# Aloha — AI Agent for Home Assistant

Aloha is an AI-powered chat agent that lives inside your Home Assistant. Talk to Claude, GPT-4, Gemini, or a local Ollama model to control devices, create automations, edit config files, manage dashboards, and more — all through a conversational interface.

---

## Installation

1. Open Home Assistant and go to **Settings → Add-ons → Add-on Store**.
2. Click the menu (three dots, top right) and select **Repositories**.
3. Add the Aloha repository URL:
   ```
   https://github.com/sackio/aloha
   ```
4. Find **Aloha** in the add-on store and click **Install**.
5. After installation, go to the **Configuration** tab and set your preferred AI provider and options.
6. Click **Start**, then open the **Aloha** panel from the Home Assistant sidebar.

---

## First-Run Setup

When you open the Aloha panel for the first time, a setup wizard guides you through:

1. **Choose your AI provider** — Anthropic, OpenAI, Gemini, Ollama (local), or a custom OpenAI-compatible endpoint.
2. **Select a model** — a recommended default is pre-selected; you can change it.
3. **Enter your API key** — paste your provider API key (stored encrypted; never logged).
4. **Verify the connection** — Aloha tests the key and shows you the connected model.
5. **Done** — you can start chatting immediately.

The setup wizard can be re-run at any time from **Settings → Re-run Setup**.

---

## Supported AI Providers

| Provider | Models | Requires API Key | Notes |
|---|---|---|---|
| **Anthropic** | claude-opus-4-5, claude-sonnet-4-5, claude-haiku-3-5 | Yes | [console.anthropic.com](https://console.anthropic.com) |
| **OpenAI** | gpt-4o, gpt-4o-mini, gpt-4-turbo | Yes | [platform.openai.com](https://platform.openai.com) |
| **Google Gemini** | gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash | Yes | [aistudio.google.com](https://aistudio.google.com) |
| **Ollama** | any locally-pulled model | No | Requires Ollama running on your network |
| **OpenRouter** | any OpenRouter model | Yes | [openrouter.ai](https://openrouter.ai) |
| **Groq** | llama3, mixtral, gemma, etc. | Yes | [console.groq.com](https://console.groq.com) |
| **Custom** | any OpenAI-compatible API | Optional | Set a base URL in settings |

---

## Safety Modes

Aloha categorizes every action by its potential impact and requires approval accordingly.

| Mode | Behavior |
|---|---|
| **Supervised** (default) | Read-only actions run automatically. All writes (device control, automations, config files) show a confirmation card before executing. |
| **Autonomous** | Read-only and soft-write actions (device control) run automatically. Config-file writes and destructive actions (delete automation, restart HA) still require approval. |

You can change the safety mode at any time from the Aloha settings panel. Regardless of mode, any action that modifies a YAML/JSON config file always shows a diff review card so you can see exactly what will change before approving.

---

## MCP External Client Setup

Aloha exposes a Model Context Protocol (MCP) server so you can connect external AI tools (such as Claude Desktop or VS Code extensions) directly to your Home Assistant.

### Connection details

- **MCP endpoint**: `http://<ha-ip>:7123/mcp`
- **Authentication**: same long-lived token used for HA (set in Aloha settings)

### Claude Desktop example (`~/.config/Claude/claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "aloha": {
      "url": "http://192.168.1.100:7123/mcp",
      "headers": {
        "Authorization": "Bearer <your-ha-token>"
      }
    }
  }
}
```

Replace `192.168.1.100` with your Home Assistant IP and `<your-ha-token>` with a long-lived access token created in HA under **Profile → Long-Lived Access Tokens**.

---

## Troubleshooting

### 1. "HA connection lost" error in chat

Aloha lost contact with Home Assistant's API. Check:
- The add-on is running (Settings → Add-ons → Aloha → Info tab shows "Started").
- Your HA instance is healthy (open the HA UI in another tab).
- If you are using a custom HA URL in settings, verify it is reachable from inside the add-on container.

### 2. API key is rejected / "Invalid API key"

- Double-check the key was copied completely (no trailing spaces).
- Verify the key is active in your provider's console and has not been revoked.
- For Anthropic keys, ensure you are using a key from [console.anthropic.com](https://console.anthropic.com), not the older API dashboard.

### 3. Ollama models are not listed

- Aloha queries Ollama at the URL configured in settings (default: `http://localhost:11434`).
- If Ollama runs on a different machine, update the Ollama URL in Aloha settings to `http://<ollama-host>:11434`.
- Ensure Ollama is running and at least one model has been pulled (`ollama pull llama3`).

### 4. Diff review card appears but "Apply" does nothing

- Your browser session may have disconnected. Reload the Aloha panel and check the chat history — the diff card will still be there if it has not been resolved.
- Check the add-on logs (Settings → Add-ons → Aloha → Log tab) for filesystem permission errors on `/data/aloha`.

### 5. The Aloha panel does not appear in the sidebar

- Confirm the add-on is started (not just installed).
- Hard-refresh your browser (`Ctrl+Shift+R` / `Cmd+Shift+R`).
- If the panel still does not appear, go to **Settings → Dashboards** and check whether the Aloha panel entry is present. If not, restart the add-on — the panel registration happens at startup.
