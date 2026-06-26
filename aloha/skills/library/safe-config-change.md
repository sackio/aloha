---
name: safe-config-change
description: The safe workflow for ANY edit to a HA YAML/config file (always validate + check before applying).
category: operate
---

Goal: never break a user's Home Assistant with a bad config write. Follow this whenever you
edit configuration files (configuration.yaml, packages, scripts, includes, etc.).

1. **Read first.** `read_config_file` the target. Understand the surrounding structure; use
   `list_config_files` if you're unsure of the path or how config is split.
2. **Make the minimal change.** Edit only what's needed; preserve comments, formatting, and
   unrelated content. Never touch `secrets.yaml` or `.storage/` (off-limits).
3. **Validate the YAML** you're about to write. For automations use
   `validate_automation_yaml`; for templates use `render_template` to confirm they evaluate.
4. **Write via the diff gate.** Use `write_config_file` (or `create_automation` /
   `update_automation` for automations). This emits a diff for the user to review and
   approve — present the before/after clearly. Do NOT try to bypass approval.
5. **Check config BEFORE reloading.** After the write is approved, call `check_config`. If it
   returns invalid, STOP, show the user the error, and offer to revert (the original content
   is in your context / the pre-edit backup). Do not reload a broken config.
6. **Reload, not restart, when possible.** Prefer `reload_core_config` / `reload_all_yaml` /
   `reload_automations` over `restart_ha`. Only `restart_ha` if a reload can't apply the
   change — and that always requires explicit confirmation.
7. **Verify.** Confirm the intended effect (entity exists, automation listed, template
   renders) and tell the user what changed.
