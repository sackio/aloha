"""Integration: exercise the box's HTTP routes in-process (no live HA)."""

import base64


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["ha_connected"] is False  # no HA in tests


# --- skills ---------------------------------------------------------------

def test_skills_list_has_builtins(client):
    r = client.get("/api/skills")
    assert r.status_code == 200
    skills = r.json()
    assert len(skills) >= 20
    assert all("editable" in s for s in skills)
    assert not any(s["editable"] for s in skills)  # built-ins only, initially


def test_skill_crud(client):
    # add
    r = client.post("/api/skills", json={"name": "My Test Skill", "content": "1. do a thing"})
    assert r.status_code == 200
    slug = r.json()["name"]
    assert slug == "my-test-skill"
    # now editable + fetchable
    listed = {s["name"]: s for s in client.get("/api/skills").json()}
    assert listed[slug]["editable"] is True
    md = client.get(f"/api/skills/{slug}")
    assert md.status_code == 200
    assert "do a thing" in md.text
    # delete user skill
    assert client.delete(f"/api/skills/{slug}").status_code == 200
    assert slug not in {s["name"] for s in client.get("/api/skills").json()}


def test_cannot_delete_builtin(client):
    builtin = next(s["name"] for s in client.get("/api/skills").json() if not s["editable"])
    r = client.delete(f"/api/skills/{builtin}")
    assert r.status_code == 403


# --- MCP access keys + auth enforcement -----------------------------------

def test_mcp_key_lifecycle_and_enforcement(client):
    # mint
    r = client.post("/api/mcp-keys", json={"name": "laptop"})
    assert r.status_code == 200
    cred = r.json()
    key, secret = cred["key"], cred["secret"]
    assert key.startswith("amk_") and secret.startswith("ams_")

    # list hides the secret
    rows = client.get("/api/mcp-keys").json()
    assert rows[0]["key"] == key
    assert "secret" not in rows[0]

    # a key exists now → /mcp without auth is rejected by the middleware (401,
    # returned before the SSE handler, so no hang)
    assert client.get("/mcp").status_code == 401

    # OAuth2 token endpoint: exchange key+secret (HTTP Basic) for a Bearer token
    basic = base64.b64encode(f"{key}:{secret}".encode()).decode()
    tok = client.post("/mcp/token", headers={"Authorization": f"Basic {basic}"},
                      data={"grant_type": "client_credentials"})
    assert tok.status_code == 200
    assert tok.json()["token_type"] == "Bearer"

    # bad secret → invalid_client
    bad = base64.b64encode(f"{key}:wrong".encode()).decode()
    assert client.post("/mcp/token", headers={"Authorization": f"Basic {bad}"},
                       data={"grant_type": "client_credentials"}).status_code == 401

    # regenerate rotates the secret
    new = client.post(f"/api/mcp-keys/{key}/regenerate").json()
    assert new["secret"] != secret

    # terminate
    assert client.delete(f"/api/mcp-keys/{key}").status_code == 200
    assert client.get("/api/mcp-keys").json() == []


# --- public URL + relay ---------------------------------------------------

def test_public_url_status_default(client):
    r = client.get("/api/public-url")
    assert r.status_code == 200
    assert r.json()["provider"] == "none"


def test_relay_status_no_account(client):
    r = client.get("/api/relay/status")
    assert r.status_code == 200
    assert r.json() == {"has_account": False, "entitled": False}
