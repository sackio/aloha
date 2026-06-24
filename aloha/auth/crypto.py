"""
aloha/auth/crypto.py

Fernet-based symmetric encryption for credential storage.

Key derivation uses PBKDF2HMAC(SHA256) with a fixed salt ("aloha-v1")
and 100,000 iterations.  The machine secret is read from /etc/machine-id;
if that file is unavailable, a UUID is generated and persisted at
{data_dir}/.machine_id.

Public API:
    encrypt(plaintext: str) -> str
    decrypt(ciphertext: str) -> str
    load_or_create_key(keyfile: Path) -> bytes
"""

from __future__ import annotations

import base64
import os
import uuid
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_SALT = b"aloha-v1"
_ITERATIONS = 100_000
_DEFAULT_DATA_DIR = Path("/data/aloha")

# Module-level cached key (derived once per process from the default data_dir)
_default_key: Optional[bytes] = None


def _get_machine_secret(data_dir: Path = _DEFAULT_DATA_DIR) -> bytes:
    """
    Return a stable machine-specific secret as bytes.

    Priority:
    1. /etc/machine-id (standard on Linux systems)
    2. {data_dir}/.machine_id (fallback; created on first use)
    """
    machine_id_path = Path("/etc/machine-id")
    if machine_id_path.exists():
        secret = machine_id_path.read_text().strip()
        if secret:
            return secret.encode()

    # Fallback: use or create a local .machine_id file
    local_id_path = data_dir / ".machine_id"
    if local_id_path.exists():
        secret = local_id_path.read_text().strip()
        if secret:
            return secret.encode()

    # Generate and persist a new UUID
    data_dir.mkdir(parents=True, exist_ok=True)
    new_id = str(uuid.uuid4())
    local_id_path.write_text(new_id)
    local_id_path.chmod(0o600)
    return new_id.encode()


def _derive_key(secret: bytes) -> bytes:
    """Derive a 32-byte Fernet key from the given secret via PBKDF2HMAC."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=_ITERATIONS,
    )
    raw_key = kdf.derive(secret)
    return base64.urlsafe_b64encode(raw_key)


def _get_default_key() -> bytes:
    """Return (and cache) the default Fernet key derived from the machine secret."""
    global _default_key
    if _default_key is None:
        secret = _get_machine_secret(_DEFAULT_DATA_DIR)
        _default_key = _derive_key(secret)
    return _default_key


def load_or_create_key(keyfile: Path) -> bytes:
    """
    Load a Fernet key from keyfile, or derive and persist one on first use.

    The keyfile is stored at mode 0600.  Returns raw key bytes suitable
    for passing directly to encrypt()/decrypt() as the `key` parameter.
    """
    if keyfile.exists():
        return keyfile.read_bytes().strip()

    # Derive key from machine secret and persist it
    secret = _get_machine_secret(keyfile.parent)
    key = _derive_key(secret)
    keyfile.parent.mkdir(parents=True, exist_ok=True)
    keyfile.write_bytes(key)
    keyfile.chmod(0o600)
    return key


def encrypt(plaintext: str, key: Optional[bytes] = None) -> str:
    """
    Encrypt a plaintext string and return a Fernet token (URL-safe base64 string).

    Parameters
    ----------
    plaintext : str
        The secret to encrypt.
    key : bytes, optional
        A Fernet key (URL-safe base64, 32 bytes decoded).
        Defaults to the machine-derived key.
    """
    fernet_key = key if key is not None else _get_default_key()
    f = Fernet(fernet_key)
    token = f.encrypt(plaintext.encode())
    return token.decode()


def decrypt(ciphertext: str, key: Optional[bytes] = None) -> str:
    """
    Decrypt a Fernet token and return the plaintext string.

    Parameters
    ----------
    ciphertext : str
        A Fernet token previously returned by encrypt().
    key : bytes, optional
        A Fernet key (URL-safe base64, 32 bytes decoded).
        Defaults to the machine-derived key.

    Raises
    ------
    cryptography.fernet.InvalidToken
        If the token is malformed or was encrypted with a different key.
    """
    fernet_key = key if key is not None else _get_default_key()
    f = Fernet(fernet_key)
    return f.decrypt(ciphertext.encode()).decode()
