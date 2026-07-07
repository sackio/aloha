"""Relay tunnel client: URL building + creds persistence (no network)."""

from aloha import relay_tunnel


def test_public_url():
    assert relay_tunnel.public_url("https://aloha.pushbuild.com", "box123") == \
        "https://aloha.pushbuild.com/box/box123/mcp"
    # trailing slash tolerated
    assert relay_tunnel.public_url("https://x.com/", "b") == "https://x.com/box/b/mcp"


def test_ws_url_scheme():
    assert relay_tunnel._ws_url("https://x.com", "b", "t").startswith("wss://x.com/tunnel/b?token=t")
    assert relay_tunnel._ws_url("http://x.com", "b", "t").startswith("ws://x.com/tunnel/b?token=t")


def test_creds_persistence(data_dir):
    assert relay_tunnel.load_creds(data_dir) is None
    relay_tunnel._creds_path(data_dir).write_text('{"box_id":"b","token":"t"}')
    creds = relay_tunnel.load_creds(data_dir)
    assert creds["box_id"] == "b"
    assert creds["token"] == "t"
