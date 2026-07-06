#!/usr/bin/env bash
# Aloha HAOS test fixture — boot a throwaway Home Assistant OS VM.
#
# HAOS is the appliance install: a full OS that runs the Supervisor, add-on
# store, and system backups. This fixture boots the official HAOS "OVA" image
# (generic x86-64 qcow2) under QEMU/KVM + UEFI (OVMF) so we can validate the
# Supervisor path — the 22 supervisor.py tools and the HAOS local add-on — that
# a plain-Docker install can't exercise.
#
# Requirements on the host: qemu-system-x86_64, KVM (/dev/kvm), an OVMF UEFI
# firmware, xz, curl. On Debian/Ubuntu: apt install qemu-system-x86 ovmf.
#
# Usage:
#   ./boot-vm.sh                 # download (if needed) + boot, HA on host :8125
#   HAOS_VERSION=18.1 ./boot-vm.sh
#   ./boot-vm.sh --fresh         # discard the VM disk and re-extract a clean image
#
# The VM boots headless (-nographic, serial console). HA lands at
# http://localhost:8125 after ~1-2 min. First boot installs Supervisor + Core
# and can take several minutes. Ctrl-a x quits QEMU; teardown.sh cleans up.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HAOS_VERSION="${HAOS_VERSION:-18.1}"
HOST_HA_PORT="${HOST_HA_PORT:-8125}"   # host port → guest 8123 (HA UI + API)
RAM_MB="${RAM_MB:-4096}"
CPUS="${CPUS:-2}"
CACHE="$HERE/.cache"                    # git-ignored; holds the big image + VM disk
ASSET="haos_ova-${HAOS_VERSION}.qcow2"
URL="https://github.com/home-assistant/operating-system/releases/download/${HAOS_VERSION}/${ASSET}.xz"
DISK="$CACHE/${ASSET}"                  # the working (mutable) VM disk

mkdir -p "$CACHE"

if [[ "${1:-}" == "--fresh" ]]; then
  echo "==> --fresh: removing existing VM disk"
  rm -f "$DISK"
fi

# --- Pre-flight: KVM + OVMF firmware -----------------------------------------
if [[ ! -e /dev/kvm ]]; then
  echo "!! /dev/kvm not present — this host can't run the HAOS VM with KVM." >&2
  echo "   (You can still boot without KVM by editing this script, but it's slow.)" >&2
  exit 1
fi

# Locate OVMF UEFI firmware (paths vary by distro).
OVMF_CODE=""
for p in /usr/share/OVMF/OVMF_CODE.fd /usr/share/ovmf/OVMF.fd \
         /usr/share/edk2/x64/OVMF_CODE.fd /usr/share/qemu/OVMF.fd; do
  [[ -f "$p" ]] && OVMF_CODE="$p" && break
done
if [[ -z "$OVMF_CODE" ]]; then
  echo "!! No OVMF UEFI firmware found. Install it (apt install ovmf)." >&2
  exit 1
fi
# Writable copy of the UEFI variable store (per-VM).
OVMF_VARS="$CACHE/OVMF_VARS.fd"
if [[ ! -f "$OVMF_VARS" ]]; then
  for v in /usr/share/OVMF/OVMF_VARS.fd /usr/share/edk2/x64/OVMF_VARS.fd; do
    [[ -f "$v" ]] && cp "$v" "$OVMF_VARS" && break
  done
  # Fallback: a blank 4M vars store if the distro ships only a combined image.
  [[ -f "$OVMF_VARS" ]] || truncate -s 4M "$OVMF_VARS"
fi

# --- Fetch + extract the HAOS image ------------------------------------------
if [[ ! -f "$DISK" ]]; then
  echo "==> Downloading HAOS $HAOS_VERSION OVA image…"
  echo "    $URL"
  code=$(curl -sL -o "$CACHE/${ASSET}.xz" -w '%{http_code}' "$URL")
  if [[ "$code" != "200" ]]; then
    echo "!! Download failed (HTTP $code). Check that version $HAOS_VERSION exists at" >&2
    echo "   https://github.com/home-assistant/operating-system/releases" >&2
    rm -f "$CACHE/${ASSET}.xz"
    exit 1
  fi
  echo "==> Decompressing (this qcow2 is ~1-2 GB)…"
  xz -dk -T0 "$CACHE/${ASSET}.xz"
  # HAOS disks ship small; grow to 32G so the Supervisor + add-ons have room.
  qemu-img resize "$DISK" 32G >/dev/null
  echo "==> VM disk ready: $DISK"
fi

# --- Boot --------------------------------------------------------------------
cat <<EOF
==> Booting HAOS $HAOS_VERSION under QEMU/KVM (headless serial console).
    HA will come up at:  http://localhost:$HOST_HA_PORT
    First boot installs Supervisor + Core — allow several minutes.
    Quit QEMU: press  Ctrl-a  then  x
EOF

exec qemu-system-x86_64 \
  -machine q35,accel=kvm \
  -cpu host -smp "$CPUS" -m "$RAM_MB" \
  -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" \
  -drive if=pflash,format=raw,file="$OVMF_VARS" \
  -drive file="$DISK",if=virtio,format=qcow2 \
  -netdev user,id=net0,hostfwd=tcp::${HOST_HA_PORT}-:8123 \
  -device virtio-net-pci,netdev=net0 \
  -nographic
