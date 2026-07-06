---
name: manage-addons
description: Install, update, start/stop, or remove Home Assistant add-ons (HAOS/Supervised only).
category: integrate
---

Goal: manage add-ons via the Supervisor. Add-ons are a HAOS/Supervised concept.

1. **Confirm the environment.** Call `get_environment`. If `kind` is not `haos`, add-ons
   aren't available (plain Docker has no Supervisor/add-on store) — tell the user, and for
   custom components suggest the `install-hacs-integration` skill instead.
2. **See what's installed:** `list_addons` (slug, name, version, state, update available).
3. **Find a new add-on:** `search_addons` with a query to browse the store; `get_addon_info`
   for details on a specific slug before installing.
4. **Install:** `install_addon` with the slug, then `start_addon`. Many add-ons need
   configuration in the HA UI afterward (Settings → Add-ons → the add-on → Configuration) —
   tell the user what to set.
5. **Lifecycle:** `start_addon` / `stop_addon` / `restart_addon`, and `update_addon` when an
   update is available. `get_addon_logs` to troubleshoot one that won't start.
6. **Remove:** `uninstall_addon` — confirm with the user first, since it deletes the add-on
   and its config.
