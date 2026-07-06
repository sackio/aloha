#!/usr/bin/env bash
# Tear down the docker test fixture: stop + remove the scratch HA and its volume.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "==> docker compose down -v (removes the scratch HA + its config volume)…"
docker compose -f "$HERE/docker-compose.yml" down -v
rm -f "$HERE/.ha_token"
echo "==> Done. Scratch HA and token removed."
