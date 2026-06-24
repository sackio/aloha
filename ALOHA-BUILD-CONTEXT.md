# Aloha Build Context

> **This document is the authoritative contract for all build agents.** Every section below specifies exact types, field names, API shapes, and file paths. Implement against these specifications exactly — do not invent alternatives.

---

## 1. What Aloha Is

Aloha is a single Docker image (`ghcr.io/aloha-ha/aloha:latest`) that bundles Home Assistant and an AI-powered agent into one deployable unit.

### Runtime architecture

- **Home Assistant** runs on port `8123` (internal).
- **Aloha Agent** (FastAPI + React frontend) runs on port `7123`.
- Both processes are managed by **s6-overlay v3** inside the container.
- HA and Aloha communicate over `localhost`; Aloha always reaches HA at `http://localhost:8123`.
- A single Docker volume is mounted at `/data`:
  - `/data/homeassistant` — HA configuration directory
  - `/data/aloha` — Aloha configuration, encrypted credentials, session store, diff store

### Env-var modes

| Variable | Value | Behavior |
|---|---|---|
| `ALOHA_MODE` | `standalone` | Skips starting the internal HA; user brings their own HA instance |
| `ALOHA_MODE` | *(unset / `bundled`)* | Starts both HA and Aloha under s6 |

### HAOS add-on mode

Aloha is also distributed as a Home Assistant OS add-on. In this mode only the Aloha Agent process runs; HA is provided by the Supervisor. The add-on connects to HA using the Supervisor token and URL (`http://supervisor/core`).

---

## 2. File Tree

Every file that must be written, grouped by module. Build agents should produce exactly this tree.

```
aloha/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── README.md
│
├── rootfs/                          # s6-overlay additions (copied into image)
│   └── etc/
│       └── s6-overlay/
│           └── s6-rc.d/
│               ├── homeassistant/
│               │   ├── type          # "longrun"
│               │   ├── run           # exec script
│               │   └── finish        # cleanup script
│               ├── aloha/
│               │   ├── type          # "longrun"
│               │   ├── run           # exec script
│               │   ├── finish        # cleanup script
│               │   └── dependencies.d/
│               │       └── homeassistant   # empty file — aloha waits for HA
│               └── user/
│                   └── contents.d/
│                       ├── homeassistant   # empty file — activate service
│                       └── aloha           # empty file — activate service
│
├── aloha/                           # Python package root
│   ├── __init__.py
│   ├── main.py                      # FastAPI app factory + lifespan
│   ├── config.py                    # AlohaConfig (pydantic-settings)
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── types.py                 # Pydantic domain types + SSE events
│   │   ├── runner.py                # Chat orchestration loop
│   │   ├── context.py               # HA context builder
│   │   ├── diff.py                  # Config diff manager
│   │   └── sessions.py              # Session store
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   └── crypto.py                # Fernet key derivation + encrypt/decrypt
│   │
│   ├── backends/
│   │   ├── __init__.py
│   │   ├── base.py                  # Abstract BaseBackend
│   │   ├── anthropic.py             # Claude backend
│   │   ├── openai.py                # OpenAI-compatible backend
│   │   ├── gemini.py                # Google Gemini backend
│   │   └── ollama.py                # Ollama backend
│   │
│   ├── ha/
│   │   ├── __init__.py
│   │   └── client.py                # HAClient + singleton helpers
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py              # Tool registry + dispatcher
│   │   ├── entities.py              # Entity read/write tools
│   │   ├── automations.py           # Automation CRUD tools
│   │   ├── config.py                # Config file read/write/validate tools
│   │   ├── system.py                # System info / health tools
│   │   ├── dashboards.py            # Dashboard (Lovelace) tools
│   │   └── hacs.py                  # HACS integration tools
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py                # GET /health
│   │   ├── settings.py              # GET|POST /api/settings
│   │   ├── context.py               # GET /api/context, POST /api/context/refresh
│   │   ├── sessions.py              # Session CRUD endpoints
│   │   ├── chat.py                  # POST /api/chat (SSE)
│   │   ├── approve.py               # POST /api/approve
│   │   ├── providers.py             # GET /api/providers
│   │   └── auth.py                  # POST /api/auth/test, GET /auth/*/start|callback
│   │
│   └── frontend/                    # Built React app (served as static files)
│       └── dist/                    # Output of `npm run build`
│
└── frontend/                        # React source
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── store/
        │   ├── settingsStore.ts
        │   └── chatStore.ts
        ├── components/
        │   ├── Wizard/
        │   │   ├── Wizard.tsx
        │   │   └── steps/
        │   │       ├── WelcomeStep.tsx
        │   │       ├── ProviderStep.tsx
        │   │       ├── ModelStep.tsx
        │   │       ├── HATokenStep.tsx
        │   │       └── DoneStep.tsx
        │   ├── Chat/
        │   │   ├── ChatPane.tsx
        │   │   ├── MessageList.tsx
        │   │   ├── MessageBubble.tsx
        │   │   ├── ToolCallBubble.tsx
        │   │   ├── DiffReviewCard.tsx
        │   │   └── InputBar.tsx
        │   └── Settings/
        │       ├── SettingsPanel.tsx
        │       └── ProviderForm.tsx
        └── lib/
            ├── api.ts               # Typed fetch wrappers
            └── sse.ts               # SSE stream consumer
```

