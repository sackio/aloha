---
name: backup-config
description: Snapshot key config files to timestamped copies before a risky change (no full-system backup exists here).
category: operate
---

Goal: a quick safety net before risky edits. Honest scope: there is NO dedicated backup tool —
this snapshots individual config FILES only. Full HAOS/Supervisor snapshots (add-ons, database,
secrets, the whole system) are done in the HA UI under Settings → System → Backups; tell the
user to make one there before anything truly destructive.

1. **Enumerate.** `list_config_files` to see what's present and confirm paths.
2. **Pick the important files.** Whatever the change will touch, plus the core set if relevant:
   `configuration.yaml`, `automations.yaml`, `scripts.yaml`, `scenes.yaml`, and any package/
   include files in scope. Do NOT copy `secrets.yaml` or `.storage/` (off-limits).
3. **Read each.** `read_config_file` for every file you're snapshotting.
4. **Write timestamped copies.** For each, `write_config_file` to a clearly-named backup path,
   e.g. `backups/automations.yaml.2026-06-29T1430.bak` (use the current date/time). Keep the
   original untouched. These `.bak` files are inert and won't be loaded by HA.
5. **Confirm.** List the backup paths you created and note that they can be restored by reading
   a `.bak` and writing it back over the original (then `check_config` + reload).
6. **Remind** the user that for a complete, restorable system backup they should use
   Settings → System → Backups in the HA UI — this file snapshot does not cover the database,
   add-ons, or secrets.
