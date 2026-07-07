"""Public-URL manager: status shape + lifecycle (no real tunnels)."""

import pytest

from aloha.public_url import PublicUrlManager


@pytest.fixture
def mgr(data_dir):
    return PublicUrlManager("https://relay.test", data_dir, 7123)


def test_initial_status(mgr):
    st = mgr.status()
    assert st == {"provider": "none", "url": "", "online": False, "error": ""}


async def test_start_none_is_noop(mgr):
    st = await mgr.start("none")
    assert st["provider"] == "none"
    assert st["online"] is False


async def test_unknown_provider_errors(mgr):
    st = await mgr.start("bogus")
    assert st["error"]
    assert st["provider"] == "none"


async def test_local_base(mgr):
    assert mgr.local_base == "http://127.0.0.1:7123"
