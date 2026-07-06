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

From inside the running add-on container (where `SUPERVISOR_TOKEN` exists):

```bash
docker exec -it addon_local_aloha python3 /path/to/validate_supervisor.py
# or copy validate_supervisor.py in and run it; add --with-backup to also
# create a real (harmless) backup and list it back.
```

It calls every read tool (`get_environment`, `get_supervisor_info`,
`get_core_info`, `get_os_info`, `check_updates`, `list_addons`, `search_addons`,
`list_backups`, plus `get_addon_info`/`get_addon_logs` for an installed add-on)
and reports pass/fail. This confirms `supervisor.py` works against a live
Supervisor API rather than only the built-to-spec assumption.

## Notes

- The destructive tools (`update_core/os/supervisor`, `reboot_host`,
  `restore_backup`, `uninstall_addon`) are intentionally **not** auto-run by the
  validator. Exercise them by hand on the throwaway VM if you want to confirm
  them end-to-end — that's exactly what the throwaway is for.
- `search_addons` hits the public add-on store, so the VM needs outbound
  network (the default QEMU user-net provides it).
