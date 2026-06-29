---
name: build-dashboard
description: Create a new Lovelace dashboard for a room or purpose, populated with sensible cards.
category: configure
---

Goal: stand up a useful Lovelace dashboard for a room or purpose, with cards for the relevant entities.

1. **Clarify scope.** Confirm the dashboard's title/purpose (e.g. a single room, a "Climate" overview, a "Security" view) and which categories of entities it should surface.
2. **Discover entities.** For a room, use `get_entities_by_area` to pull its entities; otherwise use `get_entities_by_domain` (lights, climate, sensors, covers, locks, media_player) or `search_entities`. Group them logically (lights, climate, sensors, etc.) and confirm ambiguous picks with the user.
3. **Create the dashboard.** Call `create_dashboard` with a clear title and a url-slug. This gives you a dashboard with a default view to populate.
4. **Add cards.** Use `add_card_to_view` to add sensible cards per group — e.g. a `light` or `entities` card for lights, a `thermostat` card for `climate.*`, an `entities`/`glance` card for sensors, a `cover` card for shades. Pick card types that match each domain. Use `update_card` / `remove_card` to refine.
5. **Verify.** Call `get_dashboard` (and `get_dashboard_view`) to confirm the views and cards are present and reference real entity_ids. Tell the user the dashboard's URL/slug and offer to adjust the layout.