---

## 3. Python Types (`aloha/agent/types.py`)

```python
"""
aloha/agent/types.py

All domain types and SSE event models used across the Aloha agent.
Import from here; do not duplicate these definitions elsewhere.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Safety levels
# ---------------------------------------------------------------------------

class SafetyLevel(str, Enum):
    """
    Severity classification for each MCP tool.

    READ          — read-only; never modifies state; always auto-approved.
    WRITE_SOFT    — changes runtime state only (e.g. turn on a light);
                    reversible; auto-approved in normal safety mode.
    WRITE_CONFIG  — modifies persistent configuration files (YAML, JSON);
                    requires user approval or SAFETY_MODE=permissive.
    DESTRUCTIVE   — irreversible or high-risk (e.g. delete automation,
                    restart HA); always requires explicit user approval.
    """

    READ = "read"
    WRITE_SOFT = "write_soft"
    WRITE_CONFIG = "write_config"
    DESTRUCTIVE = "destructive"


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

class ToolDef(BaseModel):
    """
    Descriptor for a single MCP-style tool exposed to the AI backend.

    `parameters` is a JSON Schema object dict, e.g.:
        {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "..."}
            },
            "required": ["entity_id"]
        }
    """

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    safety: SafetyLevel = SafetyLevel.READ
    returns: str = "str"   # human-readable description of the return type


# ---------------------------------------------------------------------------
# Chat message
# ---------------------------------------------------------------------------

class Message(BaseModel):
    """
    A single turn in the conversation history.

    role       — "user" | "assistant" | "tool"
    content    — the text body of the message (may be empty string for
                 assistant turns that only contain tool calls)
    tool_call_id — present only when role == "tool"; links result to call
    tool_name    — present only when role == "tool"; used by some backends
    """

    role: Literal["user", "assistant", "tool"]
    content: str
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None


# ---------------------------------------------------------------------------
# SSE event models
# ---------------------------------------------------------------------------
# Every event emitted over the /api/chat SSE stream must be one of these.
# The frontend discriminates on the `type` field.

class ContentEvent(BaseModel):
    """Streamed text delta from the AI."""
    type: Literal["content"] = "content"
    delta: str


class ToolCallEvent(BaseModel):
    """
    The AI is invoking a tool.
    Emitted before the tool runs so the frontend can show a spinner.
    """
    type: Literal["tool_call"] = "tool_call"
    id: str           # unique call id (echoed back in ToolResultEvent)
    name: str         # tool name
    args: dict[str, Any]


class ToolResultEvent(BaseModel):
    """Result of a tool call (or error if the tool raised)."""
    type: Literal["tool_result"] = "tool_result"
    id: str           # matches ToolCallEvent.id
    name: str
    result: str       # JSON-serialised or plain-text result
    error: bool = False


class DiffEvent(BaseModel):
    """
    The AI proposes a file change that requires human approval.

    id      — unique diff id; used with POST /api/approve
    path    — absolute path of the file inside the container (e.g.
              /data/homeassistant/automations/lights.yaml)
    before  — current file content (empty string if file does not exist)
    after   — proposed new content
    content — same as `after`; included as a convenience alias so the
              frontend can write the file directly without re-deriving it
    """
    type: Literal["diff"] = "diff"
    id: str
    path: str
    before: str
    after: str
    content: str      # alias for after; value must equal after


class DoneEvent(BaseModel):
    """Signals end of stream. usage contains token counts if available."""
    type: Literal["done"] = "done"
    usage: Optional[dict[str, int]] = None


class ErrorEvent(BaseModel):
    """Fatal error during stream processing."""
    type: Literal["error"] = "error"
    message: str
    code: Optional[str] = None
```

---

## 4. Config (`aloha/config.py`)

```python
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
    ai_provider: Literal["anthropic", "openai", "gemini", "ollama", "custom"] = "anthropic"
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
```

---

## 5. BaseBackend (`aloha/backends/base.py`)

