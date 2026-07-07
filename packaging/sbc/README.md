# Aloha on an SBC — Home Assistant OS

Raspberry Pi 4/5, ODROID, and other arm64 boards run **Home Assistant OS**
directly. Flash the official per-board image, then add the Aloha add-on — you get
the full appliance (Supervisor, backups, OTA OS updates) with Aloha managing it.

## Install

1. Open **Raspberry Pi Imager** → Choose OS → *Other specific-purpose OS* →
   *Home Assistant and Home Automation* → **Home Assistant OS** (pick your board).
   (Or download the board image from <https://www.home-assistant.io/installation/>.)
2. Flash to the SD card / SSD, boot the board, complete onboarding.
3. **Settings → Add-ons → Add-on store → ⋮ → Repositories**, add
   `https://github.com/sackio/aloha`.
4. Install **Aloha** → **Start**.

The Aloha add-on image is multi-arch (`aarch64`), so it runs natively on
the Pi. Same add-on as the VM — see [`../vm/`](../vm/) for the automated HAOS
confirm (arm boards get their final sign-off on real hardware).
