---
name: install-hacs-integration
description: Install a custom (community) integration via HACS, restart HA, then guide the user through any UI config flow it needs.
category: integrate
---

Goal: install a HACS custom integration cleanly. HACS downloads the code; HA then loads it,
but many integrations STILL need a UI config flow to actually configure (these tools can't
drive that part — hand it off honestly).

1. **Confirm HACS is present.** Call `hacs_is_installed`. If it returns false, stop and tell
   the user HACS must be installed first (it itself is a one-time UI/config-flow setup) — do
   not try to install HACS via these tools.
2. **Find the repository.** Use `hacs_list_available` to locate the repo by name. If it's not
   listed it may be a custom repo the user must add manually in the HACS UI — tell them so.
3. **Inspect before installing.** Call `hacs_get_repository_info` on the match to confirm it's
   the right project, check the category (integration), and note version + any requirements.
4. **Install.** Call `hacs_install_repository` for the chosen repo. Confirm success in the
   returned result, and check `hacs_list_installed` to verify it now appears.
5. **Restart HA.** Custom integrations need a restart to load. Confirm with the user, then call
   `restart_ha`. Wait for it to come back (`get_ha_version` / `get_system_health`).
6. **Finish setup (often a UI hand-off).** Many custom integrations require configuration via a
   config flow these tools can't drive. Guide the user: Settings → Devices & Services → Add
   Integration → search the integration name → complete the dialog. If instead it's a
   YAML-configured custom integration, invoke `use_skill("safe-config-change")`, add its config
   block, `check_config`, then `reload_all_yaml`.
7. **Verify.** Use `get_config_entry_list` / `get_entities_by_domain` to confirm entities
   appeared, and `get_error_log` to catch load errors. Report the outcome to the user.