```python
"""
aloha/backends/base.py

Abstract base class that all AI provider backends must implement.
Each backend translates the internal message/tool format into provider-
specific API calls and yields a normalized stream of dicts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from aloha.agent.types import ToolDef


class BaseBackend(ABC):
    """
    Abstract AI backend.

    Subclasses: AnthropicBackend, OpenAIBackend, GeminiBackend, OllamaBackend.

    Yielded dict shapes from chat_stream():

        Text delta:
            {"type": "content", "delta": str}

        Tool call (complete, not streamed incrementally):
            {"type": "tool_call", "id": str, "name": str, "args": dict}

        Error (non-fatal; stream may continue):
            {"type": "error", "message": str}
    """

    def __init__(
        self,
        api_key: str,
        model: str = "auto",
        base_url: str = "",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    # ---------------------------------------------------------------------------
    # Abstract methods — every subclass must implement these
    # ---------------------------------------------------------------------------

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        system: str,
        tools: list[ToolDef],
    ) -> AsyncIterator[dict]:
        """
        Stream a chat completion.

        Parameters
        ----------
        messages : list[dict]
            Conversation history in the OpenAI messages format:
              [{"role": "user"|"assistant"|"tool", "content": str, ...}]
            Tool result messages carry additional keys:
              {"role": "tool", "tool_call_id": str, "name": str, "content": str}
        system : str
            System prompt.  Passed separately because some APIs (Anthropic)
            treat system as a top-level parameter, not a message.
        tools : list[ToolDef]
            Tool definitions to advertise to the model.

        Yields
        ------
        dict
            See class docstring for yielded shapes.
        """
        ...

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """
        Validate credentials and connectivity.

        Returns
        -------
        (True, model_name)   on success
        (False, error_msg)   on failure
        """
        ...

    # ---------------------------------------------------------------------------
    # Abstract properties
    # ---------------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name, e.g. 'Anthropic'."""
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model ID to use when model='auto'."""
        ...

    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        """
        Ordered list of supported model IDs, best-first.
        Used to populate the model picker in the setup wizard.
        """
        ...
```

---

## 6. HAClient (`aloha/ha/client.py`)

```python
"""
aloha/ha/client.py

Async HTTP client for the Home Assistant REST API.

Singleton usage:
    from aloha.ha.client import get_ha_client
    client = get_ha_client()

Initialisation (call once at startup):
    from aloha.ha.client import init_ha_client
    init_ha_client(ha_url="http://localhost:8123", ha_token="Bearer ...")
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Optional

import httpx


class HAClient:
    """
    Async wrapper around the Home Assistant REST API.

    All methods raise httpx.HTTPStatusError on 4xx/5xx responses.
    The caller is responsible for handling those errors.
    """

    def __init__(self, base_url: str, token: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    # ---------------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._headers,
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ---------------------------------------------------------------------------
    # Health / discovery
    # ---------------------------------------------------------------------------

    async def ping(self) -> bool:
        """Return True if HA is reachable and the token is valid."""
        try:
            c = await self._get_client()
            r = await c.get("/api/")
            r.raise_for_status()
            return True
        except Exception:
            return False

    async def get_version(self) -> str:
        """Return the HA version string."""
        c = await self._get_client()
        r = await c.get("/api/")
        r.raise_for_status()
        return r.json().get("version", "unknown")

    async def get_system_health(self) -> dict[str, Any]:
        """Return the /api/system_health payload."""
        c = await self._get_client()
        r = await c.get("/api/system_health")
        r.raise_for_status()
        return r.json()

    # ---------------------------------------------------------------------------
    # States
    # ---------------------------------------------------------------------------

    async def get_states(self) -> list[dict[str, Any]]:
        """Return all entity states."""
        c = await self._get_client()
        r = await c.get("/api/states")
        r.raise_for_status()
        return r.json()

    async def get_state(self, entity_id: str) -> dict[str, Any]:
        """Return state for a single entity."""
        c = await self._get_client()
        r = await c.get(f"/api/states/{entity_id}")
        r.raise_for_status()
        return r.json()

    async def subscribe_state_changes(
        self,
        entity_ids: Optional[list[str]] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Async generator that yields state-changed events via WebSocket.
        entity_ids=None means all entities.
        Uses the HA WebSocket API at ws://{host}/api/websocket.
        """
        # Implementation uses websockets library; yields event dicts.
        raise NotImplementedError

    # ---------------------------------------------------------------------------
    # Services
    # ---------------------------------------------------------------------------

    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: Optional[dict[str, Any]] = None,
        target: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Call a HA service.

        Returns the list of affected entity state dicts.
        """
        payload: dict[str, Any] = {}
        if service_data:
            payload.update(service_data)
        if target:
            payload["target"] = target

        c = await self._get_client()
        r = await c.post(f"/api/services/{domain}/{service}", json=payload)
        r.raise_for_status()
        return r.json()

    # ---------------------------------------------------------------------------
    # Configuration
    # ---------------------------------------------------------------------------

    async def get_config(self) -> dict[str, Any]:
        """Return the /api/config payload (location, unit system, etc.)."""
        c = await self._get_client()
        r = await c.get("/api/config")
        r.raise_for_status()
        return r.json()

    async def check_config(self) -> dict[str, Any]:
        """
        Trigger a HA config check.
        Returns {"result": "valid"} or {"result": "invalid", "errors": str}.
        """
        c = await self._get_client()
        r = await c.post("/api/config/core/check_config")
        r.raise_for_status()
        return r.json()

    async def list_config_entries(self) -> list[dict[str, Any]]:
        """Return all config entries (integrations)."""
        c = await self._get_client()
        r = await c.get("/api/config/config_entries/entry")
        r.raise_for_status()
        return r.json()

    async def reload_config(self, domain: Optional[str] = None) -> None:
        """
        Reload HA configuration.
        domain=None reloads core; otherwise reloads that integration.
        """
        c = await self._get_client()
        if domain:
            r = await c.post(f"/api/services/{domain}/reload")
        else:
            r = await c.post("/api/config/core/reload")
        r.raise_for_status()

    async def restart(self) -> None:
        """Restart Home Assistant (DESTRUCTIVE)."""
        c = await self._get_client()
        r = await c.post("/api/services/homeassistant/restart")
        r.raise_for_status()

    # ---------------------------------------------------------------------------
    # History / logs
    # ---------------------------------------------------------------------------

    async def get_history(
        self,
        entity_ids: Optional[list[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> list[list[dict[str, Any]]]:
        """Return entity history. Times are ISO8601 strings."""
        params: dict[str, Any] = {}
        if entity_ids:
            params["filter_entity_id"] = ",".join(entity_ids)
        if end_time:
            params["end_time"] = end_time

        path = f"/api/history/period"
        if start_time:
            path += f"/{start_time}"

        c = await self._get_client()
        r = await c.get(path, params=params)
        r.raise_for_status()
        return r.json()

    async def get_logbook(
        self,
        entity_ids: Optional[list[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Return logbook entries."""
        params: dict[str, Any] = {}
        if entity_ids:
            params["entity_id"] = ",".join(entity_ids)
        if end_time:
            params["end_time"] = end_time

        path = "/api/logbook"
        if start_time:
            path += f"/{start_time}"

        c = await self._get_client()
        r = await c.get(path, params=params)
        r.raise_for_status()
        return r.json()

    async def get_error_log(self) -> str:
        """Return the HA error log as a plain-text string."""
        c = await self._get_client()
        r = await c.get("/api/error_log")
        r.raise_for_status()
        return r.text

    # ---------------------------------------------------------------------------
    # Templates
    # ---------------------------------------------------------------------------

    async def get_template(self, template: str) -> str:
        """Render a Jinja2 template string and return the result."""
        c = await self._get_client()
        r = await c.post("/api/template", json={"template": template})
        r.raise_for_status()
        return r.text

    # ---------------------------------------------------------------------------
    # Long-lived access tokens
    # ---------------------------------------------------------------------------

    async def create_long_lived_token(
        self,
        client_name: str,
        lifespan_days: int = 3650,
    ) -> str:
        """
        Create a long-lived access token for the current user.
        Returns the token string.
        Uses the HA WebSocket API (REST endpoint not available for this).
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_client: Optional[HAClient] = None


def init_ha_client(ha_url: str, ha_token: str) -> HAClient:
    """
    Initialise (or replace) the module-level singleton.
    Call once at application startup from the FastAPI lifespan handler.
    """
    global _client
    _client = HAClient(base_url=ha_url, token=ha_token)
    return _client


def get_ha_client() -> HAClient:
    """
    Return the module-level singleton.
    Raises RuntimeError if init_ha_client() has not been called.
    """
    if _client is None:
        raise RuntimeError(
            "HAClient not initialised. Call init_ha_client() at startup."
        )
    return _client
```

