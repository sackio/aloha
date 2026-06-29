---
name: create-scene
description: Create a Home Assistant scene that captures a set of entity states (e.g. "Movie Night") in scenes.yaml.
category: configure
---

Goal: define a reusable scene that sets a group of entities to specific states in one shot.

1. **Clarify the scene.** Get the scene's name/purpose and the desired end-state of each entity (which lights on/dim/color, covers position, climate setpoint, switches, etc.).
2. **Discover entities.** Resolve named rooms/devices to entity_ids with `get_entities_by_area`, `search_entities`, or `get_entities_by_domain`. Use `get_entity_state` to read each entity's current state/attributes as a starting point. Confirm ambiguous entity_ids with the user.
3. **Build the scene YAML.** Compose a scene entry with a stable `id`, a friendly `name`, and an `entities:` map of `entity_id: { state + attributes }` (e.g. `light.x: { state: on, brightness: 120, color_temp: 350 }`). Keep only the attributes that matter.
4. **Write it safely.** Invoke `use_skill` with `safe-config-change` to edit `scenes.yaml`: `read_config_file` it first, append/merge your new scene, and confirm `check_config` is clean. Write through the diff gate with `write_config_file` (or `append_config_file`) — the user reviews and approves the diff.
5. **Reload.** After approval and a clean `check_config`, call `reload_all_yaml` so the scene registers.
6. **Verify.** Confirm the `scene.<name>` entity exists with `get_entity_state` / `get_entities_by_domain`. Offer to activate it once (via `call_service_raw` `scene.turn_on`) as a test, and tell the user how to trigger it.
