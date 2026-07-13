"""
Unit tests for opt-in error reporting + safe diagnostics (aloha/telemetry.py).

These never touch the network: with no DSN, init is a no-op, and the scrubber /
diagnostics builder are pure functions.
"""

from __future__ import annotations

import logging

from aloha import telemetry


def test_scrub_redacts_common_secret_shapes():
    samples = [
        "api_key: sk-ant-abc123456789 trailing",
        'Authorization: Bearer eyJhbGciOi.payloadpart.signaturepart',
        "token=amk_deadbeefcafe secret=ams_0123456789ab",
        'password: "hunter2supersecret"',
    ]
    for s in samples:
        out = telemetry.scrub(s)
        assert "«redacted»" in out
    # A concrete key must not survive verbatim.
    assert "sk-ant-abc123456789" not in telemetry.scrub("key sk-ant-abc123456789")
    assert "amk_deadbeefcafe" not in telemetry.scrub("token=amk_deadbeefcafe")


def test_scrub_leaves_ordinary_text_alone():
    text = "Turned on light.living_room and created automation bedtime_routine."
    assert telemetry.scrub(text) == text


def test_init_is_noop_without_dsn(config):
    # Fresh config has no DSN → reporting stays inactive, no exception.
    assert telemetry.init_error_reporting(config) is False
    assert telemetry.is_active() is False


def test_build_diagnostics_is_secret_free(config):
    # Seed the log ring with something sensitive.
    telemetry.install_log_ring()
    logging.getLogger("test.telemetry").info("using api_key sk-ant-SECRETVALUE123 now")

    diag = telemetry.build_diagnostics(config, note="my token is amk_TOPSECRET99", ha_connected=True)

    blob = "\n".join(diag["log_tail"]) + diag["note"]
    assert "sk-ant-SECRETVALUE123" not in blob
    assert "amk_TOPSECRET99" not in blob
    assert diag["aloha_version"] == telemetry.VERSION
    assert diag["ha_connected"] is True
    # Provider name is fine to include; the KEY must never be in the bundle.
    assert "ai_provider" in diag


def test_capture_report_returns_bundle_without_dsn(config):
    diag = telemetry.capture_report(config, note="something broke")
    assert diag["reported"] is False
    assert "log_tail" in diag
