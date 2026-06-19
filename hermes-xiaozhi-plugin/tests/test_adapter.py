import hashlib
import hmac
import json
import asyncio

import aiohttp
import pytest
from gateway.config import PlatformConfig

from hermes_xiaozhi.adapter import XiaozhiAdapter


def _body(payload):
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()


def _signature(secret, body):
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return "sha256=" + digest


def _clear_env(monkeypatch):
    for name in (
        "XIAOZHI_WEBHOOK_HOST",
        "XIAOZHI_WEBHOOK_PORT",
        "XIAOZHI_WEBHOOK_SECRET",
        "XIAOZHI_DEVICE_ID",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.asyncio
async def test_connect_handles_signed_webhook(monkeypatch):
    _clear_env(monkeypatch)
    secret = "test-secret"
    device_id = "ac:a7:04:30:91:78"
    payload = {
        "user_text": "你好",
        "assistant_text": "echoed: 你好",
        "device_id": device_id,
    }
    body = _body(payload)

    adapter = XiaozhiAdapter(
        PlatformConfig(
            extra={
                "host": "127.0.0.1",
                "port": 0,
                "webhook_secret": secret,
                "device_id": "fallback-device",
            }
        )
    )
    received = []
    handled = asyncio.Event()

    async def fake_handle_message(event):
        received.append(event)
        handled.set()

    adapter.handle_message = fake_handle_message

    no_secret_adapter = XiaozhiAdapter(
        PlatformConfig(extra={"host": "127.0.0.1", "port": 0})
    )
    no_secret_received = []

    async def no_secret_handle_message(event):
        no_secret_received.append(event)

    no_secret_adapter.handle_message = no_secret_handle_message

    await adapter.connect()
    await no_secret_adapter.connect()
    try:
        url = (
            f"http://127.0.0.1:{adapter.webhook_port}"
            "/webhooks/xiaozhi-transcript"
        )
        no_secret_url = (
            f"http://127.0.0.1:{no_secret_adapter.webhook_port}"
            "/webhooks/xiaozhi-transcript"
        )
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": _signature(secret, body),
                },
            )
            assert response.status == 202
            await asyncio.wait_for(handled.wait(), timeout=1)

            invalid = await session.post(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": "sha256=bad",
                },
            )
            assert invalid.status == 401

            missing = await session.post(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
            )
            assert missing.status == 401

            no_secret = await session.post(
                no_secret_url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": _signature(secret, body),
                },
            )
            assert no_secret.status == 403

        assert len(received) == 1
        event = received[0]
        assert event.text == "XiaoZhi user said: 你好. Assistant replied: echoed: 你好"
        assert event.source.chat_id == f"xiaozhi:{device_id}"
        assert event.raw_message == payload
        assert no_secret_received == []
    finally:
        await adapter.disconnect()
        await no_secret_adapter.disconnect()
