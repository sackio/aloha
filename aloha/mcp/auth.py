"""
aloha/mcp/auth.py

OAuth-style client credentials for the box's MCP endpoint. Each credential is a
**key + secret** pair (client_id + client_secret):

  • key    (``amk_…``) — the client id, public, used to identify/manage the cred.
  • secret (``ams_…``) — the client secret, shown once, hashed at rest.

Both are required to authenticate. Clients present them either as HTTP Basic
(``Authorization: Basic base64(key:secret)``) or by exchanging them at the OAuth2
token endpoint (``POST /mcp/token``, grant_type=client_credentials) for a
short-lived Bearer access token.

Enforcement: the MCP endpoint requires valid credentials **iff at least one key
exists** — a purely-local box with no keys stays open (backward compatible), and
the moment you mint a key every MCP request must authenticate.

Stored at ``{data_dir}/mcp_keys.json`` (credentials) and
``{data_dir}/mcp_tokens.json`` (issued access tokens).
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from pathlib import Path

TOKEN_TTL = 3600  # access-token lifetime (seconds)


def _keys_path(data_dir: Path) -> Path:
    return Path(data_dir) / "mcp_keys.json"


def _tokens_path(data_dir: Path) -> Path:
    return Path(data_dir) / "mcp_tokens.json"


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _load(path: Path) -> list[dict]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def _save(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2))
    try:
        path.chmod(0o600)
    except Exception:
        pass


# --- credentials -----------------------------------------------------------

def any_keys(data_dir: Path) -> bool:
    return len(_load(_keys_path(data_dir))) > 0


def list_keys(data_dir: Path) -> list[dict]:
    """Public view — never includes secrets."""
    return [
        {"key": k["key"], "name": k.get("name", ""), "created_at": k.get("created_at", ""),
         "secret_prefix": k.get("secret_prefix", "")}
        for k in _load(_keys_path(data_dir))
    ]


def mint(data_dir: Path, name: str = "", *, now: str = "") -> dict:
    """Create a credential. Returns {key, secret, name} — secret shown once."""
    key = "amk_" + secrets.token_hex(8)
    secret = "ams_" + secrets.token_urlsafe(32)
    rows = _load(_keys_path(data_dir))
    rows.append({
        "key": key,
        "name": name.strip()[:60] or "MCP client",
        "created_at": now,
        "secret_hash": _hash(secret),
        "secret_prefix": secret[:12],
    })
    _save(_keys_path(data_dir), rows)
    return {"key": key, "secret": secret, "name": name.strip()[:60] or "MCP client"}


def regenerate(data_dir: Path, key: str) -> dict | None:
    """Rotate a credential's secret (same key). Returns {key, secret} or None."""
    rows = _load(_keys_path(data_dir))
    for k in rows:
        if k["key"] == key:
            secret = "ams_" + secrets.token_urlsafe(32)
            k["secret_hash"] = _hash(secret)
            k["secret_prefix"] = secret[:12]
            _save(_keys_path(data_dir), rows)
            # Revoking the secret also invalidates any access tokens it minted.
            _prune_tokens(data_dir, drop_key=key)
            return {"key": key, "secret": secret}
    return None


def revoke(data_dir: Path, key: str) -> bool:
    rows = _load(_keys_path(data_dir))
    remaining = [k for k in rows if k["key"] != key]
    if len(remaining) == len(rows):
        return False
    _save(_keys_path(data_dir), remaining)
    _prune_tokens(data_dir, drop_key=key)
    return True


def verify_pair(data_dir: Path, key: str, secret: str) -> bool:
    """True iff (key, secret) is a valid credential pair."""
    if not key or not secret:
        return False
    h = _hash(secret)
    for k in _load(_keys_path(data_dir)):
        if k["key"] == key and secrets.compare_digest(k.get("secret_hash", ""), h):
            return True
    return False


# --- OAuth2 access tokens --------------------------------------------------

def _prune_tokens(data_dir: Path, *, drop_key: str | None = None) -> list[dict]:
    now = time.time()
    rows = [t for t in _load(_tokens_path(data_dir))
            if t.get("expires_at", 0) > now and (drop_key is None or t.get("key") != drop_key)]
    _save(_tokens_path(data_dir), rows)
    return rows


def issue_token(data_dir: Path, key: str) -> dict:
    """Mint a short-lived Bearer access token for a (already-verified) key."""
    token = "amt_" + secrets.token_urlsafe(32)
    rows = _prune_tokens(data_dir)
    rows.append({"token_hash": _hash(token), "key": key, "expires_at": time.time() + TOKEN_TTL})
    _save(_tokens_path(data_dir), rows)
    return {"access_token": token, "token_type": "Bearer", "expires_in": TOKEN_TTL}


def verify_token(data_dir: Path, token: str) -> bool:
    if not token:
        return False
    h = _hash(token)
    now = time.time()
    for t in _load(_tokens_path(data_dir)):
        if secrets.compare_digest(t.get("token_hash", ""), h) and t.get("expires_at", 0) > now:
            return True
    return False
