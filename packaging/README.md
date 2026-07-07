# Aloha distribution artifacts

Two shapes, one agent:

| For | Artifact | How |
|---|---|---|
| **VMs & SBCs (the appliance)** | **Home Assistant OS + the Aloha add-on** | official HAOS image (per board) + our add-on repo |
| **Run-your-own host** | **Docker image** (`ghcr.io/sackio/aloha`) | `docker run` — bundles HA Core + the agent |

## Why HAOS for the VM/SBC images

On **Home Assistant OS** the Supervisor is present, so Aloha runs at full power —
it can update Core/OS/Supervisor, install add-ons, and take real backups (the
`supervisor.py` toolset). That's the whole point of the appliance. The plain
Docker image is HA *Container* (no Supervisor), so there Aloha manages the
container instead. Same agent, different reach.

Aloha ships as a **Home Assistant add-on** (`haos-addon/`), published as
`ghcr.io/sackio/aloha-addon:{arch}` and installable from this repo as an add-on
repository. So any HAOS box — VM or SBC — gets Aloha the standard way.

## VM (Home Assistant OS)

See [`vm/`](vm/). Import HA's official **OVA/qcow2** into Proxmox / VirtualBox /
VMware, then add the Aloha add-on. `vm/confirm.sh` boots a throwaway HAOS under
QEMU and installs + verifies the add-on end-to-end.

## SBC / SD card (Home Assistant OS)

See [`sbc/`](sbc/). Flash HA's official per-board image (Pi 4/5, ODROID, generic
aarch64, …) with Raspberry Pi Imager, then add the Aloha add-on.

## Docker image

See [`docker/`](docker/). Multi-arch (amd64/arm64/armv7), built + pushed to
`ghcr.io/sackio/aloha` by CI on a `v*` tag. Confirmed via `docker/confirm.sh`.

## Adding the Aloha add-on to any HAOS

1. **Settings → Add-ons → Add-on store → ⋮ → Repositories**
2. Add `https://github.com/sackio/aloha`
3. Install **Aloha**, then **Start**. Open it from the sidebar.

(Built + pushed by `.github/workflows/build-addon.yml`; validated on a throwaway
HAOS VM by `vm/confirm.sh`.)
