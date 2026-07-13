# Troubleshooting

Common issues and how to fix them. If none of these match, use the in-app
**Report a problem** button (bundles a secrets-free diagnostics snapshot and
opens a prefilled GitHub issue), or open an issue with the bug-report template.

First, two quick checks that resolve most problems:

```bash
# Is Aloha healthy and connected to HA?
curl -s http://your-host:7123/health

# What does Aloha see about itself? (safe, no secrets)
curl -s http://your-host:7123/api/report/diagnostics
```

`/health` returns `ha_connected`, `ha_version`, `setup_complete`, and the
provider.

---

## Aloha won't connect to Home Assistant

**Symptom:** chat says HA is unavailable; `/health` shows `"ha_connected": false`.

- **HAOS add-on:** the Supervisor injects the token automatically — you normally
  don't configure anything. If it's failing, check the add-on has
  `hassio_api: true` and `homeassistant_api: true` (it does by default) and look
  at the add-on log (Settings → Add-ons → Aloha → Log).
- **Docker/standalone:** confirm `ALOHA_HA_URL` points at a reachable HA
  (`curl $ALOHA_HA_URL/api/` from inside the container), and that the token is
  valid. Aloha stores the token encrypted; re-enter it in the wizard if in doubt.
- **Bundled Docker:** HA Core takes ~1–2 minutes to boot on first run. Aloha
  keeps retrying — give it a moment. The log line to look for is
  `HA bootstrap complete.`
- **Token expired / revoked:** create a fresh long-lived access token in HA
  (Profile → Security → Long-lived access tokens) and re-enter it.

---

## The AI provider errors out

**Symptom:** chat returns an auth or quota error from the provider.

- **Bad/'unauthorized' key:** re-enter it in **Settings**. Keys are validated on
  save; a red result means the provider rejected it.
- **Wrong model:** set `model` to `auto`, or a model your account actually has
  access to.
- **Ollama (local):** make sure Ollama is running and reachable at
  `ALOHA_OLLAMA_URL` (default `http://localhost:11434`). From a container,
  `localhost` is the container — point at the host IP.
- **Rate limits / quota:** these come straight from your provider; check your
  provider dashboard.

---

## MCP client can't connect / gets 401

**Symptom:** Claude Code / Cursor / ChatGPT can't reach `/mcp`, or returns 401.

- **401 unauthorized:** once you've minted an MCP key, `/mcp` requires auth.
  Send HTTP Basic `base64(key:secret)`, or exchange the pair for a Bearer token
  at `POST /mcp/token` (`grant_type=client_credentials`). The Settings → MCP page
  generates the exact header for you.
- **Connection refused from the cloud:** a cloud chatbot can't reach a box behind
  home NAT over `localhost`/LAN IP. Set up a **public MCP URL**
  (Settings → Public URL) and use that URL.
- **SSE transport:** Aloha's MCP is SSE — add it with
  `--transport sse` (`claude mcp add --transport sse aloha <url>/mcp`).

---

## Public URL isn't working

**Symptom:** the tunnel URL doesn't resolve or drops.

- **Cloudflare tunnel** gives a fresh random URL each start — grab the current
  one from Settings → Public URL. It's meant for quick/dev use.
- **ngrok** needs a valid authtoken (Settings → Public URL → ngrok). Free ngrok
  URLs also rotate unless you have a reserved domain.
- **Aloha relay** requires an active $1/mo subscription; if the URL 404s, check
  the subscription is active in the relay account panel.
- Whatever the provider, confirm Aloha itself is up first (`/health`), then the
  tunnel process (its status shows in Settings → Public URL).

---

## HAOS add-on doesn't appear in the store

**Symptom:** you added the repository but "Aloha" isn't listed.

- Give it a moment and **reload** the add-on store (⋮ → Check for updates).
- Make sure you added the repo URL exactly: `https://github.com/sackio/aloha`.
- The add-on only ships for `amd64` and `aarch64`. On a 32-bit `armv7` install
  it won't show — use a 64-bit HAOS image.
- If it still doesn't appear, the Supervisor logs the reason. Settings → System →
  Logs → Supervisor, or check `/resolution/info` via the Supervisor API. (For
  maintainers: two add-on config mistakes silently reject an add-on — an invalid
  `map:` type, and putting `{arch}` in the image tag instead of the name. Aloha's
  config avoids both.)

---

## Changes aren't being applied

**Symptom:** you ask for an automation but nothing changes.

This is usually the **safety gate** doing its job: in `normal`/`strict` mode the
agent shows a diff and waits for your approval before writing. Look for the
diff/approve prompt in the chat. If you want the agent to apply routine changes
without prompting, switch to `permissive` mode in Settings (understand the
trade-off first — see the [user guide](USER_GUIDE.md#safety-modes)).

---

## Enabling error reporting (opt-in)

By default Aloha sends **nothing** off-box. If you're helping debug an issue (or
in the beta), you can enable error reporting by setting a Sentry DSN:

```bash
-e ALOHA_ERROR_REPORTING_DSN=https://...ingest.sentry.io/...
```

Events are scrubbed of secrets before send. With no DSN set, no network calls
are ever made. See [docs/BETA.md](BETA.md).

---

## Still stuck?

- **In-app:** click **Report a problem** — it bundles diagnostics and opens a
  prefilled GitHub issue.
- **CLI:** grab `curl -s http://your-host:7123/api/report/diagnostics` and paste
  it into a [new issue](https://github.com/sackio/aloha/issues/new). It's
  secrets-free by construction.
