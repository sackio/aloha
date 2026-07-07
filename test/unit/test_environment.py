"""Environment detection: haos / docker / core."""

import pytest

import aloha.ha.environment as env


@pytest.fixture(autouse=True)
def _clear_env_cache():
    # detect_environment is lru_cached (env is static in prod); reset per test.
    env.detect_environment.cache_clear()
    yield
    env.detect_environment.cache_clear()


def test_supervisor_env(monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "tok123")
    assert env.supervisor_token() == "tok123"
    assert env.has_supervisor() is True
    e = env.detect_environment()
    assert e["kind"] == "haos"
    assert e["supervisor"] is True
    assert e["can_manage_system"] is True


def test_docker_env(monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    monkeypatch.setattr(env, "has_docker_socket", lambda: True)
    monkeypatch.setattr(env, "has_supervisor", lambda: False)
    e = env.detect_environment()
    assert e["kind"] == "docker"
    assert e["docker_socket"] is True
    assert e["can_manage_system"] is True


def test_core_env(monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    monkeypatch.setattr(env, "has_docker_socket", lambda: False)
    monkeypatch.setattr(env, "has_supervisor", lambda: False)
    e = env.detect_environment()
    assert e["kind"] == "core"
    assert e["can_manage_system"] is False


def test_shape(monkeypatch):
    monkeypatch.setattr(env, "has_docker_socket", lambda: False)
    monkeypatch.setattr(env, "has_supervisor", lambda: False)
    e = env.detect_environment()
    for key in ("kind", "supervisor", "docker_socket", "supervisor_url",
                "docker_sock", "can_manage_system"):
        assert key in e
