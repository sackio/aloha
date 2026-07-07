#!/usr/bin/env bash
# Confirm Aloha installs + runs as a Home Assistant OS add-on, end-to-end.
#
# Boots a throwaway HAOS VM (the test/fixtures/haos fixture), onboards it, then
# drives the Supervisor — via HA Core's authenticated WebSocket `supervisor/api`
# proxy — to add the Aloha add-on repository, install the add-on, and start it,
# then verifies it reports "started". This is exactly the user flow (Settings →
# Add-ons → add repo → install), automated.
#
# Requires the add-on image to be pullable — i.e. ghcr.io/sackio/aloha-addon:{arch}
# published (a `v*` tag runs build-addon.yml), OR install as a local add-on.
#
#   ./packaging/vm/confirm.sh
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HA="http://localhost:8125"

echo "== booting a FRESH throwaway HAOS (first boot takes several minutes) =="
# --fresh re-extracts a clean disk each run so onboarding always starts fresh.
"$REPO/test/fixtures/haos/boot-vm.sh" --fresh >/tmp/aloha-haos-confirm.log 2>&1 &
trap 'pkill -f "$REPO/test/fixtures/haos/.cache/haos_ova" 2>/dev/null' EXIT

echo "== waiting for HA onboarding endpoint =="
for _ in $(seq 1 90); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 "$HA/api/onboarding" 2>/dev/null)" = "200" ] && break
  sleep 10
done

echo "== onboarding + minting an admin token =="
LLAT="$(python3 "$REPO/test/fixtures/onboard_ha.py" --url "$HA" --user aloha --pass aloha-test 2>/dev/null | tail -1)"
[ -n "$LLAT" ] || { echo "onboarding failed"; exit 1; }

echo "== install + start the Aloha add-on via the Supervisor =="
python3 - "$HA" "$LLAT" <<'PY'
import asyncio, json, sys
import websockets
HA, LLAT = sys.argv[1], sys.argv[2]
REPO_URL = "https://github.com/sackio/aloha"

async def sup(ws, i, endpoint, method="get", data=None):
    m = {"id": i, "type": "supervisor/api", "endpoint": endpoint, "method": method}
    if data is not None: m["data"] = data
    await ws.send(json.dumps(m))
    while True:
        r = json.loads(await ws.recv())
        if r.get("id") == i: return r

async def main():
    ws_url = HA.replace("http://", "ws://") + "/api/websocket"
    async with websockets.connect(ws_url, max_size=None) as ws:
        await ws.recv(); await ws.send(json.dumps({"type": "auth", "access_token": LLAT})); await ws.recv()
        i = 0
        def nxt():
            nonlocal i; i += 1; return i
        print("adding add-on repository…")
        print(" ", (await sup(ws, nxt(), "/store/repositories", "post", {"repository": REPO_URL})).get("success"))
        await sup(ws, nxt(), "/store/reload", "post")
        await asyncio.sleep(6)

        # Custom-repo add-ons are namespaced (<repo-hash>_aloha) — discover the slug.
        slug = None
        for _ in range(12):
            store = await sup(ws, nxt(), "/store/addons")
            addons = store.get("result", {}).get("addons", store.get("result", [])) if store.get("success") else []
            for a in addons:
                if a.get("slug", "").endswith("_aloha") or a.get("name") == "Aloha":
                    slug = a["slug"]; break
            if slug: break
            await asyncio.sleep(5)
        print("resolved add-on slug:", slug)
        if not slug:
            print("add-on not found in store — dumping diagnostics:")
            res = await sup(ws, nxt(), "/resolution/info")
            issues = res.get("result", {}).get("issues", []) if res.get("success") else res
            print(" resolution issues:", json.dumps(issues)[:600])
            store = await sup(ws, nxt(), "/store/addons")
            adds = store.get("result", {}); adds = adds.get("addons", adds) if isinstance(adds, dict) else adds
            print(" sample store slugs:", [a.get("slug") for a in (adds or [])][:8])
            sys.exit(1)

        print(f"installing add-on '{slug}' (pulls the image)…")
        r = await sup(ws, nxt(), f"/store/addons/{slug}/install", "post")
        print(" install:", r.get("success"), r.get("error", {}).get("message", "") if not r.get("success") else "")
        for _ in range(40):   # pulling the image can take a while
            info = await sup(ws, nxt(), f"/addons/{slug}/info")
            if info.get("success") and info["result"].get("version"):
                break
            await asyncio.sleep(10)
        await sup(ws, nxt(), f"/addons/{slug}/start", "post")
        await asyncio.sleep(8)
        info = await sup(ws, nxt(), f"/addons/{slug}/info")
        state = info["result"].get("state") if info.get("success") else "?"
        print("add-on state:", state)
        sys.exit(0 if state == "started" else 1)

asyncio.run(main())
PY
rc=$?
[ "$rc" = 0 ] && echo "== CONFIRMED: Aloha runs as a HAOS add-on ==" || echo "== add-on did not reach 'started' =="
exit "$rc"