---

## 7. Frontend-Backend API Contract

All endpoints are served by the FastAPI app at `http://localhost:7123`.

### 7.1 Health

```
GET /health
```

**Response 200:**
```json
{
  "status": "ok",
  "ha_connected": true,
  "ha_version": "2024.6.0",
  "setup_complete": true,
  "provider": "anthropic"
}
```

### 7.2 Settings

```
GET /api/settings
```

**Response 200:**
```json
{
  "ai_provider": "anthropic",
  "model": "claude-opus-4-5",
  "safety_mode": "normal",
  "ha_url": "http://localhost:8123",
  "context_refresh_minutes": 5,
  "mode": "bundled",
  "port": 7123,
  "ollama_url": "http://localhost:11434",
  "custom_base_url": "",
  "setup_complete": true,
  "has_api_key": true,
  "has_ha_token": true
}
```

Note: `api_key` and `ha_token` are **never** included in GET responses. The `has_api_key` / `has_ha_token` booleans indicate whether a credential is stored.

```
POST /api/settings
Content-Type: application/json
```

**Request body** (all fields optional; only supplied fields are updated):
```json
{
  "ai_provider": "anthropic",
  "model": "claude-opus-4-5",
  "safety_mode": "normal",
  "ha_url": "http://localhost:8123",
  "context_refresh_minutes": 5,
  "api_key": "sk-ant-...",
  "ha_token": "eyJ...",
  "ollama_url": "http://localhost:11434",
  "custom_base_url": "",
  "setup_complete": true
}
```

**Response 200:**
```json
{"ok": true}
```

### 7.3 Context

```
GET /api/context
```

