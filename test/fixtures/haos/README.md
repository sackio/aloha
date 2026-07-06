# HAOS test fixture

Boots a **throwaway Home Assistant OS** VM so we can validate the Supervisor
path — the 22 tools in `aloha/mcp/tools/supervisor.py` and the local add-on in
`haos-addon/` — which a plain-Docker install (`../docker`) can't exercise.

HAOS is the appliance install: a full OS running the **Supervisor**, the add-on
store, and system backups. Aloha's job on HAOS is to *administer the box*
(update Core/OS/Supervisor, manage add-ons, take backups), and that only works
where a `SUPERVISOR_TOKEN` is injected — i.e. inside a real HAOS.

## Requirements (host)

- KVM (`/dev/kvm`), `qemu-system-x86_64`, OVMF UEFI firmware, `xz`, `curl`.
  Debian/Ubuntu: `sudo apt install qemu-system-x86 ovmf`.
- ~4 GB free RAM, ~35 GB free disk (the VM disk grows to 32 GB).

## 1. Boot the VM

```bash
./boot-vm.sh                 # downloads HAOS (cached) + boots, HA on host :8125
HAOS_VERSION=18.1 ./boot-vm.sh
```

The image is downloaded once to `.cache/` (git-ignored) and reused. First boot
installs Supervisor + Core and takes several minutes. HA lands at
<http://localhost:8125>. QEMU runs headless on the serial console — quit with
`Ctrl-a` then `x`. `./teardown.sh` removes the VM + cache.

## 2. Onboard

Either through the browser at <http://localhost:8125>, or non-interactively with
the shared helper (same REST flow as the docker fixture):

```bash
python3 ../onboard_ha.py --url http://localhost:8125 --user aloha --pass aloha-test
```

## 3. Install Aloha as a local add-on

Local add-ons live in the HAOS `/addons` share. Get `haos-addon/` into it, then
install from the **Local add-ons** repository:

1. Install the **Advanced SSH & Web Terminal** add-on (Settings → Add-ons →
   Add-on Store), or the **Samba share** add-on, to reach the filesystem.
2. Copy the repo's `haos-addon/` directory to `/addons/aloha/` on the VM
   (via `scp`/Samba, or `git clone` from inside the SSH add-on).
3. Settings → Add-ons → Add-on Store → **⋮ → Check for updates**. "Aloha"
   appears under *Local add-ons*. Open it → **Install** → **Start**.
4. The add-on's `config.yaml` declares `hassio_api: true`, `hassio_role: admin`,
   and `auth_api: true`, so the Supervisor injects a `SUPERVISOR_TOKEN` with
   full admin — exactly what the supervisor tools need.

## 4. Validate the Supervisor toolset

There are two validators — pick based on how much fidelity you need.

### 4a. Fast path — from outside the VM (no add-on install)

`validate_via_ws.py` drives the **real** Supervisor without installing Aloha.
HA Core holds its own Supervisor token and proxies Supervisor calls for admins
over the authenticated WebSocket `supervisor/api` command (this is how the
frontend's Supervisor panel works). The harness monkeypatches
`supervisor.py`'s `_sup` to route through that proxy, then runs the **actual**
tool dispatch — so it validates the real path construction, response unwrapping,
and output formatting against a live Supervisor.

```bash
# after onboarding (step 2), with the admin LLAT:
python3 validate_via_ws.py --url http://localhost:8125 --token <admin-LLAT>
python3 validate_via_ws.py --with-backup   # also create + list a real backup
```

This is the quick, CI-friendly check. Two caveats, both inherent to the proxy:
- `get_environment` reports the **harness host's** environment (it detects the
  process it runs in), not the target box — ignore its `kind` here.
- `get_addon_logs` is skipped: the Supervisor logs endpoint returns plain text,
  which the JSON-only WS proxy can't carry. Covered by 4b instead.

Verified against **HAOS 18.1 / Supervisor 2026.06.2 / Core 2026.7.1**: all read
tools pass, `search_addons` lists the store, `install_addon` (core_ssh) works,
`get_addon_info` on the installed add-on works, and `create_backup` +
`list_backups` round-trip a real backup.

### 4b. Full fidelity — inside the add-on container

`validate_supervisor.py` runs where a real `SUPERVISOR_TOKEN` is injected, so it
also exercises `get_addon_logs` and the true env detection (`kind="haos"`):

```bash
docker exec -it addon_local_aloha python3 /path/to/validate_supervisor.py
# add --with-backup to also create a real backup and list it back.
```

## Notes

- The destructive tools (`update_core/os/supervisor`, `reboot_host`,
  `restore_backup`, `uninstall_addon`) are intentionally **not** auto-run by the
  validator. Exercise them by hand on the throwaway VM if you want to confirm
  them end-to-end — that's exactly what the throwaway is for.
- `search_addons` hits the public add-on store, so the VM needs outbound
  network (the default QEMU user-net provides it).
