---
name: analyze-error-log
description: Pull and summarize the HA error log — collapse duplicates, surface top recurring errors with likely causes.
category: operate
---

Goal: turn a noisy log into a short, prioritized list of what's actually wrong — and recommend
fixes without applying them.

1. **Pull the log.** `get_error_log`. (For broader context on a specific entity/automation you
   can also use `get_logbook` or `get_entity_logbook`, but start with the error log.)
2. **Collapse duplicates.** Group near-identical lines (same component + message, varying only
   timestamp/entity). Count occurrences per group — frequency is the priority signal.
3. **Rank.** Order by impact × frequency. A repeating integration setup failure or a template
   error firing every few seconds outranks a one-off warning.
4. **Diagnose.** For each top offender, name the likely cause: which integration/component,
   and whether it's a config error, an unavailable device/network issue, a deprecation, or a
   template/automation bug. Cross-reference with `get_entity_state` / `list_integrations` if it
   helps pin the source.
5. **Report.** For each of the top ~3-5 issues: the error (collapsed), how often it occurs, the
   likely cause, and a RECOMMENDED fix. Note deprecation warnings separately as lower priority.
6. **Do not auto-apply.** Recommend only. Offer to take the next step (e.g. run debug-automation,
   open the relevant config) if the user wants — but make no changes without being asked.