**Response 200:**
```json
{
  "summary": "...",
  "entity_count": 142,
  "automation_count": 17,
  "last_refreshed": "2026-06-23T10:00:00Z"
}
```

```
POST /api/context/refresh
```

**Response 200:**
```json
{"ok": true, "last_refreshed": "2026-06-23T10:05:00Z"}
```

### 7.4 Sessions

```
GET /api/sessions
```

**Response 200:**
```json
[
  {
    "id": "ses_abc123",
    "title": "Turn off kitchen lights",
    "created_at": "2026-06-23T09:00:00Z",
    "updated_at": "2026-06-23T09:05:00Z",
    "message_count": 4
  }
]
```

```
POST /api/sessions
Content-Type: application/json
{"title": "New session"}
```

**Response 201:**
```json
{"id": "ses_xyz789", "title": "New session", "created_at": "...", "updated_at": "...", "message_count": 0}
```

```
GET /api/sessions/{id}
```

**Response 200:**
```json
{
  "id": "ses_abc123",
  "title": "Turn off kitchen lights",
  "created_at": "...",
  "updated_at": "...",
  "messages": [
    {"role": "user", "content": "Turn off all kitchen lights"}
  ]
}
```

```
DELETE /api/sessions/{id}
```

**Response 204** (no body)

### 7.5 Chat (SSE stream)

```
POST /api/chat
Content-Type: application/json

{
  "session_id": "ses_abc123",
  "message": "Turn off all the lights in the kitchen"
}
```

**Response: `text/event-stream`**

Each SSE event is formatted as:
```
data: <JSON>\n\n
```

Event JSON shapes (discriminated by `type`):

```json
{"type": "content", "delta": "Sure, I'll turn off..."}
{"type": "tool_call", "id": "tc_001", "name": "call_service", "args": {"domain": "light", "service": "turn_off", "target": {"area_id": "kitchen"}}}
{"type": "tool_result", "id": "tc_001", "name": "call_service", "result": "[{\"entity_id\": \"light.kitchen_main\", ...}]", "error": false}
{"type": "diff", "id": "diff_abc", "path": "/data/homeassistant/automations/lights.yaml", "before": "- id: old...", "after": "- id: new...", "content": "- id: new..."}
{"type": "done", "usage": {"input_tokens": 1200, "output_tokens": 340}}
{"type": "error", "message": "HA connection lost", "code": "HA_UNREACHABLE"}
```

### 7.6 Approve

```
POST /api/approve
Content-Type: application/json

{
  "diff_id": "diff_abc",
  "action": "apply"
}
```

`action` must be `"apply"` or `"reject"`.

**Response 200:**
```json
{"ok": true, "diff_id": "diff_abc", "action": "apply"}
```

**Response 404** if diff_id not found or already resolved:
```json
{"detail": "Diff not found or already resolved"}
```

### 7.7 Providers

```
GET /api/providers
```

**Response 200:**
```json
[
  {
    "id": "anthropic",
    "name": "Anthropic",
    "requires_api_key": true,
    "models": ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-3-5"],
    "default_model": "claude-opus-4-5"
  },
  {
    "id": "openai",
    "name": "OpenAI",
    "requires_api_key": true,
    "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    "default_model": "gpt-4o"
  },
  {
    "id": "gemini",
    "name": "Google Gemini",
    "requires_api_key": true,
    "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    "default_model": "gemini-2.0-flash"
  },
  {
    "id": "ollama",
    "name": "Ollama (local)",
    "requires_api_key": false,
    "models": [],
    "default_model": ""
  },
  {
    "id": "custom",
    "name": "Custom (OpenAI-compatible)",
    "requires_api_key": false,
    "models": [],
    "default_model": ""
  }
]
```

### 7.8 Auth Test

```
POST /api/auth/test
Content-Type: application/json

{
  "provider": "anthropic",
  "api_key": "sk-ant-...",
  "model": "claude-opus-4-5"
}
```

**Response 200 (success):**
```json
{"ok": true, "model": "claude-opus-4-5"}
```

**Response 200 (failure):**
```json
{"ok": false, "error": "Invalid API key"}
```

### 7.9 OAuth (future / provider-specific)

```
GET /auth/{provider}/start
```

Redirects to the provider's OAuth consent page.

```
GET /auth/{provider}/callback?code=...&state=...
```

Handles OAuth callback, exchanges code for token, saves to config, redirects to `/`.

---

## 8. React Store Shapes

### 8.1 Settings Store (`src/store/settingsStore.ts`)

```typescript
// Zustand store for application settings

interface SettingsData {
  ai_provider: "anthropic" | "openai" | "gemini" | "ollama" | "custom";
  model: string;
  safety_mode: "strict" | "normal" | "permissive";
  ha_url: string;
  context_refresh_minutes: number;
  mode: "bundled" | "standalone" | "addon";
  port: number;
  ollama_url: string;
  custom_base_url: string;
  setup_complete: boolean;
  has_api_key: boolean;
  has_ha_token: boolean;
}

interface SettingsState {
  settings: SettingsData | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchSettings: () => Promise<void>;
  updateSettings: (patch: Partial<SettingsData> & {
    api_key?: string;
    ha_token?: string;
  }) => Promise<void>;
  setSetupComplete: (complete: boolean) => Promise<void>;
}
```

