# MCP tool reference

Aloha exposes **104 tools** over the Model Context Protocol (and to its own agent). Each tool has a *safety level* — reads are always allowed; writes are shown as a diff for your approval (in `supervised` safety mode) before anything is written.

> Auto-generated from the tool registry. Regenerate: `python3 scripts/gen_tool_docs.py`.


## Entities & devices

| Tool | Safety | Description |
|---|---|---|
| `get_entity_state` | read | Get the current state and all attributes of a single entity. |
| `get_all_states` | read | Get states for all entities in Home Assistant. |
| `get_entities_by_domain` | read | Get all entities belonging to a specific domain (e.g. 'light', 'switch', 'sensor'). |
| `get_entities_by_area` | read | Get all entities assigned to a named area. |
| `search_entities` | read | Full-text search entities by entity_id or friendly name. |
| `get_entity_history` | read | Get state history for an entity over a time range. |
| `get_entity_logbook` | read | Get logbook entries for an entity over a time range. |
| `turn_on` | write_soft | Turn on a light, switch, fan, or other entity. |
| `turn_off` | write_soft | Turn off a light, switch, fan, or other entity. |
| `toggle` | write_soft | Toggle a light, switch, or other entity between on and off. |
| `set_light_brightness` | write_soft | Set light brightness (0–255, where 255 is full brightness). |
| `set_light_color` | write_soft | Set light RGB color. |
| `set_light_color_temp` | write_soft | Set light color temperature in mireds (lower = cooler/bluer, higher = warmer/yellower). |
| `set_cover_position` | write_soft | Set cover or blind position (0 = fully closed, 100 = fully open). |
| `set_climate_temperature` | write_soft | Set thermostat target temperature. |
| `set_climate_hvac_mode` | write_soft | Set thermostat HVAC mode (e.g. 'heat', 'cool', 'auto', 'off'). |
| `set_fan_speed` | write_soft | Set fan speed as a percentage (0–100). |
| `lock_entity` | write_soft | Lock a lock entity. |
| `unlock_entity` | write_soft | Unlock a lock entity. |
| `run_script` | write_soft | Execute a Home Assistant script entity. |
| `call_service_raw` | write_soft | Call any Home Assistant service with arbitrary service data. |

## Automations, scripts & scenes

| Tool | Safety | Description |
|---|---|---|
| `list_automations` | read | List all automations with their id, alias, and enabled state. |
| `get_automation` | read | Get the full YAML definition of a single automation. |
| `trigger_automation` | write_soft | Manually trigger an automation to run immediately. |
| `enable_automation` | write_soft | Enable a currently disabled automation. |
| `disable_automation` | write_soft | Disable a currently enabled automation. |
| `create_automation` | write_config | Create a new automation by providing its YAML configuration. Returns a DiffEvent dict for user approval — does NOT write directly. |
| `update_automation` | write_config | Update an existing automation's YAML configuration. Returns a DiffEvent dict for user approval — does NOT write directly. |
| `delete_automation` | destructive | Permanently delete an automation. This action is irreversible. |
| `reload_automations` | write_soft | Reload all automations from disk by calling the automation.reload service. |
| `validate_automation_yaml` | read | Validate automation YAML syntax without saving it to disk. |

## Configuration files

| Tool | Safety | Description |
|---|---|---|
| `read_config_file` | read | Read the contents of a file from the Home Assistant configuration directory. |
| `list_config_files` | read | List files in the Home Assistant configuration directory. Optionally filter by glob pattern (e.g. '*.yaml'). |
| `write_config_file` | write_config | Propose writing or overwriting a file in the HA configuration directory. Returns a DiffEvent dict for user approval — never writes directly. Access to secrets.yaml and .storage/ is denied. |
| `append_config_file` | write_config | Propose appending content to a config file. Returns a DiffEvent dict for user approval — never writes directly. |
| `delete_config_file` | destructive | Permanently delete a file from the HA configuration directory. This action is irreversible. |
| `check_config` | read | Run Home Assistant's built-in configuration check and return the result. |
| `get_config_entry_list` | read | List all Home Assistant config entries (loaded integrations). |
| `reload_config_entry` | write_soft | Reload a specific integration config entry by domain name. |
| `get_ha_config` | read | Get the Home Assistant core configuration (location, units, components, etc.). |
| `render_template` | read | Render a Jinja2 template string using Home Assistant's template engine. |

## Dashboards

| Tool | Safety | Description |
|---|---|---|
| `list_dashboards` | read | List all Lovelace dashboards configured in Home Assistant. |
| `get_dashboard` | read | Get the full YAML configuration for a Lovelace dashboard. |
| `get_dashboard_view` | read | Get the configuration for a single view within a dashboard. |
| `create_dashboard` | write_config | Create a new Lovelace dashboard. Returns a DiffEvent dict for user approval — does not write directly. |
| `update_dashboard` | write_config | Update the configuration of an existing Lovelace dashboard. Returns a DiffEvent dict for user approval — does not write directly. |
| `delete_dashboard` | destructive | Permanently delete a Lovelace dashboard. This action is irreversible. |
| `add_card_to_view` | write_config | Add a card to a specific view in a dashboard. Returns a DiffEvent dict for user approval. |
| `update_card` | write_config | Update an existing card in a dashboard view. Returns a DiffEvent dict for user approval. |
| `remove_card` | destructive | Remove a card from a dashboard view. This action is irreversible. |

## HACS

