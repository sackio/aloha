---
name: system-backup
description: Take a backup before risky changes — full system on HAOS, config snapshot on Docker.
category: operate
---

Goal: create a restore point, using the best mechanism the environment offers.

1. **Detect the environment.** Call `get_environment`.
2. **HAOS/Supervised — full system backup:** `create_backup` (optionally with a name). This
   captures Core config, add-ons, and settings. Confirm it succeeded with `list_backups`.
   To restore later: `restore_backup` with the backup slug (warn — it overwrites current state).
3. **Docker — config snapshot:** there's no Supervisor backup, so use the `backup-config`
   skill to snapshot the HA config files (configuration.yaml, automations, scripts, scenes,
   etc.) to timestamped copies. Be honest with the user that this covers *config*, not the
   full container/database — a complete backup means archiving the HA config volume on the
   host (`docker` + a tar of the mounted `/config`).
4. **Always back up before:** upgrading HA, bulk automation/config edits, installing/removing
   integrations or add-ons, or restoring anything.
