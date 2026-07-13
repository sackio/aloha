"""
Integration tests for the "report a problem" route.

No error-reporting DSN is configured, so nothing is sent off-box; the route
still returns a secrets-free diagnostics bundle + a prefilled GitHub issue URL.
"""

from __future__ import annotations


def test_diagnostics_endpoint(client):
    r = client.get("/api/report/diagnostics")
    assert r.status_code == 200
    body = r.json()
    assert body["aloha_version"]
    assert body["error_reporting_active"] is False
    assert isinstance(body["log_tail"], list)


def test_report_problem_bundles_issue_url_and_scrubs(client):
    r = client.post("/api/report/problem", json={"note": "leaking sk-ant-SHOULDNOTLEAK123"})
    assert r.status_code == 200
    body = r.json()
    assert body["reported"] is False           # no DSN → not forwarded
    assert body["error_reporting_active"] is False
    assert body["github_issue_url"].startswith("https://github.com/sackio/aloha/issues/new?")
    # The secret must not survive anywhere in the response.
    assert "sk-ant-SHOULDNOTLEAK123" not in r.text
