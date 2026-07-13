# Contributing to Aloha

Thanks for helping build Aloha — an AI agent for Home Assistant. Issues and PRs
are welcome. This guide covers dev setup, the test suite, and how changes flow.

## Quickest possible contribution: a skill

Skills are plain markdown playbooks the agent follows for real tasks. They live
in `aloha/skills/library/` — one `.md` file per skill. Adding a good one is the
best first contribution and needs no Python:

1. Copy an existing skill (e.g. `aloha/skills/library/motion-lighting.md`).
2. Give it a clear title, a short "when to use this," and step-by-step guidance
   the agent can follow (which tools to call, what to check, what to confirm).
3. Run `python3 -m pytest test/unit/test_skills.py` to confirm it loads.
4. Open a PR describing the task it automates.

## Dev setup

```bash
git clone https://github.com/sackio/aloha.git
cd aloha
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"        # dev extras: pytest, pytest-asyncio, anyio
```

Frontend (React + Vite):

```bash
cd ui
npm install
npm run build      # writes the SPA into aloha/static/ (see ui/vite.config.ts)
```

Run the whole thing locally against a Home Assistant you already have:

```bash
ALOHA_MODE=standalone ALOHA_HA_URL=http://your-ha:8123 \
ALOHA_DATA_DIR=./.devdata python3 -m aloha
# Aloha UI → http://localhost:7123
```

## Tests

The box test suite runs fully in-process (Starlette TestClient, a stubbed HA) —
no live Home Assistant, no network:

```bash
python3 -m pytest            # unit + integration (fast)
test/smoke.sh                # 18-check end-to-end smoke test
```

- **Unit** tests live in `test/unit/`, **integration** (route-level) in
  `test/integration/`. Fixtures are in `test/conftest.py` — each test gets an
  isolated `data_dir`.
- Please add or update tests with any behavioural change. New tools should have
  at least a registry/smoke assertion; new routes an integration test.
- The UI has a type-check + build gate (`npm run build`); if you add UI logic,
  keep it building clean.

CI (`.github/workflows/test.yml`) runs pytest, the smoke test, and the UI build
on every PR. `build.yml` / `build-addon.yml` publish images on a `v*` tag.

## Coding conventions

- Match the surrounding style. Python is typed where it helps; modules carry a
  short docstring explaining their role (see the top of any file in `aloha/`).
- **Never log or serialize secrets.** Credentials (`api_key`, `ha_token`, MCP
  secrets) are encrypted at rest and must never be written in plaintext or
  echoed in responses/logs. If you touch diagnostics, route it through
  `aloha/telemetry.py`'s `scrub()`.
- Tools that write to HA must be marked with the right safety level so the
  diff→approve gate covers them. Regenerate the tool reference after tool
  changes: `python3 scripts/gen_tool_docs.py`.

## Pull requests

1. Branch from `main`.
2. Keep PRs focused; describe the change and how you tested it.
3. Make sure `python3 -m pytest` and `test/smoke.sh` pass.
4. Link any related issue.

## Reporting bugs

Use the in-app **Report a problem** button (bundles a secrets-free diagnostics
snapshot and opens a prefilled GitHub issue), or open an issue directly with the
bug-report template. See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for
common fixes first.

## License

By contributing you agree your contributions are licensed under the project's
[MIT License](LICENSE).
