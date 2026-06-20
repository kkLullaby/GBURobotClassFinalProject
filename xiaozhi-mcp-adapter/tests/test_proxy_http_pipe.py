from starlette.testclient import TestClient

from xiaozhi_mcp_adapter import pipe as pipe_module
from xiaozhi_mcp_adapter import proxy_http, show_text_proxy


def test_startup_hook_skips_when_no_env(monkeypatch):
    monkeypatch.delenv("MCP_ENDPOINT", raising=False)
    show_text_proxy._PIPE = object()

    async def forbidden_connect(url):
        raise AssertionError("pipe.connect should not be called without MCP_ENDPOINT")

    monkeypatch.setattr(pipe_module, "connect", forbidden_connect)

    with TestClient(proxy_http.app):
        assert show_text_proxy._PIPE is None

    assert show_text_proxy._PIPE is None


def test_startup_hook_assigns_pipe_when_env(monkeypatch):
    monkeypatch.setenv("MCP_ENDPOINT", "ws://fake")

    class FakePipe:
        def __init__(self):
            self.closed = False

        async def close(self):
            self.closed = True

    fake_pipe = FakePipe()

    async def fake_connect(url):
        assert url == "ws://fake"
        return fake_pipe

    monkeypatch.setattr(pipe_module, "connect", fake_connect)

    with TestClient(proxy_http.app):
        assert show_text_proxy._PIPE is fake_pipe
        assert fake_pipe.closed is False

    assert show_text_proxy._PIPE is None
    assert fake_pipe.closed is True
