#!/usr/bin/env bash
# Run the Aloha agent against the scratch HA from this fixture.
# Assumes setup.sh has already run (token present).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
TOKEN_FILE="$HERE/.ha_token"

if [[ ! -s "$TOKEN_FILE" ]]; then
  echo "No token at $TOKEN_FILE — run ./setup.sh first." >&2
  exit 1
fi

export ALOHA_MODE="${ALOHA_MODE:-standalone}"
export HA_URL="${HA_URL:-http://localhost:8124}"
export HA_TOKEN="$(cat "$TOKEN_FILE")"

echo "==> Running Aloha (standalone) against $HA_URL"
cd "$REPO"
exec python3 -m aloha "$@"
