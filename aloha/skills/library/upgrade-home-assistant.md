---
name: upgrade-home-assistant
description: Upgrade Home Assistant to the latest version — works on both HAOS/Supervised and plain Docker.
category: operate
---

Goal: safely upgrade Home Assistant, using the right mechanism for the environment.

1. **Detect the environment first.** Call `get_environment`. `kind` is `haos` (Supervisor
   available), `docker` (Docker socket), or `core` (neither — you can't upgrade from here;
   tell the user to update their install manually).
2. **Back up before upgrading.** On HAOS use `create_backup`. On Docker, use the
   `backup-config` skill (snapshot config files) — note a full container backup needs host
   tooling.
3. **Check what's available (HAOS):** `check_updates` shows Core / OS / Supervisor versions
   and whether updates exist. Report them to the user and confirm before proceeding.
4. **Upgrade:**
   - **HAOS/Supervised:** `update_core` (this pulls the new Core and restarts HA). If the
     Supervisor itself is behind, `update_supervisor` first.
   - **Docker:** `update_ha_docker` — it pulls the latest image for the HA container, then
     tells you how to recreate it (a plain restart keeps the old image). If it's compose-
     managed, the user runs `docker compose up -d`; otherwise recreate with the same
     volumes/env. Use `docker_restart_container` only after the recreate.
5. **Verify.** After it comes back, confirm the new version (`get_core_info` on HAOS, or
   `docker_container_info` on Docker) and run a quick `check_config` / health check.
6. **If anything breaks,** restore the backup you took in step 2.
