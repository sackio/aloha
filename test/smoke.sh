#!/usr/bin/env bash
# Aloha end-to-end smoke test / demo routine.
#
# Boots the REAL box process against a tiny stub Home Assistant and exercises the
# whole HTTP surface with curl — including the SSE /mcp endpoint with key+secret
# auth, which the in-process pytest suite can't drive. Prints PASS/FAIL per check
# and a summary; exits non-zero on any failure. Everything runs in a temp dir and
# is torn down on exit.
#
#   ./test/smoke.sh            # run against a freshly-launched box
#   PORT=7299 ./test/smoke.sh  # pick ports
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-7298}"
HA_PORT="${HA_PORT:-8199}"
TMP="$(mktemp -d)"
PASS=0; FAIL=0

pass() { echo "  ✓ $1"; PASS=$((PASS+1)); }
fail() { echo "  ✗ $1"; FAIL=$((FAIL+1)); }
check() { # check "<desc>" <actual> <expected>
  if [ "$2" = "$3" ]; then pass "$1 ($2)"; else fail "$1 (got '$2', want '$3')"; fi
}

cleanup() {
  [ -n "${BOX_PID:-}" ] && kill "$BOX_PID" 2>/dev/null
  [ -n "${HA_PID:-}" ] && kill "$HA_PID" 2>/dev/null
  rm -rf "$TMP"
}
trap cleanup EXIT

code() { curl -s -o /dev/null -w '%{http_code}' --max-time 6 "$@"; }
# For SSE endpoints: connect briefly, report the status line without hanging.
sse_code() { curl -s -o /dev/null -w '%{http_code}' --max-time 3 -N "$@"; }

echo "== Aloha smoke test =="
echo "-- starting stub Home Assistant on :$HA_PORT"
cat > "$TMP/stubha.py" <<'PY'
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
async def api(r): return JSONResponse({"message": "API running."})
app = Starlette(routes=[Route("/api/", api), Route("/api", api)])
PY
( cd "$TMP" && python3 -m uvicorn stubha:app --host 127.0.0.1 --port "$HA_PORT" >/dev/null 2>&1 ) &
HA_PID=$!
sleep 2

echo "-- starting Aloha box on :$PORT"
ALOHA_DATA_DIR="$TMP/data" ALOHA_PORT="$PORT" ALOHA_HA_URL="http://127.0.0.1:$HA_PORT" \
  python3 -m aloha > "$TMP/box.log" 2>&1 &
BOX_PID=$!

echo "-- waiting for box health"
B="http://127.0.0.1:$PORT"
up=""
for _ in $(seq 1 30); do
  if [ "$(code $B/health)" = "200" ]; then up=1; break; fi
  sleep 1
done
[ -n "$up" ] || { echo "box did not come up; log:"; tail -20 "$TMP/box.log"; exit 1; }

echo "== health =="
check "health 200" "$(code $B/health)" 200

echo "== skills =="
N=$(curl -s --max-time 6 $B/api/skills | python3 -c "import sys,json;print(len(json.load(sys.stdin)))")
[ "$N" -ge 20 ] && pass "skill catalog has $N skills" || fail "skill catalog only $N"
SLUG=$(curl -s --max-time 6 -X POST $B/api/skills -H 'content-type: application/json' \
  -d '{"name":"Smoke Skill","content":"1. step"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['name'])")
check "upload skill" "$SLUG" "smoke-skill"
check "fetch uploaded skill" "$(code $B/api/skills/$SLUG)" 200
check "delete user skill" "$(code -X DELETE $B/api/skills/$SLUG)" 200
BUILTIN=$(curl -s --max-time 6 $B/api/skills | python3 -c "import sys,json;print([s['name'] for s in json.load(sys.stdin) if not s['editable']][0])")
check "built-in delete blocked" "$(code -X DELETE $B/api/skills/$BUILTIN)" 403

echo "== MCP auth (key + secret) =="
check "/mcp open before any key" "$(sse_code $B/mcp)" 200
MK=$(curl -s --max-time 6 -X POST $B/api/mcp-keys -H 'content-type: application/json' -d '{"name":"smoke"}')
KEY=$(echo "$MK" | python3 -c "import sys,json;print(json.load(sys.stdin)['key'])")
SEC=$(echo "$MK" | python3 -c "import sys,json;print(json.load(sys.stdin)['secret'])")
BASIC=$(python3 -c "import base64;print(base64.b64encode(b'$KEY:$SEC').decode())")
check "/mcp 401 without auth" "$(sse_code $B/mcp)" 401
check "/mcp 200 with Basic key:secret" "$(sse_code -H "Authorization: Basic $BASIC" $B/mcp)" 200
AT=$(curl -s --max-time 6 -X POST $B/mcp/token -H "Authorization: Basic $BASIC" -d 'grant_type=client_credentials' \
  | python3 -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))")
[ -n "$AT" ] && pass "token endpoint issued a Bearer" || fail "token endpoint gave no token"
check "/mcp 200 with Bearer token" "$(sse_code -H "Authorization: Bearer $AT" $B/mcp)" 200
check "token endpoint rejects bad secret" \
  "$(code -X POST $B/mcp/token -d "grant_type=client_credentials&client_id=$KEY&client_secret=nope")" 401
check "regenerate key" "$(code -X POST $B/api/mcp-keys/$KEY/regenerate)" 200
check "old secret now 401" "$(sse_code -H "Authorization: Basic $BASIC" $B/mcp)" 401
check "terminate key" "$(code -X DELETE $B/api/mcp-keys/$KEY)" 200
check "/mcp open again after delete" "$(sse_code $B/mcp)" 200

echo "== public URL + relay =="
check "public-url default none" \
  "$(curl -s --max-time 6 $B/api/public-url | python3 -c 'import sys,json;print(json.load(sys.stdin)["provider"])')" none
check "relay status: no account" \
  "$(curl -s --max-time 6 $B/api/relay/status | python3 -c 'import sys,json;print(json.load(sys.stdin)["has_account"])')" False

echo
echo "== summary: $PASS passed, $FAIL failed =="
[ "$FAIL" -eq 0 ]
