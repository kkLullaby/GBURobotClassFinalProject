import json

import httpx
import pytest
from gateway.config import PlatformConfig

from hermes_xiaozhi import adapter as adapter_module
from hermes_xiaozhi.adapter import XiaozhiAdapter


@pytest.mark.asyncio
async def test_adapter_send_returns_success_without_mcp_url(monkeypatch):
    monkeypatch.delenv("XIAOZHI_MCP_ADAPTER_URL", raising=False)

    adapter = XiaozhiAdapter(PlatformConfig())
    result = await adapter.send("ac:a7:04:30:91:78", "hello")

    assert result.success is True
    assert result.message_id.startswith("stub-")


@pytest.mark.asyncio
async def test_adapter_send_posts_to_mcp_url_when_set(monkeypatch):
    monkeypatch.setenv("XIAOZHI_MCP_ADAPTER_URL", "http://m1-adapter")
    received = []

    def handler(request: httpx.Request) -> httpx.Response:
        received.append(
            {
                "method": request.method,
                "url": str(request.url),
                "body": json.loads(request.content.decode()),
            }
        )
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(adapter_module.httpx, "AsyncClient", client_factory)

    adapter = XiaozhiAdapter(PlatformConfig())
    result = await adapter.send("ac:a7:04:30:91:78", "hello")

    assert result.success is True
    assert result.message_id.startswith("stub-")
    assert len(received) == 1
    assert received[0]["method"] == "POST"
    assert received[0]["url"] == "http://m1-adapter/tools/show_text"
    assert received[0]["body"] == {
        "device_id": "ac:a7:04:30:91:78",
        "text": "hello",
        "kind": "chat",
    }
