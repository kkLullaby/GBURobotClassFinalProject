"""Common fixtures: set env to predictable values, force fresh LarkClient per test."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _lark_env(monkeypatch):
    monkeypatch.setenv("LARK_APP_ID", "cli_testapp")
    monkeypatch.setenv("LARK_APP_SECRET", "test-secret")
    monkeypatch.setenv("LARK_USER_MOBILE", "13800000000")
    monkeypatch.setenv("LARK_HOST", "https://open.feishu.cn")
    # Strip SOCKS proxy envs — httpx (used by client.py) rejects scheme `socks://`
    # at AsyncClient init even when respx has already patched the transport.
    for k in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy",
              "HTTPS_PROXY", "https_proxy", "NO_PROXY", "no_proxy"):
        monkeypatch.delenv(k, raising=False)
    yield
