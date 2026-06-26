---
name: triage-unavailable-entities
description: Find entities that are unavailable/unknown and diagnose why (common cause of "my light won't turn off").
category: debug
---

Goal: surface broken entities and explain the likely cause, because an `unavailable`
entity silently breaks group actions and automations (a `homeassistant.turn_off` on a
group skips unavailable members with no error).

1. **Find them.** `get_all_states` and filter for entities whose state is `unavailable`
   or `unknown`. Group the results by domain and by integration/device where possible.
2. **Group by likely cause.** For each broken entity:
   - `get_entity_state` for its attributes, and `get_device_info` / `list_devices` to find
     the owning device and integration.
   - A whole integration's entities unavailable → integration/hub offline or a bad reload.
   - A single device → that device is powered off, off-network, or its IP changed.
3. **Confirm integration health.** `list_integrations` and `get_error_log` — look for the
   integration failing to set up or connection errors (timeouts, auth failures, wrong host).
4. **Report clearly.** List the broken entities grouped by root cause, with the most likely
   reason for each (device offline vs. integration down vs. config error).
5. **Suggest fixes** (do not apply silently): power-cycle the device, fix a wrong IP/host in
   the integration config, reload the integration (`reload_config_entry`), or remove a
   permanently-dead entity. Apply config fixes only via the diff→approve flow.
