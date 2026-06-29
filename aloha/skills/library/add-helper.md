---
name: add-helper
description: Create an input helper (input_boolean, input_number, input_text, input_select, input_datetime) by editing YAML config safely, validating, and reloading.
category: integrate
---

Goal: add a helper entity via YAML. (Helpers can also be made in the UI under Settings →
Devices & Services → Helpers, but YAML-defined helpers are fully doable with these tools.)

1. **Pick the right domain.** Map the user's need to a helper type: `input_boolean` (on/off
   toggle), `input_number` (slider/box), `input_text` (string), `input_select` (dropdown of
   options), `input_datetime` (date and/or time). Confirm name and options with the user.
2. **Follow safe-config-change for the edit.** Invoke `use_skill("safe-config-change")` and
   obey it for every file write.
3. **Locate the right config block.** `read_config_file` configuration.yaml; use
   `list_config_files` if helpers live in an include. Find or create the top-level key for the
   chosen domain (e.g. `input_boolean:`), preserving existing entries.
4. **Add the helper definition.** Append the new helper under its domain key with a stable slug
   id and sensible attributes — e.g. `name`, `icon`; for `input_number` include `min`/`max`/
   `step`; for `input_select` include the `options` list; for `input_datetime` set
   `has_date`/`has_time`. Don't disturb existing helpers.
5. **Validate & write.** Use `render_template` to sanity-check any templated default if used,
   then `write_config_file` (via the diff gate from safe-config-change), then `check_config`.
   If invalid, stop and show the error rather than reloading.
6. **Reload & verify.** Call `reload_all_yaml` (helpers reload without a restart). Confirm the
   new entity exists with `get_entity_state` (e.g. `input_boolean.<slug>`) and report the
   entity_id to the user.
