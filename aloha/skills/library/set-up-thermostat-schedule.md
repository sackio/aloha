---
name: set-up-thermostat-schedule
description: Create time-based climate control — set thermostat temperature/mode at scheduled times, with optional home/away awareness.
category: configure
---

Goal: schedule a thermostat so it changes setpoint (and optionally HVAC mode) at set times of day, optionally only when someone is home.

1. **Identify the climate entity.** Find it with `get_entities_by_domain` (`climate`) or `get_entities_by_area`; use `get_entity_state` to see supported HVAC modes and the current setpoint. Confirm the exact `climate.*` entity_id with the user if there are several.
2. **Confirm the schedule.** Collect each scheduled change: time of day, target temperature, and (if relevant) HVAC mode (heat/cool/auto/off). If the user wants home/away awareness, find a `person.*` / `device_tracker.*` to gate the actions.
3. **Build the YAML.** Compose automation(s) with:
   - trigger: `time` triggers at each scheduled time (or a `time_pattern`).
   - optional condition: presence (`person`/`device_tracker` is `home`) for "comfort" setpoints; use an away/eco setpoint otherwise.
   - action: `climate.set_temperature` for the setpoint and, when needed, `climate.set_hvac_mode` for the mode. (These map to the `set_climate_temperature` / `set_climate_hvac_mode` tools.)
   Give a clear `alias` and stable `id` per scheduled change.
4. **Validate** with `validate_automation_yaml`; fix errors and re-validate.
5. **Create** with `create_automation` — it emits a diff for the user to approve. Do NOT bypass approval.
6. **Activate & verify.** After approval call `reload_automations`, confirm with `list_automations`, and tell the user when the first scheduled change will fire (offer a `trigger_automation` dry run).
