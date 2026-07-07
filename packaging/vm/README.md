# Aloha on a VM — Home Assistant OS

The appliance path: run **Home Assistant OS** in a VM and add the Aloha add-on.
Full Supervisor, so Aloha can manage the whole box (Core/OS updates, add-ons,
backups).

## Install

1. Download HA's official VM image for your hypervisor from
   <https://www.home-assistant.io/installation/> (OVA for VirtualBox/VMware,
   qcow2 for Proxmox/KVM, VHDX for Hyper-V).
2. Import it and boot. Complete Home Assistant onboarding.
3. **Settings → Add-ons → Add-on store → ⋮ → Repositories**, add
   `https://github.com/sackio/aloha`.
4. Install **Aloha** → **Start**. Open it from the sidebar.

## Confirm it works (throwaway HAOS under QEMU)

```bash
./packaging/vm/confirm.sh
```

Boots a throwaway HAOS VM (KVM/OVMF), onboards it, adds the add-on repo, installs
+ starts the Aloha add-on via the Supervisor, and verifies it's running — the
same steps a user follows, automated end-to-end.