### 8.2 Chat Store (`src/store/chatStore.ts`)

```typescript
// Zustand store for chat sessions and streaming

interface ChatMessage {
  id: string;                  // client-generated uuid
  role: "user" | "assistant" | "tool";
  content: string;             // accumulated text for assistant messages
  tool_call?: {
    id: string;
    name: string;
    args: Record<string, unknown>;
    result?: string;
    error?: boolean;
  };
  pending_diff?: PendingDiff;
  created_at: string;          // ISO8601
}

interface PendingDiff {
  id: string;                  // diff_id from DiffEvent
  path: string;
  before: string;
  after: string;
  content: string;
  status: "pending" | "applied" | "rejected";
}

interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface ChatState {
  sessions: Session[];
  activeSessionId: string | null;
  messages: ChatMessage[];     // messages for the active session
  streaming: boolean;
  error: string | null;

  // Actions
  fetchSessions: () => Promise<void>;
  createSession: (title?: string) => Promise<string>;    // returns new session id
  selectSession: (id: string) => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;       // triggers SSE stream
  approveDiff: (diffId: string, action: "apply" | "reject") => Promise<void>;
  cancelStream: () => void;
}
```

### 8.3 Provider Config / Wizard (`src/store/settingsStore.ts` — wizard slice)

```typescript
interface ProviderConfig {
  id: "anthropic" | "openai" | "gemini" | "ollama" | "custom";
  name: string;
  requires_api_key: boolean;
  models: string[];
  default_model: string;
}

type WizardStep =
  | "welcome"       // Landing page
  | "provider"      // Choose AI provider
  | "model"         // Choose model (if applicable)
  | "api_key"       // Enter API key (if required)
  | "ha_token"      // Enter HA long-lived token
  | "test"          // Test connectivity
  | "done";         // Setup complete

interface WizardState {
  step: WizardStep;
  providers: ProviderConfig[];
  selectedProvider: ProviderConfig | null;
  selectedModel: string;
  apiKey: string;
  haToken: string;
  testResult: { ok: boolean; error?: string } | null;
  testing: boolean;

  // Actions
  fetchProviders: () => Promise<void>;
  setStep: (step: WizardStep) => void;
  selectProvider: (id: string) => void;
  selectModel: (model: string) => void;
  setApiKey: (key: string) => void;
  setHaToken: (token: string) => void;
  testConnection: () => Promise<void>;
  completeSetup: () => Promise<void>;
}
```

---

## 9. MCP Tool List

All tools are registered in `aloha/tools/registry.py` and dispatched from there. Each tool corresponds to a function in the module indicated.

### 9.1 Entity Tools (`aloha/tools/entities.py`)

| Tool Name | SafetyLevel | Description |
|---|---|---|
| `get_entity_state` | READ | Get the current state of a single entity |
| `get_all_states` | READ | Get states for all entities |
| `get_entities_by_domain` | READ | Get all entities in a domain (e.g. `light`) |
| `get_entities_by_area` | READ | Get all entities in a named area |
| `search_entities` | READ | Full-text search entities by id or name |
| `get_entity_history` | READ | Get state history for an entity over a time range |
| `get_entity_logbook` | READ | Get logbook entries for an entity |
| `turn_on` | WRITE_SOFT | Turn on a light, switch, or other entity |
| `turn_off` | WRITE_SOFT | Turn off a light, switch, or other entity |
| `toggle` | WRITE_SOFT | Toggle a light or switch |
| `set_light_brightness` | WRITE_SOFT | Set light brightness (0–255) |
| `set_light_color` | WRITE_SOFT | Set light RGB color |
| `set_light_color_temp` | WRITE_SOFT | Set light color temperature in mireds |
| `set_cover_position` | WRITE_SOFT | Set cover/blind position (0–100%) |
| `set_climate_temperature` | WRITE_SOFT | Set thermostat target temperature |
| `set_climate_hvac_mode` | WRITE_SOFT | Set thermostat HVAC mode |
| `set_fan_speed` | WRITE_SOFT | Set fan speed percentage |
| `lock_entity` | WRITE_SOFT | Lock a lock entity |
| `unlock_entity` | WRITE_SOFT | Unlock a lock entity |
| `run_script` | WRITE_SOFT | Execute a HA script |
| `call_service_raw` | WRITE_SOFT | Call any HA service with arbitrary data |

### 9.2 Automation Tools (`aloha/tools/automations.py`)

