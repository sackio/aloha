#!/usr/bin/env bash
# Build the Aloha image locally, run it, and confirm both bundled services come
# up: Home Assistant (:8123) and the Aloha agent (:7123). Tears down on exit.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMG="${IMG:-aloha:confirm}"
HA_PORT="${HA_PORT:-8123}"
UI_PORT="${UI_PORT:-7123}"
NAME="aloha-confirm"

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1; }
trap cleanup EXIT

echo "== building $IMG (this pulls the HA base + builds the UI) =="
docker build -t "$IMG" "$REPO" || { echo "BUILD FAILED"; exit 1; }

echo "== running =="
docker rm -f "$NAME" >/dev/null 2>&1
docker run -d --name "$NAME" -p "$UI_PORT:7123" -p "$HA_PORT:8123" "$IMG" >/dev/null

wait_up() { # wait_up <url> <label> <timeout_s>
  local url="$1" label="$2" deadline=$(( SECONDS + ${3:-180} ))
  while [ "$SECONDS" -lt "$deadline" ]; do
    local c; c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 "$url" 2>/dev/null || echo 000)
    if [ "$c" != "000" ]; then echo "  ✓ $label up (HTTP $c)"; return 0; fi
    sleep 5
  done
  echo "  ✗ $label did not come up"; return 1
}

echo "== waiting for services =="
ok=0
wait_up "http://127.0.0.1:$HA_PORT/" "Home Assistant :$HA_PORT" 120 || ok=1
wait_up "http://127.0.0.1:$UI_PORT/health" "Aloha agent :$UI_PORT" 180 || ok=1

if [ "$ok" = 0 ]; then echo "== Docker image confirmed: bundled HA + Aloha both running =="; else
  echo "== FAILED — logs: =="; docker logs --tail 30 "$NAME"; fi
exit "$ok"
