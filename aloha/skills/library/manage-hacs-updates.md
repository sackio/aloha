---
name: manage-hacs-updates
description: Check for and apply pending HACS updates, restart HA if required, and verify everything still loads.
category: integrate
---

Goal: keep HACS custom components up to date safely, one at a time, with verification.

1. **List what's pending.** Call `hacs_list_pending_updates` to see which repos have updates.
   If none, tell the user everything is current and stop.
2. **Review each update.** For each pending repo, call `hacs_get_repository_info` to see the
   installed vs. available version and read release notes / breaking-change notes. Surface
   anything risky (major version bumps, breaking changes) to the user before proceeding.
3. **Confirm scope with the user.** Ask whether to update all pending repos or only specific
   ones. Don't bulk-update blindly if any release notes flagged breaking changes.
4. **Apply updates.** For each approved repo, call `hacs_update_repository`. Confirm success in
   the returned result before moving to the next one.
5. **Restart if required.** Most integration updates need a restart to take effect. Confirm
   with the user, then call `restart_ha`. Wait for it to return (`get_ha_version` /
   `get_system_health`).
6. **Verify.** Re-run `hacs_list_pending_updates` to confirm the updates cleared, check
   `get_error_log` for load failures introduced by the new versions, and spot-check affected
   entities with `get_entities_by_domain`. Report what was updated and the new versions.
