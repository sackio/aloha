---
name: install-integration
description: Add a new Home Assistant integration — fully via YAML when supported, otherwise prep what you can and hand off the UI config flow to the user.
category: integrate
---

Goal: set up a new integration correctly. The key fork: some integrations are configured
in YAML (you can do these end-to-end); most modern ones use a UI "config flow"
(OAuth / device discovery / credential dialog) that these REST-API tools CANNOT drive.

1. **Identify the integration & its setup method.** Use `list_integrations` to see what's
   already loaded and `render_template` / docs knowledge to decide: does it support YAML
   config, or is it UI-only (config flow)? When unsure, default to treating it as UI-only.
2. **YAML path (you can do this fully).** If the integration supports YAML:
   - Invoke `use_skill("safe-config-change")` and follow it for every file edit.
   - `read_config_file` configuration.yaml (or the relevant include), add the integration's
     config block, referencing secrets via `!secret` (never inline credentials).
   - `check_config`, then `reload_all_yaml` (or `reload_core_config`); use `restart_ha` only
     if the integration requires it, and only with explicit user confirmation.
   - Verify with `get_entities_by_domain` / `list_integrations` that entities appeared.
3. **UI / config-flow path (hand off honestly).** If it's OAuth/discovery/credential-based:
   - Do NOT claim you can click through it. Prepare whatever you can (e.g. add API keys to
     `secrets.yaml` via safe-config-change, or note prerequisites).
   - Then give the user exact steps: Settings → Devices & Services → Add Integration →
     search the integration name → follow the dialog (sign in / enter credentials / pick
     devices). Tell them to report back when done.
4. **Verify after either path.** Use `get_config_entry_list` and `get_entities_by_domain`
   to confirm the integration loaded and entities exist; check `get_error_log` if anything
   looks off. Report the result and the new entity_ids to the user.
