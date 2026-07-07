"""
Shared pytest fixtures for the Aloha box test suite.

The FastAPI app runs fully in-process (Starlette TestClient) against a temporary
data directory — no live Home Assistant, no network. Routes that read config do
so via AlohaConfig.load(), which honours the ALOHA_DATA_DIR env the `data_dir`
fixture sets, so each test is isolated.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Isolated data dir; routes load config from here via ALOHA_DATA_DIR."""
    d = tmp_path / "aloha"
    d.mkdir()
    monkeypatch.setenv("ALOHA_DATA_DIR", str(d))
    # Never let a real HA env leak into tests.
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    return d


@pytest.fixture
def config(data_dir):
    from aloha.config import AlohaConfig
    return AlohaConfig.load()


@pytest.fixture
def app(data_dir):
    from aloha.app import create_app
    from aloha.config import AlohaConfig
    return create_app(AlohaConfig.load())


@pytest.fixture
def client(app):
    """TestClient WITHOUT lifespan (no provider auto-start) — routes only."""
    return TestClient(app)
