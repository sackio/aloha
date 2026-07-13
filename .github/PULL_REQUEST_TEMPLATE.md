<!-- Thanks for contributing to Aloha! Keep PRs focused and describe your change. -->

## What & why

<!-- What does this change, and why? Link any related issue (e.g. Fixes #123). -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] New/updated skill (`aloha/skills/library/`)
- [ ] New/updated tool
- [ ] Docs only
- [ ] Refactor / chore

## How I tested

<!-- Commands you ran, setups you tested against. -->

- [ ] `python3 -m pytest` passes
- [ ] `test/smoke.sh` passes (if behaviour changed)
- [ ] UI builds (`cd ui && npm run build`) — if you touched the frontend
- [ ] Regenerated `docs/MCP_TOOLS.md` (`python3 scripts/gen_tool_docs.py`) — if you changed tools

## Checklist

- [ ] No secrets are logged, serialized, or returned in plaintext.
- [ ] Tests added/updated for the change.
- [ ] Docs updated if user-facing behaviour changed.
