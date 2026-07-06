"""
aloha/mcp/auth.py

Access credentials for the box's MCP endpoint. Each credential is an OAuth-style
key + secret: the *key* (``amk_…``) is a public identifier used to manage the
credential; the *secret* (``ams_…``) is the bearer token an MCP client presents
in the ``Authorization: Bearer`` header. Only a hash of the secret is stored, so
the plaintext secret is shown exactly once — at mint / regenerate time.

Enforcement policy: the MCP endpoint requires a valid secret **iff at least one
key exists**. So a purely-local box with no keys stays open (backward compatible),
and the moment you mint a key — which you should before exposing a public URL —
every MCP request must authenticate.

Stored at ``{data_dir}/mcp_keys.json``.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path


def _path(data_dir: Path) -> Path:
    return Path(data_dir) / "mcp_keys.json"


def _hash(secret: str) -> str:
    # Secrets are 256-bit random tokens, so a plain SHA-256 is sufficient.
    return hashlib.sha256(secret.encode()).hexdigest()


def _load(data_dir: Path) -> list[dict]:
    try:
        return json.loads(_path(data_dir).read_text())
    except Exception:
        return []


def _save(data_dir: Path, keys: list[dict]) -> None:
    p = _path(data_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(keys, indent=2))
    try:
        p.chmod(0o600)
    except Exception:
        pass


def any_keys(data_dir: Path) -> bool:
    return len(_load(data_dir)) > 0


def list_keys(data_dir: Path) -> list[dict]:
    """Public view — never includes secrets."""
    return [
        {"id": k["id"], "name": k.get("name", ""), "created_at": k.get("created_at", ""),
         "secret_prefix": k.get("secret_prefix", "")}
        for k in _load(data_dir)
    ]


def verify(data_dir: Path, secret: str) -> str | None:
    """Return the key id whose secret matches, or None."""
    if not secret:
        return None
    h = _hash(secret)
    for k in _load(data_dir):
        if secrets.compare_digest(k.get("secret_hash", ""), h):
            return k["id"]
    return None


def mint(data_dir: Path, name: str = "", *, now: str = "") -> dict:
    """Create a credential. Returns {id, secret, name} — secret shown once."""
    key_id = "amk_" + secrets.token_hex(8)
    secret = "ams_" + secrets.token_urlsafe(32)
    keys = _load(data_dir)
    keys.append({
        "id": key_id,
        "name": name.strip()[:60] or "MCP key",
        "created_at": now,
        "secret_hash": _hash(secret),
        "secret_prefix": secret[:12],
    })
    _save(data_dir, keys)
    return {"id": key_id, "secret": secret, "name": name.strip()[:60] or "MCP key"}


def regenerate(data_dir: Path, key_id: str) -> dict | None:
    """Rotate a credential's secret (same id). Returns {id, secret} or None."""
    keys = _load(data_dir)
    for k in keys:
        if k["id"] == key_id:
            secret = "ams_" + secrets.token_urlsafe(32)
            k["secret_hash"] = _hash(secret)
            k["secret_prefix"] = secret[:12]
            _save(data_dir, keys)
            return {"id": key_id, "secret": secret}
    return None


def revoke(data_dir: Path, key_id: str) -> bool:
    keys = _load(data_dir)
    remaining = [k for k in keys if k["id"] != key_id]
    if len(remaining) == len(keys):
        return False
    _save(data_dir, remaining)
    return True
