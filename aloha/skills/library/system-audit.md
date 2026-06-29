---
name: system-audit
description: A deeper operate sweep than health-check — versions, integrations, unavailable entities, automations, and pending HACS updates, in one prioritized report.
category: operate
---

Goal: a thorough periodic audit. This complements the quick health-check skill — run that for a
fast status; run this for a deeper, integration-by-integration sweep with update tracking.

1. **Version.** `get_ha_version` — note the running version (is it current / due for update?).
2. **Core health.** `get_system_health` — recorder, cloud, database, and per-integration health.
3. **Integrations.** `list_integrations` — flag any in a failed / retrying / not-loaded setup
   state. These are the highest-priority findings.
4. **Unavailable entities.** `get_all_states` — count `unavailable`/`unknown` entities and
   group them BY integration, so a single failing hub shows as one root cause, not 40 symptoms.
   (Hand off to triage-unavailable-entities via `use_skill` if there are many.)
5. **Automations.** `list_automations` — flag any unexpectedly disabled, and (cross-check
   `get_error_log`) any that are erroring. Note last-triggered staleness if relevant.
6. **Pending updates.** `hacs_list_pending_updates` — list custom integrations/cards with
   available updates (recommend, don't auto-update).
7. **Report — prioritized.**
   - 🔴 broken integrations, erroring automations, root-cause device/hub outages
   - 🟡 disabled automations, pending HACS/core updates, deprecations
   - 🟢 healthy subsystems
   Keep it scannable, attribute symptoms to root causes, and offer to fix the top item —
   but make NO changes without the user asking.
