#!/usr/bin/env bash
# Tear down the HAOS test fixture: kill any running VM and remove the cache.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "==> Killing any QEMU booting this fixture's disk…"
pkill -f "$HERE/.cache/haos_ova" 2>/dev/null && echo "    killed." || echo "    (none running)"
echo "==> Removing cached image + VM disk ($HERE/.cache)…"
rm -rf "$HERE/.cache"
echo "==> Done."
