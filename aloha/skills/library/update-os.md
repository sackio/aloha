---
name: update-os
description: Update Home Assistant OS (HAOS only) — the underlying appliance operating system.
category: operate
---

Goal: keep the Home Assistant OS itself up to date. This applies ONLY to HAOS.

1. **Detect the environment.** Call `get_environment`. If `kind` is not `haos`, stop: OS
   updates don't apply — a plain-Docker or Supervised install runs on a host OS the user
   maintains themselves (apt/etc.), and Aloha shouldn't touch it. Tell the user that.
2. **Check for an OS update:** `get_os_info` (or `check_updates`) shows the current and
   latest HAOS version. Report it and confirm the user wants to proceed — an OS update
   **reboots the host**, so HA will be briefly unavailable.
3. **Back up first:** `create_backup` (a full system backup), so there's a restore point.
4. **Update:** `update_os`. The host will download the new OS and reboot into it.
5. **Verify after reboot:** once HA is reachable again, `get_os_info` to confirm the new
   version and `get_system_health` to confirm everything came back cleanly.
