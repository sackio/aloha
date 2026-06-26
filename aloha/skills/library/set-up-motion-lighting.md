---
name: set-up-motion-lighting
description: Create a motion-activated lighting automation (turn a light on when motion is detected, off after a timeout).
category: configure
---

Goal: a robust "motion turns the light on, then off after N minutes of no motion" automation.

1. **Identify the entities.** If the user named a room rather than entity_ids, use
   `get_entities_by_area` (or `search_entities`) to find the motion sensor
   (`binary_sensor.*` with `device_class: motion`) and the target light(s)
   (`light.*` / `switch.*`). Confirm the exact entity_ids with the user if ambiguous.
2. **Confirm behavior.** Default to: on when motion → `on`; off after 5 minutes of no
   motion. Ask the user only if they hinted at different timing or conditions
   (e.g. "only at night" → add a `sun` condition).
3. **Build the YAML.** Compose an automation with:
   - trigger: state of the motion sensor to `"on"` (turn on), and to `"off"`
     `for: "00:05:00"` (turn off).
   - action: a `choose` on the trigger, calling `light.turn_on` / `light.turn_off`.
   Give it a clear `alias` and a stable `id`.
4. **Validate** with `validate_automation_yaml` before writing. Fix any errors.
5. **Create** with `create_automation`. This emits a diff for the user to review and
   approve (supervised mode) — do NOT bypass it.
6. **Activate & verify.** After approval, call `reload_automations`, then confirm it
   exists with `list_automations`. Offer to `trigger_automation` once as a smoke test,
   and tell the user how to test it physically (walk past the sensor).
