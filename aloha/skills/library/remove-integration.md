---
name: remove-integration
description: Safely remove an integration or HACS custom component — warn about dependents first, then uninstall/clean YAML, reload/restart, and verify nothing broke.
category: integrate
---

Goal: cleanly remove an integration without leaving broken automations, dashboards, or
orphaned entities behind.

1. **Identify exactly what to remove.** Use `get_config_entry_list` for built-in/config-flow
   integrations and `hacs_list_installed` for HACS custom components. Confirm the precise
   target with the user (name + domain).
2. **Find dependents and WARN.** Before removing anything, search for things that rely on it:
   `get_entities_by_domain` for entities it provides, `list_automations` (+ `get_automation`)
   and dashboards (`list_dashboards` / `get_dashboard`) that reference those entity_ids. Show
   the user what will break and get explicit confirmation to proceed.
3. **Remove it.**
   - HACS component: call `hacs_uninstall_repository` for the repo.
   - YAML integration: invoke `use_skill("safe-config-change")`, `read_config_file`, remove the
     integration's config block (and any related includes/secrets the user agrees are unused),
     then `check_config`.
   - Config-flow/UI integration: these tools can't delete a config entry's UI side. Guide the
     user: Settings → Devices & Services → click the integration → Delete. Hand this off
     honestly rather than claiming you removed it.
4. **Reload or restart.** Prefer `reload_all_yaml` / `reload_core_config` for YAML changes; a
   HACS uninstall needs `restart_ha` (confirm with the user first).
5. **Verify nothing broke.** Confirm the entities are gone (`get_entities_by_domain`), check
   `get_error_log` for missing-platform errors, and re-check the automations/dashboards you
   flagged in step 2 so the user can fix or remove any now-dangling references. Report results.
