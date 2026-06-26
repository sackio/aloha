"""
aloha/__main__.py

Entry point: python -m aloha

Startup sequence
----------------
1. Load AlohaConfig (env vars + data_dir/config.json).
2. Configure logging.
3. await bootstrap(config) — wait for HA, acquire/validate token, return HAClient.
4. init_context_engine and await start() — begin background context refresh.
5. create_app(config) — assemble the FastAPI application.
6. uvicorn.Server(Config(...)).serve() — run until shutdown.
"""

from __future__ import annotations

import asyncio
import logging
import sys


def _configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )
    # Quieten noisy third-party loggers
    for noisy in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


async def main() -> None:
    import os

    # -----------------------------------------------------------------------
    # 1. Load config
    # -----------------------------------------------------------------------
    from aloha.config import AlohaConfig

    config = AlohaConfig.load()

    # Derive debug flag from env
    debug = os.environ.get("ALOHA_DEBUG", "").lower() in ("1", "true", "yes")
    _configure_logging(debug=debug)

    log = logging.getLogger(__name__)
    log.info(
        "Aloha starting — provider=%s mode=%s port=%d",
        config.ai_provider,
        config.mode,
        config.port,
    )

    # -----------------------------------------------------------------------
    # 2. Bootstrap HA connection
    # -----------------------------------------------------------------------
    from aloha.bootstrap import bootstrap

    try:
        ha_client = await bootstrap(config)
        log.info("HA bootstrap complete.")
    except RuntimeError as exc:
        log.error("HA bootstrap failed: %s", exc)
        log.warning(
            "Continuing without a live HA connection. "
            "Chat and tools will be unavailable until HA is reachable."
        )
        ha_client = None

    # -----------------------------------------------------------------------
    # 3. Initialise and start context engine
    # -----------------------------------------------------------------------
    context_engine = None
    if ha_client is not None:
        from aloha.context.engine import init_context_engine

        context_engine = init_context_engine(
            ha_client=ha_client,
            ha_config_dir=config.ha_config_dir,
            refresh_minutes=config.context_refresh_minutes,
        )
        await context_engine.start()
        log.info(
            "Context engine started (refresh every %d min).",
            config.context_refresh_minutes,
        )
    else:
        log.warning("Context engine not started — HA client unavailable.")

    # -----------------------------------------------------------------------
    # 3b. Initialise and start the external MCP client manager (best-effort)
    # -----------------------------------------------------------------------
    from aloha.mcp.client import init_mcp_manager

    mcp_manager = init_mcp_manager(config.data_dir)
    try:
        await mcp_manager.start()
    except Exception:
        log.warning("MCP client manager failed to start", exc_info=True)

    # -----------------------------------------------------------------------
    # 4. Create FastAPI app
    # -----------------------------------------------------------------------
    from aloha.app import create_app

    app = create_app(config)

    # -----------------------------------------------------------------------
    # 5. Run uvicorn
    # -----------------------------------------------------------------------
    import uvicorn

    uvi_config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=config.port,
        log_level="debug" if debug else "info",
        # Disable uvicorn's own log config so our basicConfig applies
        log_config=None,
        # Allow the event loop we're already running in to be reused
        loop="none",
    )
    server = uvicorn.Server(uvi_config)

    log.info("Aloha listening on 0.0.0.0:%d", config.port)

    try:
        await server.serve()
    finally:
        # Graceful teardown
        if context_engine is not None:
            await context_engine.stop()
            log.info("Context engine stopped.")

        if ha_client is not None:
            await ha_client.close()
            log.info("HA client closed.")

        try:
            await mcp_manager.stop()
        except Exception:
            log.debug("Error stopping MCP client manager", exc_info=True)

        log.info("Aloha shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
