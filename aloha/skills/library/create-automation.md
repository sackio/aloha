---
name: create-automation
description: The general workflow for turning ANY natural-language request into a Home Assistant automation.
category: configure
---

Goal: reliably translate a free-form "when X happens, do Y" request into a validated, approved automation. This is the generic counterpart to `set-up-motion-lighting` — use it for any automation that doesn't have a more specific skill.

1. **Clarify intent.** Restate the request as trigger(s) → condition(s) → action(s). Pin down anything vague: which entity, what threshold, what time window, what should happen on the "reset" side. Ask the user only about genuinely ambiguous points.
2. **Discover entities.** If the user named rooms/devices instead of entity_ids, resolve them with `get_entities_by_area`, `search_entities`, or `get_entities_by_domain`. Use `get_entity_state` to confirm an entity's current state/attributes. Confirm any ambiguous entity_id with the user before building.
3. **Build the YAML.** Compose the automation with a clear `alias`, a stable `id`, and explicit `trigger`/`condition`/`action` blocks. Reference real `entity_id`s and real service calls. Add conditions (e.g. a `sun` or time condition) only if the request implies them.
4. **Validate** with `validate_automation_yaml` before creating. Fix every reported error and re-validate.
5. **Create** with `create_automation`. This emits a diff for the user to review and approve (supervised mode) — present it clearly and do NOT bypass approval.
6. **Activate.** After approval, call `reload_automations`.
7. **Verify.** Confirm it exists with `list_automations` / `get_automation`. Offer to `trigger_automation` once as a smoke test, and tell the user how to exercise the real-world trigger.
