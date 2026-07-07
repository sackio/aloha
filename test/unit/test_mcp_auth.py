"""MCP auth: key+secret credentials, verification, token endpoint, lifecycle."""

from aloha.mcp import auth


def test_no_keys_means_open(data_dir):
    assert auth.any_keys(data_dir) is False


def test_mint_and_verify_pair(data_dir):
    cred = auth.mint(data_dir, "laptop")
    assert cred["key"].startswith("amk_")
    assert cred["secret"].startswith("ams_")
    assert auth.any_keys(data_dir) is True
    assert auth.verify_pair(data_dir, cred["key"], cred["secret"]) is True
    # wrong secret / wrong key / empties
    assert auth.verify_pair(data_dir, cred["key"], "ams_wrong") is False
    assert auth.verify_pair(data_dir, "amk_wrong", cred["secret"]) is False
    assert auth.verify_pair(data_dir, "", "") is False


def test_secret_not_stored_plaintext(data_dir):
    cred = auth.mint(data_dir, "x")
    stored = (data_dir / "mcp_keys.json").read_text()
    assert cred["secret"] not in stored
    assert cred["secret"][:12] in stored  # prefix only


def test_list_hides_secret(data_dir):
    auth.mint(data_dir, "one")
    rows = auth.list_keys(data_dir)
    assert len(rows) == 1
    assert "secret" not in rows[0]
    assert rows[0]["name"] == "one"


def test_regenerate_rotates_secret(data_dir):
    cred = auth.mint(data_dir, "x")
    new = auth.regenerate(data_dir, cred["key"])
    assert new["secret"] != cred["secret"]
    assert auth.verify_pair(data_dir, cred["key"], cred["secret"]) is False
    assert auth.verify_pair(data_dir, cred["key"], new["secret"]) is True
    assert auth.regenerate(data_dir, "amk_missing") is None


def test_revoke(data_dir):
    cred = auth.mint(data_dir, "x")
    assert auth.revoke(data_dir, cred["key"]) is True
    assert auth.verify_pair(data_dir, cred["key"], cred["secret"]) is False
    assert auth.any_keys(data_dir) is False
    assert auth.revoke(data_dir, cred["key"]) is False  # already gone


def test_access_token_issue_and_verify(data_dir):
    cred = auth.mint(data_dir, "x")
    tok = auth.issue_token(data_dir, cred["key"])
    assert tok["token_type"] == "Bearer"
    assert tok["access_token"].startswith("amt_")
    assert auth.verify_token(data_dir, tok["access_token"]) is True
    assert auth.verify_token(data_dir, "amt_bogus") is False


def test_regenerate_invalidates_tokens(data_dir):
    cred = auth.mint(data_dir, "x")
    tok = auth.issue_token(data_dir, cred["key"])
    auth.regenerate(data_dir, cred["key"])
    assert auth.verify_token(data_dir, tok["access_token"]) is False
