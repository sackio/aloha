# Aloha closed beta

Aloha is a functional **v0.1.0 pre-release**. The agent, tools, skills, MCP, and
all install paths (Docker, HAOS add-on) work and are covered by an automated test
suite — but it hasn't yet been lived-in on many real homes over time. The closed
beta is how we get there: a small group running Aloha on real setups, with a
tight feedback loop.

## What "beta" means here

- **Expect rough edges.** The core works; polish, breadth of real-world coverage,
  and the managed billing flow are still maturing.
- **Your data stays yours.** Aloha still phones nothing home by default. The only
  telemetry is the **opt-in** error reporting below — off unless you turn it on.
- **The safety gate is on.** In the default mode every change is shown as a diff
  for your approval before it's written. Keep it on during the beta.

## Joining

1. Install Aloha the normal way — see the
   [download page](https://aloha.pushbuild.com/download) or the
   [user guide](USER_GUIDE.md#1-install). The HAOS add-on is the recommended path.
2. Run through the setup wizard (bring your own AI key, or the managed relay).
3. Use it on your real home and tell us what breaks (below).

If you're testing the **managed relay** ($1/mo tunnel or hosted AI), note it runs
in Stripe **test mode** during the beta — no real charges. We'll announce before
go-live.

## Turning on error reporting (opt-in)

Enabling this sends Aloha's unhandled errors to us so we can fix them fast. It's
entirely optional and **off by default**.

- **Docker:** add `-e ALOHA_ERROR_REPORTING_DSN=<dsn we give you>`.
- **HAOS add-on / standalone:** set `error_reporting_dsn` in config.

What we get: the exception + stack trace, Aloha's version/mode/provider *name*,
and a short breadcrumb trail — **all scrubbed of secrets** before it leaves your
box (`aloha/telemetry.py` redacts anything that looks like a key, token, or
Authorization header, and forces `send_default_pii=False`). What we never get:
your AI key, HA token, MCP secrets, entity data, or config contents.

With no DSN set, zero network calls are made — verify anytime with
`curl -s http://your-host:7123/api/report/diagnostics` (that endpoint is local
and secrets-free).

## Reporting a problem

Two easy paths — both produce a **secrets-free** report:

1. **In-app (best):** click **Report a problem**. Aloha bundles a diagnostics
   snapshot (versions, mode, HA reachability, a scrubbed log tail) and opens a
   **prefilled GitHub issue** — just add what you were doing and submit.
2. **By hand:** open a
   [bug report](https://github.com/sackio/aloha/issues/new?labels=beta,needs-triage)
   and paste the output of
   `curl -s http://your-host:7123/api/report/diagnostics`.

Good reports include: what you asked Aloha to do, what you expected, what
happened, and the diagnostics bundle. The log tail and bundle are auto-scrubbed,
but give them a glance before posting.

## What we're especially watching in the beta

- **Agent quality** — does it write good automations and avoid breaking configs
  across varied real HA setups?
- **Install/upgrade** — the HAOS add-on and Docker paths on real hardware
  (including Raspberry Pi / arm64).
- **MCP + public URL** — connecting real cloud chatbots through the tunnels.
- **Anything surprising.** If it felt wrong, tell us — that's the whole point.

Thanks for helping make Aloha solid. 🌺
