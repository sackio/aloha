"""
aloha/config.py

AlohaConfig — single source of truth for all runtime configuration.

Persistence:
  - Written to {data_dir}/config.json on save().
  - On load(), config.json is read first, then env vars overlay.
  - api_key and ha_token are NEVER written as plaintext; they are stored
    as Fernet-encrypted ciphertext in config.json under the keys
    `api_key_enc` and `ha_token_enc`.

Env var prefix: ALOHA_
Examples: ALOHA_AI_PROVIDER, ALOHA_MODEL, ALOHA_HA_URL, ALOHA_PORT
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aloha.auth.crypto import decrypt, encrypt


class AlohaConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ALOHA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AI provider
    ai_provider: Literal["anthropic", "openai", "gemini", "ollama", "openrouter", "groq", "custom"] = "anthropic"
    model: str = "auto"
    safety_mode: Literal["strict", "normal", "permissive"] = "normal"

    # Home Assistant connection
    ha_url: str = "http://localhost:8123"

    # Refresh interval for HA context (entities, automations, etc.)
    context_refresh_minutes: int = 5

    # Runtime mode
    mode: Literal["bundled", "standalone", "addon"] = "bundled"

    # Directory paths
    data_dir: Path = Path("/data/aloha")
    ha_config_dir: Path = Path("/data/homeassistant")

    # Server
    port: int = 7123

    # Provider-specific optional fields
    ollama_url: str = "http://localhost:11434"
    custom_base_url: str = ""

    # Setup wizard completion flag
    setup_complete: bool = False

    # ---------------------------------------------------------------------------
    # Encrypted credential storage
    # These fields hold ciphertext when loaded from disk; they are never exposed
    # directly. Use the api_key and ha_token properties instead.
    # ---------------------------------------------------------------------------
    _api_key_enc: Optional[str] = None   # private; not a pydantic field
    _ha_token_enc: Optional[str] = None  # private; not a pydantic field

    # ---------------------------------------------------------------------------
    # api_key property
    # ---------------------------------------------------------------------------
    @property
    def api_key(self) -> Optional[str]:
        """Return plaintext api_key by decrypting stored ciphertext."""
        if self._api_key_enc is None:
            return None
        return decrypt(self._api_key_enc, self._fernet_key())

    @api_key.setter
    def api_key(self, value: Optional[str]) -> None:
        """Encrypt and store api_key."""
        if value is None:
            self._api_key_enc = None
        else:
            self._api_key_enc = encrypt(value, self._fernet_key())

    # ---------------------------------------------------------------------------
    # ha_token property
    # ---------------------------------------------------------------------------
    @property
    def ha_token(self) -> Optional[str]:
        """Return plaintext ha_token by decrypting stored ciphertext."""
        if self._ha_token_enc is None:
            return None
        return decrypt(self._ha_token_enc, self._fernet_key())

    @ha_token.setter
    def ha_token(self, value: Optional[str]) -> None:
        """Encrypt and store ha_token."""
        if value is None:
            self._ha_token_enc = None
        else:
            self._ha_token_enc = encrypt(value, self._fernet_key())

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------
    def _fernet_key(self) -> bytes:
        """
        Derive a stable Fernet key from the data_dir path.
        The key file is stored at {data_dir}/.keyfile (mode 0600).
        Created on first use; never changes for the lifetime of the install.
        """
        from aloha.auth.crypto import load_or_create_key
        return load_or_create_key(self.data_dir / ".keyfile")

    # ---------------------------------------------------------------------------
    # Class methods
    # ---------------------------------------------------------------------------
    @classmethod
    def load(cls) -> "AlohaConfig":
        """
        Load config: start from defaults, overlay config.json, then env vars.
        Encrypted fields are loaded from config.json into private attributes.
        """
        # 1. Build from env vars + defaults
        instance = cls()

        # 2. Overlay from config.json if it exists
        config_path = instance.data_dir / "config.json"
        if config_path.exists():
            with config_path.open() as f:
                raw = json.load(f)

            # Extract encrypted credential blobs before pydantic sees them
            api_key_enc = raw.pop("api_key_enc", None)
            ha_token_enc = raw.pop("ha_token_enc", None)

            # Re-create with merged values (env vars still win)
            merged = {**raw, **{
                k: v for k, v in instance.model_dump().items()
                if os.environ.get(f"ALOHA_{k.upper()}")
            }}
            instance = cls(**{**raw, **{
                k[len("ALOHA_"):].lower(): v
                for k, v in os.environ.items()
                if k.startswith("ALOHA_")
            }})

            instance._api_key_enc = api_key_enc
            instance._ha_token_enc = ha_token_enc

        return instance

    def save(self) -> None:
        """
        Persist config to {data_dir}/config.json.
        Plaintext api_key and ha_token are NEVER written; only ciphertext blobs.
        """
        self.data_dir.mkdir(parents=True, exist_ok=True)
        config_path = self.data_dir / "config.json"

        data = self.model_dump(
            exclude={"api_key", "ha_token"},
            mode="json",
        )
        # Serialize Path objects
        data["data_dir"] = str(self.data_dir)
        data["ha_config_dir"] = str(self.ha_config_dir)

        # Write encrypted blobs
        if self._api_key_enc is not None:
            data["api_key_enc"] = self._api_key_enc
        if self._ha_token_enc is not None:
            data["ha_token_enc"] = self._ha_token_enc

        with config_path.open("w") as f:
            json.dump(data, f, indent=2)
        config_path.chmod(0o600)
