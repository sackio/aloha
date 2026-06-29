---
name: reload-configuration
description: Apply config changes without a restart — pick the right reload, validate first, then verify.
category: operate
---

Goal: apply changes with zero downtime by reloading only what's affected, instead of restarting.

1. **Validate first.** Run `check_config`. If invalid, STOP — show the user the errors and do
   not reload a broken config.
2. **Pick the narrowest reload** for what changed:
   - Automations only → `reload_automations`.
   - A single integration's config entry (e.g. options changed) → `reload_config_entry`.
   - `configuration.yaml` core sections (zones, customize, etc.) → `reload_core_config`.
   - Multiple YAML domains at once (scripts, scenes, templates, groups, input_*, etc.) →
     `reload_all_yaml`.
   Use the most targeted option that covers the change; `reload_all_yaml` is the broad fallback.
3. **Reload.** Call the chosen reload tool.
4. **Verify.** Confirm the change took effect — e.g. `list_automations` shows the new/updated
   automation, `get_entity_state` reflects the new value, or `render_template` evaluates.
   Spot-check `get_error_log` for fresh errors the reload may have surfaced.
5. **Escalate only if needed.** If the change can't be applied by any reload (core/integration
   wiring), fall back to the restart-home-assistant skill — with the user's confirmation.
6. **Report** what was reloaded and the verified result.
