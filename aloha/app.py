"""
aloha/app.py

FastAPI application factory.

Usage
-----
    from aloha.app import create_app
    from aloha.config import AlohaConfig

    config = AlohaConfig.load()
    app = create_app(config)
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from aloha.config import AlohaConfig

log = logging.getLogger(__name__)

# Path to the built React frontend (relative to this file's package root)
_PACKAGE_DIR = Path(__file__).parent
_STATIC_DIR = _PACKAGE_DIR / "static"
_INDEX_HTML = _STATIC_DIR / "index.html"


def create_app(config: AlohaConfig) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Routers included:
      - /health           (health check)
      - /api/settings     (settings CRUD)
      - /api/providers    (provider list)
      - /api/auth/test    (connection test)
      - /api/context      (HA context snapshot)
      - /api/sessions     (session CRUD)
      - /api/chat         (SSE chat stream)
      - /api/approve      (diff approval)
      - /api/public-url   (relay / cloudflared / ngrok tunnels)
      - /api/relay        (managed relay account + $1/mo subscription)
      - /api/mcp-keys     (MCP access credentials)
      - /api/skills       (skill library browse/manage)
      - /mcp              (MCP SSE server, key+secret auth)
      - /mcp/token        (OAuth2 client-credentials token endpoint)
      - /                 (React SPA static files)

    Parameters
    ----------
    config : AlohaConfig
        The loaded runtime configuration.

    Returns
    -------
    FastAPI
        Configured application instance ready to be served.
    """
    app = FastAPI(
        title="Aloha",
        description="AI-powered Home Assistant agent",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # -----------------------------------------------------------------------
    # Store config on app state so routes can reach it if needed
    # -----------------------------------------------------------------------
    app.state.config = config

    # -----------------------------------------------------------------------
    # MCP endpoint auth: require a valid key secret on /mcp* whenever any MCP
    # key exists (mint one before exposing a public URL). No keys → open (local).
    # -----------------------------------------------------------------------
    from aloha.mcp import auth as mcp_auth

    def _mcp_authorized(request: Request) -> bool:
        """Accept OAuth client credentials as HTTP Basic (key:secret), a Bearer
        access token from /mcp/token, or X-Api-Key/X-Api-Secret headers."""
        h = request.headers.get("authorization", "")
        if h.startswith("Basic "):
            try:
                key, _, secret = base64.b64decode(h[6:]).decode().partition(":")
                if mcp_auth.verify_pair(config.data_dir, key, secret):
                    return True
            except Exception:
                pass
        if h.startswith("Bearer ") and mcp_auth.verify_token(config.data_dir, h[7:].strip()):
            return True
        k = request.headers.get("x-api-key", "")
        s = request.headers.get("x-api-secret", "")
        return bool(k and s and mcp_auth.verify_pair(config.data_dir, k, s))

    @app.middleware("http")
    async def _mcp_auth(request: Request, call_next):
        path = request.url.path
        # The token endpoint is how a client obtains auth — never gate it.
        if path != "/mcp/token" and (path == "/mcp" or path.startswith("/mcp/")):
            if mcp_auth.any_keys(config.data_dir) and not _mcp_authorized(request):
                return JSONResponse(
                    {"error": "unauthorized",
                     "message": "MCP key + secret required — HTTP Basic (key:secret) or a "
                                "Bearer token from POST /mcp/token."},
                    status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="aloha-mcp"'})
        return await call_next(request)

    @app.post("/mcp/token")
    async def mcp_token(request: Request):
        """OAuth2 client-credentials token endpoint. Client id/secret via HTTP
        Basic or form body; returns a short-lived Bearer access token."""
        client_id = client_secret = ""
        h = request.headers.get("authorization", "")
        if h.startswith("Basic "):
            try:
                client_id, _, client_secret = base64.b64decode(h[6:]).decode().partition(":")
            except Exception:
                pass
        try:
            form = await request.form()
        except Exception:
            form = {}
        grant = form.get("grant_type", "client_credentials")
        client_id = client_id or form.get("client_id", "")
        client_secret = client_secret or form.get("client_secret", "")
        if grant != "client_credentials":
            return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)
        if not mcp_auth.verify_pair(config.data_dir, client_id, client_secret):
            return JSONResponse({"error": "invalid_client"}, status_code=401)
        return JSONResponse(mcp_auth.issue_token(config.data_dir, client_id))

    # -----------------------------------------------------------------------
    # Include API routers
    # -----------------------------------------------------------------------

    from aloha.routes.health import router as health_router
    app.include_router(health_router)

    from aloha.routes.settings import router as settings_router
    app.include_router(settings_router)

    from aloha.routes.context_route import router as context_router
    app.include_router(context_router)

    from aloha.routes.chat import router as chat_router
    app.include_router(chat_router)

    from aloha.routes.managed import router as managed_router
    app.include_router(managed_router)

    from aloha.routes.skills_route import router as skills_router
    app.include_router(skills_router)

    from aloha.routes.public_url_route import router as public_url_router
    app.include_router(public_url_router)

    from aloha.routes.relay_account import router as relay_account_router
    app.include_router(relay_account_router)

    from aloha.routes.mcp_keys_route import router as mcp_keys_router
    app.include_router(mcp_keys_router)

    # -----------------------------------------------------------------------
    # Public MCP URL manager (relay / cloudflared / ngrok) — lets a box behind
    # NAT expose /mcp to cloud chatbots. Auto-starts if a provider is configured.
    # -----------------------------------------------------------------------
    from aloha.public_url import PublicUrlManager

    app.state.public_url_manager = PublicUrlManager(
        relay_url=config.managed_relay_url,
        data_dir=config.data_dir,
        local_port=config.port,
    )

    @app.on_event("startup")
    async def _start_public_url() -> None:
        if config.public_url_provider and config.public_url_provider != "none":
            log.info("Starting public MCP URL via %s", config.public_url_provider)
            relay_token = (config.relay_token or "") or (
                config.api_key or "" if config.ai_provider == "aloha" else "")
            await app.state.public_url_manager.start(
                config.public_url_provider, config.ngrok_authtoken or "", relay_token
            )

    @app.on_event("shutdown")
    async def _stop_public_url() -> None:
        await app.state.public_url_manager.stop()

    # -----------------------------------------------------------------------
    # Mount MCP server at /mcp
    # -----------------------------------------------------------------------
    try:
        from aloha.mcp.server import create_mcp_server
        from starlette.responses import Response
        from starlette.routing import Mount

        mcp_server, sse_transport = create_mcp_server(config)

        @app.get("/mcp")
        async def mcp_sse(request: Request):
            """MCP SSE endpoint for external AI clients (Claude Code, Cursor, …)."""
            async with sse_transport.connect_sse(
                request.scope, request.receive, request._send
            ) as (read_stream, write_stream):
                await mcp_server.run(
                    read_stream, write_stream, mcp_server.create_initialization_options()
                )
            return Response()

        # Client→server message channel (ASGI mount at the path the transport advertises).
        app.router.routes.append(Mount("/mcp/messages/", app=sse_transport.handle_post_message))

        log.info("MCP server mounted at /mcp (SSE)")
    except Exception as exc:
        log.warning("Could not mount MCP server: %s", exc)

    # -----------------------------------------------------------------------
    # Serve React static files
    # -----------------------------------------------------------------------
    if _STATIC_DIR.exists():
        # Mount static assets (JS, CSS, images) — must come before SPA fallback
        app.mount(
            "/assets",
            StaticFiles(directory=_STATIC_DIR / "assets"),
            name="assets",
        )

        # SPA fallback: serve index.html for all non-API, non-/mcp paths
        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str, request: Request):
            """
            Serve the React SPA for all frontend routes.

            API paths (/api/*, /health, /auth/*, /mcp*) are handled
            by their own routers and never reach this handler because
            FastAPI routes are matched in registration order and the
            routers above are registered first.
            """
            # Try to serve the exact file first (e.g. favicon.ico, manifest.json)
            candidate = _STATIC_DIR / full_path
            if candidate.exists() and candidate.is_file():
                return FileResponse(candidate)

            # Fall back to index.html for all SPA routes
            if _INDEX_HTML.exists():
                return FileResponse(_INDEX_HTML)

            return HTMLResponse("<h1>Aloha frontend not built</h1>", status_code=200)

    else:
        log.warning(
            "Static directory %s does not exist — React frontend not served. "
            "Run `npm run build` inside the frontend/ directory.",
            _STATIC_DIR,
        )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def no_frontend(full_path: str):
            return HTMLResponse(
                "<h1>Aloha</h1><p>Frontend not built. Run <code>npm run build</code>.</p>",
                status_code=200,
            )

    return app
