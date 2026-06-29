---
name: restart-home-assistant
description: Safely restart Home Assistant — validate config, warn about downtime, then restart and verify it came back.
category: operate
---

Goal: restart HA only when necessary, and never restart into a broken config. A restart drops
automations, integrations, and the UI for ~30-60s+ — it is a last resort, not a routine step.

1. **Prefer a reload.** Before restarting, ask whether a reload would do the job (see the
   reload-configuration skill). `reload_all_yaml` / `reload_core_config` / `reload_automations`
   / `reload_config_entry` pick up most changes with no downtime. Only continue if a restart is
   genuinely required (e.g. integration/core changes a reload can't apply).
2. **Validate first.** Run `check_config`. If it returns invalid, REFUSE to restart — show the
   user the errors and offer to fix or revert. HA may not come back up from a bad config.
3. **Warn the user.** Tell them HA will be unavailable for the duration of the restart and ask
   for explicit confirmation. Do not restart on your own initiative.
4. **Announce it.** `create_persistent_notification` noting the restart and why, so anyone in
   the UI sees the reason.
5. **Restart.** Call `restart_ha`.
6. **Verify it came back.** Poll `get_ha_version`, then `get_system_health`, until HA responds.
   Confirm the version is as expected and core/integrations are healthy.
7. **Report.** Tell the user HA is back up (or, if it didn't return, surface the error and the
   pre-restart config so they can recover). `dismiss_persistent_notification` once confirmed.
