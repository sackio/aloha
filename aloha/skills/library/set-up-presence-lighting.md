---
name: set-up-presence-lighting
description: Create lights that follow presence — on when someone is home/arrives, off when everyone leaves (optional sun condition).
category: configure
---

Goal: lights that track presence — turn on when a person/device is home (optionally only after dark), and off when presence clears.

1. **Identify the entities.** Find the presence source — a `person.*` entity or `device_tracker.*` — with `get_entities_by_domain` (`person` / `device_tracker`) or `search_entities`. Find the target light(s) with `get_entities_by_area` / `get_entities_by_domain` (`light` / `switch`). Confirm ambiguous entity_ids with the user.
2. **Confirm behavior.** Default: when the tracker goes to `home` → lights on; when it goes to `not_home` (or all trackers are away) → lights off. If the user said "only at night" or "after dark," add a `sun` condition (`below_horizon`). Ask only if timing/conditions are unclear.
3. **Build the YAML.** Compose automation(s) with:
   - trigger: state of the `person`/`device_tracker` to `home` (turn on) and to `not_home` (turn off).
   - optional condition: `sun` below horizon for the turn-on path.
   - action: `light.turn_on` / `light.turn_off` on the target light(s), ideally via a `choose` on the trigger.
   Give a clear `alias` and stable `id`.
4. **Validate** with `validate_automation_yaml`; fix errors and re-validate.
5. **Create** with `create_automation` — it emits a diff for the user to approve. Do NOT bypass approval.
6. **Activate & verify.** After approval call `reload_automations`, confirm with `list_automations`, offer a `trigger_automation` smoke test, and tell the user how to test it (toggle their presence / device_tracker).
