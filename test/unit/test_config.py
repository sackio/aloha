"""Config: encrypted credential round-trips + env injection."""

import json

from aloha.config import AlohaConfig


def _cfg_json(cfg) -> dict:
    return json.loads((cfg.data_dir / "config.json").read_text())


def test_defaults(config):
    assert config.ai_provider  # a default provider is set
    assert config.port == 7123
    assert config.public_url_provider == "none"
    assert config.setup_complete is False


def test_api_key_encrypted_round_trip(config):
    config.api_key = "DUMMY-not-a-real-key"
    config.save()
    reloaded = AlohaConfig.load()
    assert reloaded.api_key == "DUMMY-not-a-real-key"
    raw = _cfg_json(config)
    assert "DUMMY-not-a-real-key" not in json.dumps(raw)  # never plaintext
    assert "api_key_enc" in raw


def test_all_secrets_encrypted(config):
    config.api_key = "aaa-key"
    config.ha_token = "bbb-token"
    config.ngrok_authtoken = "ccc-ngrok"
    config.relay_token = "ddd-relay"
    config.save()
    raw = json.dumps(_cfg_json(config))
    for secret in ("aaa-key", "bbb-token", "ccc-ngrok", "ddd-relay"):
        assert secret not in raw
    reloaded = AlohaConfig.load()
    assert reloaded.api_key == "aaa-key"
    assert reloaded.ha_token == "bbb-token"
    assert reloaded.ngrok_authtoken == "ccc-ngrok"
    assert reloaded.relay_token == "ddd-relay"


def test_clearing_secret(config):
    config.relay_token = "temp"
    config.save()
    assert AlohaConfig.load().relay_token == "temp"
    config.relay_token = ""
    config.save()
    assert AlohaConfig.load().relay_token is None


def test_env_injection(config, monkeypatch):
    monkeypatch.setenv("ALOHA_API_KEY", "env-injected-key")
    reloaded = AlohaConfig.load()
    assert reloaded.api_key == "env-injected-key"


def test_non_secret_fields_persist(config):
    config.public_url_provider = "cloudflared"
    config.setup_complete = True
    config.save()
    reloaded = AlohaConfig.load()
    assert reloaded.public_url_provider == "cloudflared"
    assert reloaded.setup_complete is True
