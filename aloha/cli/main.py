"""
aloha/cli/main.py

Click CLI for interacting with the Aloha agent over HTTP/SSE.

Commands:
    aloha chat [MESSAGE] [--session ID] [--mode supervised|autonomous]
    aloha status
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click
import httpx
from rich.console import Console
from rich.table import Table

console = Console()


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _get_base_url() -> str:
    config_path = Path("/data/aloha/config.json")
    port = 7123
    if config_path.exists():
        try:
            with config_path.open() as f:
                data = json.load(f)
            port = int(data.get("port", 7123))
        except Exception:
            pass
    return f"http://localhost:{port}"


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

async def _create_session(base_url: str) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(f"{base_url}/api/sessions", json={"title": "CLI session"})
        r.raise_for_status()
        return r.json()["id"]


# ---------------------------------------------------------------------------
# SSE stream consumer
# ---------------------------------------------------------------------------

async def _stream_chat(
    base_url: str,
    session_id: str,
    message: str,
    mode: str,
    interactive: bool,
) -> None:
    """
    POST /api/chat and consume the SSE stream, printing events as they arrive.
    Returns True if a diff was received and auto-approved (single-message mode).
    """
    payload = {
        "session_id": session_id,
        "message": message,
        "mode": mode,
    }

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            f"{base_url}/api/chat",
            json=payload,
            headers={"Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue

                raw = line[len("data:"):].strip()
                if not raw:
                    continue

                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type")

                if event_type == "content":
                    delta = event.get("delta", "")
                    console.print(delta, end="", markup=False, highlight=False)
                    sys.stdout.flush()

                elif event_type == "tool_call":
                    name = event.get("name", "")
                    args = event.get("args", {})
                    # Truncate args preview to 80 chars
                    args_str = json.dumps(args)
                    if len(args_str) > 80:
                        args_str = args_str[:77] + "..."
                    console.print(
                        f"\n[dim][{name}({args_str})][/dim]"
                    )

                elif event_type == "tool_result":
                    result = event.get("result", "")
                    preview = result[:100] + ("..." if len(result) > 100 else "")
                    console.print(f"[dim]-> {preview}[/dim]")

                elif event_type == "diff":
                    path = event.get("path", "")
                    diff_id = event.get("id", "")
                    console.print(
                        f"\n[yellow]Proposed change to {path}. "
                        f"Type 'approve' or 'reject':[/yellow]"
                    )

                    if interactive:
                        # Prompt the user in interactive mode
                        try:
                            answer = await asyncio.get_event_loop().run_in_executor(
                                None, lambda: input("").strip().lower()
                            )
                        except (EOFError, KeyboardInterrupt):
                            answer = "reject"

                        action = "apply" if answer == "approve" else "reject"
                    else:
                        # Auto-approve in single-message mode
                        console.print("[dim](auto-approving in single-message mode)[/dim]")
                        action = "apply"

                    # Send the approval
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as approve_client:
                            ar = await approve_client.post(
                                f"{base_url}/api/approve",
                                json={"diff_id": diff_id, "action": action},
                            )
                            ar.raise_for_status()
                        console.print(
                            f"[dim]Diff {diff_id} {action}d.[/dim]"
                        )
                    except Exception as exc:
                        console.print(f"[red]Failed to {action} diff: {exc}[/red]")

                elif event_type == "done":
                    console.print()  # final newline after streamed content
                    usage = event.get("usage")
                    if usage:
                        in_tok = usage.get("input_tokens", 0)
                        out_tok = usage.get("output_tokens", 0)
                        console.print(
                            f"[dim]({in_tok} in / {out_tok} out tokens)[/dim]"
                        )

                elif event_type == "error":
                    msg = event.get("message", "unknown error")
                    console.print(f"\n[red]Error: {msg}[/red]")


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
def cli() -> None:
    """Aloha — AI-powered Home Assistant agent CLI."""


# ---------------------------------------------------------------------------
# chat command
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("message", required=False, default=None)
@click.option(
    "--session",
    "session_id",
    default=None,
    help="Session ID to continue. Creates a new session if omitted.",
)
@click.option(
    "--mode",
    "mode",
    default="supervised",
    type=click.Choice(["supervised", "autonomous"], case_sensitive=False),
    show_default=True,
    help="Agent mode.",
)
def chat(message: Optional[str], session_id: Optional[str], mode: str) -> None:
    """
    Chat with the Aloha agent.

    Without MESSAGE: start an interactive readline REPL.
    With MESSAGE: send a single message and stream the response.
    """
    asyncio.run(_chat_async(message=message, session_id=session_id, mode=mode))


async def _chat_async(
    message: Optional[str],
    session_id: Optional[str],
    mode: str,
) -> None:
    base_url = _get_base_url()

    # Resolve or create session
    if not session_id:
        try:
            session_id = await _create_session(base_url)
            console.print(f"[dim]Session: {session_id}[/dim]")
        except Exception as exc:
            console.print(f"[red]Failed to create session: {exc}[/red]")
            raise SystemExit(1)

    if message is not None:
        # Single-message mode
        try:
            await _stream_chat(
                base_url=base_url,
                session_id=session_id,
                message=message,
                mode=mode,
                interactive=False,
            )
        except httpx.HTTPStatusError as exc:
            console.print(f"[red]HTTP {exc.response.status_code}: {exc.response.text}[/red]")
            raise SystemExit(1)
        except Exception as exc:
            console.print(f"[red]Error: {exc}[/red]")
            raise SystemExit(1)
        return

    # Interactive REPL
    console.print(
        f"[bold green]Aloha[/bold green] [dim]({mode} mode, session {session_id})[/dim]"
    )
    console.print("[dim]Type 'exit' or 'quit' to leave, Ctrl-C to abort.[/dim]\n")

    loop = asyncio.get_event_loop()

    while True:
        try:
            user_input = await loop.run_in_executor(
                None, lambda: input("You: ").strip()
            )
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            console.print("[dim]Goodbye.[/dim]")
            break

        console.print()
        try:
            await _stream_chat(
                base_url=base_url,
                session_id=session_id,
                message=user_input,
                mode=mode,
                interactive=True,
            )
        except httpx.HTTPStatusError as exc:
            console.print(
                f"[red]HTTP {exc.response.status_code}: {exc.response.text}[/red]"
            )
        except Exception as exc:
            console.print(f"[red]Error: {exc}[/red]")

        console.print()


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------

@cli.command()
def status() -> None:
    """Show Aloha agent health status."""
    asyncio.run(_status_async())


async def _status_async() -> None:
    base_url = _get_base_url()

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{base_url}/health")
            r.raise_for_status()
            data = r.json()
    except httpx.ConnectError:
        console.print(f"[red]Cannot connect to Aloha at {base_url}[/red]")
        raise SystemExit(1)
    except httpx.HTTPStatusError as exc:
        console.print(f"[red]HTTP {exc.response.status_code}: {exc.response.text}[/red]")
        raise SystemExit(1)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise SystemExit(1)

    table = Table(title=f"Aloha Status  [dim]{base_url}[/dim]", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    overall = data.get("status", "unknown")
    status_color = "green" if overall == "ok" else "red"
    table.add_row("Status", f"[{status_color}]{overall}[/{status_color}]")

    ha_connected = data.get("ha_connected", False)
    ha_color = "green" if ha_connected else "red"
    table.add_row("HA Connected", f"[{ha_color}]{ha_connected}[/{ha_color}]")

    if "ha_version" in data:
        table.add_row("HA Version", str(data["ha_version"]))

    setup_complete = data.get("setup_complete", False)
    setup_color = "green" if setup_complete else "yellow"
    table.add_row(
        "Setup Complete",
        f"[{setup_color}]{setup_complete}[/{setup_color}]",
    )

    if "provider" in data:
        table.add_row("AI Provider", str(data["provider"]))

    console.print(table)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
