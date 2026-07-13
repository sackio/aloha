# Changelog

All notable changes to Aloha are documented here. The format is loosely based on
[Keep a Changelog](https://keepachangelog.com/), and Aloha aims to follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Opt-in error reporting (Sentry) — OFF by default; enabled only by setting
  `error_reporting_dsn`. Events are scrubbed of secrets before send.
- **Report a problem** flow (`/api/report/*`) that bundles a secrets-free
  diagnostics snapshot and opens a prefilled GitHub issue.
- Documentation: `CONTRIBUTING.md`, this changelog, `docs/USER_GUIDE.md`,
  `docs/TROUBLESHOOTING.md`, `docs/BETA.md`, and an auto-generated
  `docs/MCP_TOOLS.md` tool reference (`scripts/gen_tool_docs.py`).
- GitHub issue + pull-request templates.

## [0.1.0] — 2026-07-07

First public pre-release.

### Added
- Provider-agnostic agent loop with multi-step tool use and a diff→approve
  safety gate. Providers: Anthropic, OpenAI, Gemini, Ollama, Groq, OpenRouter,
  any OpenAI-compatible endpoint, and the Aloha managed relay.
- **104 tools**: entities/devices, automations/scripts/scenes, config files,
  dashboards, HACS, system diagnostics, skills, Supervisor (HAOS), and Docker.
  See [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md).
- Curated **skill** library with in-UI browse + upload.
- **MCP both ways**: Aloha serves its tools over MCP (SSE) *and* consumes
  external MCP servers.
- **MCP auth**: OAuth key + secret (mint/regenerate/terminate), accepted as HTTP
  Basic or exchanged for a Bearer token at `POST /mcp/token`.
- **Public MCP URL** out of the box: free Cloudflare tunnel, bring-your-own
  ngrok, or the Aloha relay ($1/mo).
- Encrypted-at-rest credentials (Fernet) — `api_key` / `ha_token` / MCP secrets
  are never written in plaintext.
- Distribution:
  - Docker image `ghcr.io/sackio/aloha` (amd64 + arm64), bundling HA Core + the
    agent.
  - **Home Assistant OS add-on** `ghcr.io/sackio/{amd64,aarch64}-aloha-addon`,
    installable via the `github.com/sackio/aloha` add-on repository. Verified
    end-to-end on real HAOS.
  - Reproducible packaging recipes + confirm scripts under `packaging/`.
- React setup wizard, SSE chat, session management.
- Test suite: unit + integration (Starlette TestClient) and an 18-check smoke
  test; CI runs tests + builds on every PR.

[Unreleased]: https://github.com/sackio/aloha/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sackio/aloha/releases/tag/v0.1.0
