"""
aloha/public_url.py

Give the box's local MCP endpoint a public URL so a cloud chatbot can reach it
even when the box sits behind home NAT. Three interchangeable providers:

  • relay       — our hosted reverse-tunnel (aloha.pushbuild.com). Stable branded
                  URL, no third-party account. The paid ($1/mo) tier.
  • cloudflared — bundled Cloudflare quick tunnel. Free, zero-config, but the URL
                  is random + ephemeral (changes each start).
  • ngrok       — user brings their own ngrok authtoken (BYOK). Their account.

All three end up exposing the box's `http://127.0.0.1:<port>/mcp` at some public
`…/mcp` URL. The manager runs the chosen provider as a background task/process
and reports the current URL + status.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
from pathlib import Path

import httpx

from aloha import relay_tunnel

log = logging.getLogger("aloha.public_url")

Provider = str  # "none" | "relay" | "cloudflared" | "ngrok"


class PublicUrlManager:
    """Owns at most one active tunnel and exposes its public MCP URL."""

    def __init__(self, relay_url: str, data_dir: Path, local_port: int):
        self.relay_url = relay_url
        self.data_dir = Path(data_dir)
        self.local_base = f"http://127.0.0.1:{local_port}"
        self.provider: Provider = "none"
        self.url: str = ""
        self.error: str = ""
        self._task: asyncio.Task | None = None
        self._proc: asyncio.subprocess.Process | None = None

    def status(self) -> dict:
        return {
            "provider": self.provider,
            "url": self.url,
            "online": bool(self.url) and (
                (self._task is not None and not self._task.done())
                or (self._proc is not None and self._proc.returncode is None)
            ),
            "error": self.error,
        }

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await self._task
            self._task = None
        if self._proc and self._proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                self._proc.terminate()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(self._proc.wait(), timeout=5)
            self._proc = None
        self.provider = "none"
        self.url = ""
        self.error = ""

    async def start(self, provider: Provider, ngrok_authtoken: str = "",
                    relay_token: str = "") -> dict:
        await self.stop()
        self.provider = provider
        self.error = ""
        try:
            if provider == "relay":
                await self._start_relay(relay_token)
            elif provider == "cloudflared":
                await self._start_cloudflared()
            elif provider == "ngrok":
                await self._start_ngrok(ngrok_authtoken)
            elif provider == "none":
                pass
            else:
                raise ValueError(f"unknown provider {provider!r}")
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            self.provider = "none"
            log.warning("public-url start (%s) failed: %s", provider, exc)
        return self.status()

    # -- relay ---------------------------------------------------------------

    async def _start_relay(self, relay_token: str = "") -> None:
        creds = await asyncio.to_thread(
            relay_tunnel.ensure_registered, self.relay_url, self.data_dir, relay_token
        )
        self.url = relay_tunnel.public_url(self.relay_url, creds["box_id"])
        self._task = asyncio.create_task(
            relay_tunnel.run_tunnel(
                self.relay_url, creds["box_id"], creds["token"], self.local_base
            )
        )

    # -- cloudflared ---------------------------------------------------------

    async def _start_cloudflared(self) -> None:
        self._proc = await asyncio.create_subprocess_exec(
            "cloudflared", "tunnel", "--no-autoupdate", "--url", self.local_base,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        url = await self._scan(self._proc, re.compile(rb"https://[a-z0-9-]+\.trycloudflare\.com"))
        self.url = url.rstrip("/") + "/mcp"

    # -- ngrok ---------------------------------------------------------------

    async def _start_ngrok(self, authtoken: str) -> None:
        args = ["ngrok", "http", str(self.local_base.rsplit(":", 1)[1]),
                "--log", "stdout", "--log-format", "logfmt"]
        if authtoken:
            args += ["--authtoken", authtoken]
        self._proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        # ngrok exposes the public URL on its local API once up.
        for _ in range(30):
            await asyncio.sleep(0.5)
            try:
                async with httpx.AsyncClient(timeout=3) as c:
                    r = await c.get("http://127.0.0.1:4040/api/tunnels")
                tuns = r.json().get("tunnels", [])
                pub = next((t["public_url"] for t in tuns
                            if t.get("public_url", "").startswith("https")), "")
                if pub:
                    self.url = pub.rstrip("/") + "/mcp"
                    return
            except Exception:
                pass
        raise RuntimeError("ngrok did not report a public URL (check the authtoken)")

    async def _scan(self, proc: asyncio.subprocess.Process, pattern: re.Pattern) -> str:
        """Read a subprocess's output until `pattern` matches; return the match."""
        assert proc.stdout is not None
        for _ in range(2000):
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=30)
            if not line:
                break
            m = pattern.search(line)
            if m:
                return m.group(0).decode()
        raise RuntimeError("tunnel binary did not print a public URL")
