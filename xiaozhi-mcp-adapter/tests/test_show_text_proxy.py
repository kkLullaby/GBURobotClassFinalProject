import json

import httpx
import pytest

from xiaozhi_mcp_adapter import proxy_http
from xiaozhi_mcp_adapter.show_text_proxy import build_show_text_jsonrpc


def test_build_show_text_jsonrpc_basic():
    result = build_show_text_jsonrpc(
        "ac:a7:04:30:91:78",
        "hello",
        kind="chat",
    )

    assert result["jsonrpc"] == "2.0"
    assert result["method"] == "tools/call"
    assert result["params"]["name"] == "self.otto.show_text"
    assert result["params"]["arguments"] == {"text": "hello", "kind": "chat"}
    assert isinstance(result["id"], str)
    assert len(result["id"]) == 32


def test_build_show_text_jsonrpc_truncates_long_text():
    result = build_show_text_jsonrpc(
        "ac:a7:04:30:91:78",
        "汉" * 50,
        kind="invalid",
    )

    text = result["params"]["arguments"]["text"]
    assert len(text) <= 30
    assert text.endswith("...")
    assert result["params"]["arguments"]["kind"] == "notification"


@pytest.mark.asyncio
async def test_proxy_http_post_show_text(monkeypatch):
    async def fake_call_show_text(pipe, device_id, text, kind):
        assert pipe is None
        assert device_id == "ac:a7:04:30:91:78"
        assert text == "测试一下"
        assert kind == "chat"
        return {"ok": True}

    monkeypatch.setattr(proxy_http, "call_show_text", fake_call_show_text)

    transport = httpx.ASGITransport(app=proxy_http.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/tools/show_text",
            content=json.dumps(
                {
                    "device_id": "ac:a7:04:30:91:78",
                    "text": "测试一下",
                    "kind": "chat",
                }
            ),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "echo": {"ok": True}}