| Tool | Safety | Description |
|---|---|---|
| `hacs_is_installed` | read | Check whether HACS is installed and accessible in Home Assistant. |
| `hacs_list_installed` | read | List all repositories currently installed via HACS. |
| `hacs_list_available` | read | Search available HACS repositories by keyword and optional category. |
| `hacs_get_repository_info` | read | Get detailed information for a specific HACS repository. |
| `hacs_install_repository` | destructive | Install a HACS repository. This is a DESTRUCTIVE action that may require a Home Assistant restart. |
| `hacs_uninstall_repository` | destructive | Uninstall a HACS repository. This is a DESTRUCTIVE action that may require a Home Assistant restart. |
| `hacs_update_repository` | write_config | Update a HACS repository to the latest available version. |
| `hacs_list_pending_updates` | read | List all HACS repositories that have available updates. |

## System & diagnostics

| Tool | Safety | Description |
|---|---|---|
| `get_system_health` | read | Get the Home Assistant system health report. |
| `get_ha_version` | read | Get the currently running Home Assistant version. |
| `get_error_log` | read | Retrieve the Home Assistant error log. |
| `get_logbook` | read | Get general Home Assistant logbook entries (not entity-specific). |
| `list_integrations` | read | List all loaded integrations (config entries). |
| `list_devices` | read | List all Home Assistant devices. |
| `list_areas` | read | List all Home Assistant areas. |
| `list_floors` | read | List all Home Assistant floors. |
| `get_device_info` | read | Get detailed information for a specific device. |
| `restart_ha` | destructive | Restart Home Assistant. This is a DESTRUCTIVE action and will interrupt all running automations and connected clients. |
| `reload_core_config` | write_config | Reload the Home Assistant core configuration without restarting. |
| `reload_all_yaml` | write_config | Reload all YAML-based domains: automations, scripts, scenes, groups, input_booleans, input_numbers, input_selects, and template entities. |
| `create_persistent_notification` | write_soft | Create a persistent notification visible in the Home Assistant UI. |
| `dismiss_persistent_notification` | write_soft | Dismiss a persistent notification from the Home Assistant UI. |
| `send_notification` | write_soft | Send a notification via a notify service (e.g. mobile app, Pushover). |
| `fire_event` | write_soft | Fire a custom Home Assistant event on the event bus. |

## Skills

| Tool | Safety | Description |
|---|---|---|
| `list_skills` | read | List Aloha's built-in Home Assistant skills (curated playbooks for configure/debug/operate tasks). Returns each skill's name, category, and a one-line description of when to use it. |
| `use_skill` | read | Load the full step-by-step playbook for a named skill and follow it. Call this when the user's request matches a skill from the skill index or list_skills(). Returns the skill's markdown instructions. |

## Supervisor (HAOS/Supervised)

| Tool | Safety | Description |
|---|---|---|
| `get_environment` | read | Detect the HA environment (haos / docker / core) and which system-management path is available. Call this BEFORE upgrading/backing up so you use the right tools. |
| `get_supervisor_info` | read | Get Supervisor info (version, channel, healthy state). HAOS/Supervised only. |
| `get_core_info` | read | Get HA Core info: current version and whether an update is available. HAOS/Supervised only. |
| `get_os_info` | read | Get Home Assistant OS info: version and available OS update. HAOS only. |
| `check_updates` | read | Check for available Core / OS / Supervisor updates in one call. HAOS/Supervised only. |
| `list_addons` | read | List installed add-ons (slug, name, version, state, update available). HAOS/Supervised only. |
| `search_addons` | read | Search the add-on store for available add-ons by name/description. |
| `get_addon_info` | read | Get details for one add-on by slug. |
| `get_addon_logs` | read | Get recent logs for an add-on by slug. |
| `list_backups` | read | List system backups (slug, name, date, size). HAOS/Supervised only. |
| `start_addon` | write_soft | Start an add-on by slug. |
| `stop_addon` | write_soft | Stop an add-on by slug. |
| `restart_addon` | write_soft | Restart an add-on by slug. |
| `install_addon` | write_config | Install an add-on from the store by slug. |
| `update_addon` | write_config | Update an installed add-on to the latest version by slug. |
| `create_backup` | write_soft | Create a full system backup. HAOS/Supervised only. |
| `update_core` | destructive | Update Home Assistant Core to the latest version. Restarts HA. HAOS/Supervised only. |
| `update_supervisor` | destructive | Update the Supervisor to the latest version. HAOS/Supervised only. |
| `update_os` | destructive | Update Home Assistant OS to the latest version. Reboots the host. HAOS only. |
| `uninstall_addon` | destructive | Uninstall an add-on by slug (removes it). |
| `restore_backup` | destructive | Restore a full system backup by slug. Overwrites current state. HAOS/Supervised only. |
| `reboot_host` | destructive | Reboot the host machine. HAOS only. |

## Docker

| Tool | Safety | Description |
|---|---|---|
| `docker_list_containers` | read | List Docker containers (name, image, state). Docker installs only. |
| `docker_container_info` | read | Inspect a container by name or id (image, status, created). |
| `docker_container_logs` | read | Get recent logs for a container by name or id. |
| `docker_restart_container` | write_soft | Restart a container by name or id. |
| `docker_pull_image` | write_config | Pull a Docker image (e.g. 'ghcr.io/home-assistant/home-assistant:stable'). |
| `update_ha_docker` | destructive | Upgrade the Home Assistant container on a Docker install: pull its latest image, then guide the recreate. Docker installs only. |
