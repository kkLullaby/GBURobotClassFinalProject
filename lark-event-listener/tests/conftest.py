"""Common fixtures: stub env + unset proxy (bitter lesson #36)."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _lark_env(monkeypatch):
    monkeypatch.setenv("LARK_APP_ID", "cli_testapp")
    monkeypatch.setenv("LARK_APP_SECRET", "test-secret")
    monkeypatch.setenv("LARK_HOST", "https://open.feishu.cn")
    monkeypatch.setenv("LARK_LISTENER_HERMES_TIMEOUT_S", "5")
    for k in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy",
              "HTTPS_PROXY", "https_proxy", "NO_PROXY", "no_proxy"):
        monkeypatch.delenv(k, raising=False)
    yield
