#!/usr/bin/env bash
# Aloha docker test fixture — bring up scratch HA Core, onboard it, mint an LLAT.
#
# Idempotent: safe to re-run. Writes the token to test/fixtures/docker/.ha_token
# (git-ignored) and prints an env block you can source to run Aloha against it.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES="$(dirname "$HERE")"
HA_URL="${HA_URL:-http://localhost:8124}"
TOKEN_FILE="$HERE/.ha_token"
COMPOSE=(docker compose -f "$HERE/docker-compose.yml")

echo "==> Starting scratch HA Core (docker compose up -d)…"
"${COMPOSE[@]}" up -d

echo "==> Waiting for HA to answer at $HA_URL …"
for i in $(seq 1 60); do
  # /api/ returns 401 until onboarded, but any HTTP response means HA is alive.
  code=$(curl -s -o /dev/null -w '%{http_code}' "$HA_URL/manifest.json" || true)
  if [[ "$code" =~ ^(200|404|401)$ ]]; then
    echo "    HA is up (HTTP $code after ${i}0s)."
    break
  fi
  sleep 10
  if [[ "$i" == "60" ]]; then echo "    HA did not come up in 10min." >&2; exit 1; fi
done

echo "==> Onboarding + minting a long-lived token…"
TOKEN="$(python3 "$FIXTURES/onboard_ha.py" --url "$HA_URL" --user aloha --pass aloha-test)"
printf '%s' "$TOKEN" > "$TOKEN_FILE"
echo "    Token written to $TOKEN_FILE"

cat <<EOF

==> Scratch HA is ready.

    HA URL:   $HA_URL
    Username: aloha  /  Password: aloha-test
    Token:    (in $TOKEN_FILE)

To run Aloha against it (standalone mode):

    export HA_URL="$HA_URL"
    export HA_TOKEN="\$(cat $TOKEN_FILE)"
    python3 -m aloha         # or: ./test/fixtures/docker/run-aloha.sh

Environment detection will report kind="docker" if /var/run/docker.sock is
mounted/visible to the Aloha process; otherwise kind="core".
EOF