| Tool Name | SafetyLevel | Description |
|---|---|---|
| `list_automations` | READ | List all automations with id, alias, state |
| `get_automation` | READ | Get full YAML definition of a single automation |
| `trigger_automation` | WRITE_SOFT | Manually trigger an automation |
| `enable_automation` | WRITE_SOFT | Enable a disabled automation |
| `disable_automation` | WRITE_SOFT | Disable an automation |
| `create_automation` | WRITE_CONFIG | Create a new automation (writes YAML, emits DiffEvent) |
| `update_automation` | WRITE_CONFIG | Update an existing automation (writes YAML, emits DiffEvent) |
| `delete_automation` | DESTRUCTIVE | Delete an automation permanently |
| `reload_automations` | WRITE_SOFT | Call `automation.reload` service |
| `validate_automation_yaml` | READ | Validate automation YAML syntax without saving |

### 9.3 Config Tools (`aloha/tools/config.py`)

| Tool Name | SafetyLevel | Description |
|---|---|---|
| `read_config_file` | READ | Read a file from the HA config directory |
| `list_config_files` | READ | List files in the HA config directory (optionally filtered by glob) |
| `write_config_file` | WRITE_CONFIG | Write/overwrite a file in the HA config directory (emits DiffEvent) |
| `append_config_file` | WRITE_CONFIG | Append content to a config file (emits DiffEvent) |
| `delete_config_file` | DESTRUCTIVE | Delete a file from the HA config directory |
| `check_config` | READ | Run HA config check and return result |
| `get_config_entry_list` | READ | List all config entries (integrations) |
| `reload_config_entry` | WRITE_SOFT | Reload a specific integration config entry |
| `get_ha_config` | READ | Get HA core config (location, units, etc.) |
| `render_template` | READ | Render a Jinja2 template using HA's template engine |

### 9.4 System Tools (`aloha/tools/system.py`)

| Tool Name | SafetyLevel | Description |
|---|---|---|
| `get_system_health` | READ | Get HA system health report |
| `get_ha_version` | READ | Get current HA version |
| `get_error_log` | READ | Retrieve the HA error log |
| `get_logbook` | READ | Get general logbook entries (not entity-specific) |
| `list_integrations` | READ | List all loaded integrations |
| `list_devices` | READ | List all devices |
| `list_areas` | READ | List all areas |
| `list_floors` | READ | List all floors |
| `get_device_info` | READ | Get detailed info for a specific device |
| `restart_ha` | DESTRUCTIVE | Restart Home Assistant |
| `reload_core_config` | WRITE_CONFIG | Reload HA core configuration |
| `reload_all_yaml` | WRITE_CONFIG | Reload all YAML-based domains |
| `create_persistent_notification` | WRITE_SOFT | Create a persistent notification in HA UI |
| `dismiss_persistent_notification` | WRITE_SOFT | Dismiss a persistent notification |
| `send_notification` | WRITE_SOFT | Send a notification to a mobile app or notify service |
| `fire_event` | WRITE_SOFT | Fire a custom HA event |

### 9.5 Dashboard Tools (`aloha/tools/dashboards.py`)

| Tool Name | SafetyLevel | Description |
|---|---|---|
| `list_dashboards` | READ | List all Lovelace dashboards |
| `get_dashboard` | READ | Get full YAML/JSON config for a dashboard |
| `get_dashboard_view` | READ | Get a single view from a dashboard |
| `create_dashboard` | WRITE_CONFIG | Create a new Lovelace dashboard (emits DiffEvent) |
| `update_dashboard` | WRITE_CONFIG | Update a dashboard's configuration (emits DiffEvent) |
| `delete_dashboard` | DESTRUCTIVE | Delete a dashboard |
| `add_card_to_view` | WRITE_CONFIG | Add a card to a dashboard view (emits DiffEvent) |
| `update_card` | WRITE_CONFIG | Update an existing card (emits DiffEvent) |
| `remove_card` | DESTRUCTIVE | Remove a card from a view |

### 9.6 HACS Tools (`aloha/tools/hacs.py`)

| Tool Name | SafetyLevel | Description |
|---|---|---|
| `hacs_is_installed` | READ | Check if HACS is installed and accessible |
| `hacs_list_installed` | READ | List all installed HACS repositories |
| `hacs_list_available` | READ | Search available HACS repositories by category and query |
| `hacs_get_repository_info` | READ | Get details for a specific HACS repository |
| `hacs_install_repository` | DESTRUCTIVE | Install a HACS repository (triggers HA restart if needed) |
| `hacs_uninstall_repository` | DESTRUCTIVE | Uninstall a HACS repository |
| `hacs_update_repository` | WRITE_CONFIG | Update a HACS repository to the latest version |
| `hacs_list_pending_updates` | READ | List HACS repositories with available updates |

### Tool count summary

| Module | Tool count |
|---|---|
| entities.py | 21 |
| automations.py | 10 |
| config.py | 10 |
| system.py | 16 |
| dashboards.py | 9 |
| hacs.py | 8 |
| **Total** | **74** |

---

## 10. s6-overlay Service Structure

s6-overlay v3 is used to manage both Home Assistant and the Aloha Agent inside the container. The `rootfs/` directory is `COPY`d into the image root during the Docker build.

