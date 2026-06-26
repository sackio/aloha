---
name: health-check
description: Run a whole-home health check and produce a prioritized summary of issues.
category: operate
---

Goal: a quick, comprehensive status report the user can act on.

1. **Core status.** `get_ha_version` and `get_system_health` for the overall picture
   (integration health, recorder, cloud, etc.).
2. **Broken entities.** `get_all_states`; count entities that are `unavailable`/`unknown`
   and group by integration (see the triage-unavailable-entities skill if there are many).
3. **Errors.** `get_error_log`; summarize recurring errors/warnings — collapse duplicates,
   surface the top offenders rather than dumping the whole log.
4. **Automations.** `list_automations`; note any unexpectedly disabled, and any that error.
5. **Integrations.** `list_integrations`; flag any in a failed/retry setup state.
6. **Report.** Produce a prioritized summary:
   - 🔴 needs attention (broken integrations, recurring errors, unavailable devices)
   - 🟡 worth a look (disabled automations, deprecations)
   - 🟢 healthy
   Keep it scannable. Offer to fix the top item, but make no changes without the user asking.
