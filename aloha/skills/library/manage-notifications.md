---
name: manage-notifications
description: Send notifications (mobile/notify services) and manage persistent in-UI notifications.
category: operate
---

Goal: get a message to the user the right way — a push to their device, or a persistent banner
in the HA UI — and clean up afterward.

1. **Decide the channel.**
   - Reach the user on their phone/device → a notify service (push, etc.).
   - Surface something in the HA dashboard until acknowledged → a persistent notification.
2. **Discover notify targets.** `get_all_states` and look for `notify.*` services/entities
   (e.g. `notify.mobile_app_<device>`). Pick the one matching the user's device; if several
   exist, ask which to use rather than guessing.
3. **Send a push.** `send_notification` to the chosen notify service with a clear title and
   message. Confirm it was accepted.
4. **Create an in-UI notice.** `create_persistent_notification` with a title, message, and a
   stable notification id (so you can dismiss it later) for things the user should see next
   time they open HA.
5. **Dismiss when done.** `dismiss_persistent_notification` (by id) once the condition clears
   or the user acknowledges — don't leave stale banners piling up.
6. **Report** which channel(s) you used and to which target, so the user knows where to look.