### Exact file paths

```
rootfs/
└── etc/
    └── s6-overlay/
        └── s6-rc.d/
            ├── homeassistant/
            │   ├── type
            │   ├── run
            │   └── finish
            ├── aloha/
            │   ├── type
            │   ├── run
            │   ├── finish
            │   └── dependencies.d/
            │       └── homeassistant
            └── user/
                └── contents.d/
                    ├── homeassistant
                    └── aloha
```

### File contents

**`rootfs/etc/s6-overlay/s6-rc.d/homeassistant/type`**
```
longrun
```

**`rootfs/etc/s6-overlay/s6-rc.d/homeassistant/run`**
```bash
#!/command/with-contenv bash
# Skip if ALOHA_MODE=standalone
if [ "${ALOHA_MODE}" = "standalone" ]; then
    echo "ALOHA_MODE=standalone: skipping internal Home Assistant"
    exec sleep infinity
fi

exec hass --config /data/homeassistant
```

**`rootfs/etc/s6-overlay/s6-rc.d/homeassistant/finish`**
```bash
#!/command/with-contenv bash
echo "homeassistant service exited with code $1 (signal $2)"
```

**`rootfs/etc/s6-overlay/s6-rc.d/aloha/type`**
```
longrun
```

**`rootfs/etc/s6-overlay/s6-rc.d/aloha/run`**
```bash
#!/command/with-contenv bash
# Wait for HA to be ready (unless in standalone mode)
if [ "${ALOHA_MODE}" != "standalone" ]; then
    echo "Waiting for Home Assistant to be ready..."
    until curl -sf http://localhost:8123/api/ > /dev/null 2>&1; do
        sleep 2
    done
    echo "Home Assistant is ready."
fi

exec python -m uvicorn aloha.main:app \
    --host 0.0.0.0 \
    --port "${ALOHA_PORT:-7123}" \
    --log-level info
```

**`rootfs/etc/s6-overlay/s6-rc.d/aloha/finish`**
```bash
#!/command/with-contenv bash
echo "aloha service exited with code $1 (signal $2)"
```

**`rootfs/etc/s6-overlay/s6-rc.d/aloha/dependencies.d/homeassistant`**
```
(empty file — signals that aloha depends on homeassistant service)
```

**`rootfs/etc/s6-overlay/s6-rc.d/user/contents.d/homeassistant`**
```
(empty file — activates the homeassistant service in the user bundle)
```

**`rootfs/etc/s6-overlay/s6-rc.d/user/contents.d/aloha`**
```
(empty file — activates the aloha service in the user bundle)
```

### Service startup order

1. s6-overlay starts the `user` bundle.
2. `user/contents.d/homeassistant` activates the `homeassistant` longrun service.
3. `user/contents.d/aloha` activates the `aloha` longrun service.
4. Because `aloha/dependencies.d/homeassistant` exists, s6 starts `homeassistant` before `aloha`.
5. The `aloha/run` script additionally polls `http://localhost:8123/api/` before starting uvicorn, providing a health-based gate beyond the s6 dependency order.

---

## Appendix: Key Implementation Notes for Build Agents

1. **Encrypted credentials**: Never store `api_key` or `ha_token` as plaintext anywhere — not in config.json, not in logs, not in API responses. Use `aloha/auth/crypto.py` for all encrypt/decrypt operations.

2. **DiffEvent semantics**: When a tool needs to write a config file, it must NOT write the file directly. Instead it must emit a `DiffEvent` via the SSE stream and register the diff in the diff manager (`aloha/agent/diff.py`). The file is written only when the user calls `POST /api/approve` with `action: "apply"`.

3. **SafetyLevel enforcement**: The chat runner (`aloha/agent/runner.py`) must check each tool call's `SafetyLevel` before executing. `DESTRUCTIVE` and `WRITE_CONFIG` tools always require a `DiffEvent` / approval gate regardless of safety mode. `WRITE_SOFT` tools are auto-approved in `normal` and `permissive` modes. In `strict` mode, all writes require approval.

4. **SSE stream format**: Every event must be serialized as `data: <JSON>\n\n`. No other SSE fields (`id:`, `event:`, `retry:`) are required. The frontend's `src/lib/sse.ts` consumer assumes this format.

5. **Session IDs**: Use the prefix `ses_` followed by a 12-character hex string (e.g. `ses_a1b2c3d4e5f6`). Diff IDs use prefix `diff_`.

6. **Frontend build**: The React app is built with Vite (`npm run build`) and output lands in `frontend/dist/`. The FastAPI app mounts this directory as a StaticFiles route at `/` with `html=True` so that `index.html` is served for all non-API routes (SPA routing).

7. **HAOS add-on**: When `ALOHA_MODE=addon`, the HA URL should default to `http://supervisor/core` and the token comes from the `SUPERVISOR_TOKEN` environment variable (injected by the Supervisor). The `AlohaConfig.load()` method must handle this case.
