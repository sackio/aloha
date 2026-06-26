---
name: debug-automation
description: Diagnose why an automation didn't fire (or fired wrongly) and propose a fix.
category: debug
---

Goal: find the root cause of an automation misbehaving, then propose a concrete fix.

1. **Locate it.** `list_automations` (filter by the alias the user mentioned), then
   `get_automation` to read its full YAML. Note its `id`, triggers, conditions, actions,
   and whether it is currently enabled.
2. **Check it's enabled.** A disabled automation never runs — `list_automations` shows
   state. If disabled and that's unexpected, that's likely the answer.
3. **Inspect the trigger inputs.** For each entity referenced in the triggers/conditions,
   call `get_entity_state`. Look for:
   - entities that are `unavailable`/`unknown` (a condition on them silently fails),
   - states that don't actually match the trigger/condition you expected.
4. **Check recent activity.** Use `get_logbook` (and `get_entity_logbook` for the trigger
   entity) over the relevant window to see whether the trigger entity even changed state
   when the user expected the automation to run.
5. **Test conditions/templates.** If it uses Jinja templates or template conditions, run
   them through `render_template` with current state to see what they actually evaluate to.
6. **Check for errors.** `get_error_log` — look for tracebacks or warnings mentioning this
   automation, its entities, or its integration.
7. **Reproduce.** `trigger_automation` to run it manually. If the manual run works but the
   real trigger doesn't, the problem is the trigger/condition, not the action.
8. **Diagnose & fix.** State the root cause plainly. If a config change is needed, build the
   corrected YAML, `validate_automation_yaml`, then `update_automation` (diff → approve),
   and `reload_automations`. Verify the fix.
