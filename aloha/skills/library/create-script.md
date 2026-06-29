---
name: create-script
description: Create a reusable Home Assistant script (a named sequence of actions) in scripts.yaml.
category: configure
---

Goal: define a reusable script the user (or automations) can call to run a sequence of actions.

1. **Clarify the sequence.** Get the script's name and the ordered list of actions it should perform (service calls, delays, waits, conditions). Note any fields the user wants to parameterize.
2. **Discover entities.** Resolve any named devices/rooms to entity_ids with `get_entities_by_area`, `search_entities`, or `get_entities_by_domain`. Confirm ambiguous entity_ids with the user.
3. **Build the script YAML.** Compose a script entry keyed by a stable slug, with an `alias`, optional `fields:`, and a `sequence:` of steps using real services and entity_ids. Add `delay`/`wait_template` steps where the request implies timing.
4. **Write it safely.** Invoke `use_skill` with `safe-config-change` to edit `scripts.yaml`: `read_config_file` it first, merge your new script in, and write through the diff gate with `write_config_file` (or `append_config_file`). The user reviews and approves the diff; confirm `check_config` is clean.
5. **Reload.** After approval and a clean `check_config`, call `reload_all_yaml` so `script.<slug>` registers.
6. **Verify and test.** Confirm `script.<slug>` exists with `get_entity_state`. Offer to `run_script` once as a smoke test, and report the result to the user.
