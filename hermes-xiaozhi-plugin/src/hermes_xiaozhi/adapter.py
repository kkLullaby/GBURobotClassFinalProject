"""XiaoZhi platform adapter for Hermes Agent."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
from typing import Any, Dict, Optional

import httpx
from aiohttp import web

from gateway.config import Platform, PlatformConfig
from gateway.platform_registry import PlatformEntry, platform_registry
from gateway.platforms.base import (
    BasePlatformAdapter,
    MessageEvent,
    MessageType,
    SendResult,
)


LOG = logging.getLogger(__name__)
PLATFORM_NAME = "xiaozhi"
DEFAULT_WEBHOOK_PORT = 8645


def _xiaozhi_platform() -> Platform:
    try:
        return Platform(PLATFORM_NAME)
    except ValueError:
        if not platform_registry.is_registered(PLATFORM_NAME):
            platform_registry.register(
                PlatformEntry(
                    name=PLATFORM_NAME,
                    label="XiaoZhi",
                    adapter_factory=lambda cfg: None,
                    check_fn=lambda: True,
                    source="plugin",
                )
            )
        return Platform(PLATFORM_NAME)


class XiaozhiAdapter(BasePlatformAdapter):
    """Stage A skeleton for the XiaoZhi physical robot platform."""

    def __init__(self, config: PlatformConfig):
        super().__init__(config, _xiaozhi_platform())
        extra = config.extra or {}

        self.host = (
            os.getenv("XIAOZHI_WEBHOOK_HOST")
            or extra.get("host")
            or "127.0.0.1"
        )
        self.webhook_port = int(
            os.getenv(
                "XIAOZHI_WEBHOOK_PORT",
                str(
                    extra.get(
                        "webhook_port",
                        extra.get("port", DEFAULT_WEBHOOK_PORT),
                    )
                ),
            )
            or DEFAULT_WEBHOOK_PORT
        )
        self.webhook_secret = (
            os.getenv("XIAOZHI_WEBHOOK_SECRET")
            or extra.get("webhook_secret", "")
        )
        self.device_id = (
            os.getenv("XIAOZHI_DEVICE_ID")
            or extra.get("device_id", "")
        )
        self.mcp_adapter_url = (
            os.getenv("XIAOZHI_MCP_ADAPTER_URL")
            or extra.get("mcp_adapter_url", "")
        ).rstrip("/")
        self._runner: Optional[web.AppRunner] = None

    async def connect(self) -> bool:
        app = web.Application()
        app.router.add_post("/webhooks/xiaozhi-transcript", self._handle_transcript)

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.webhook_port)
        await site.start()
        server = getattr(site, "_server", None)
        sockets = getattr(server, "sockets", None)
        if sockets:
            self.webhook_port = int(sockets[0].getsockname()[1])
        self._mark_connected()
        LOG.info("XiaoZhi listener started on %s:%s", self.host, self.webhook_port)
        return True

    async def disconnect(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
        self._mark_disconnected()
        return None

    def _validate_signature(self, body: bytes, signature: str) -> bool:
        if not signature:
            return False
        expected = "sha256=" + hmac.new(
            self.webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    async def _handle_transcript(self, request: web.Request) -> web.Response:
        raw_body = await request.read()
        if not self.webhook_secret:
            return web.json_response(
                {"error": "Webhook route is missing an HMAC secret"},
                status=403,
            )

        signature = request.headers.get("X-Hub-Signature-256", "")
        if not self._validate_signature(raw_body, signature):
            return web.json_response({"error": "Invalid signature"}, status=401)

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return web.json_response({"error": "Cannot parse body"}, status=400)

        user_text = payload.get("user_text", payload.get("user", ""))
        assistant_text = payload.get(
            "assistant_text",
            payload.get("assistant", ""),
        )
        device_id = payload.get("device_id") or self.device_id
        device_id = str(device_id or "unknown")
        prompt = (
            f"XiaoZhi user said: {user_text}. "
            f"Assistant replied: {assistant_text}"
        )
        chat_id = f"xiaozhi:{device_id}"
        source = self.build_source(
            chat_id=chat_id,
            chat_name=f"XiaoZhi-{device_id}",
            chat_type="dm",
            user_id=device_id,
            user_name="XiaoZhi",
        )
        event = MessageEvent(
            text=prompt,
            message_type=MessageType.TEXT,
            source=source,
            raw_message=payload,
            message_id=request.headers.get("X-Request-ID"),
        )

        task = asyncio.create_task(self.handle_message(event))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        return web.json_response(
            {"status": "accepted", "chat_id": chat_id},
            status=202,
        )

    async def send(
        self,
        chat_id: str,
        content: str,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        del reply_to, metadata
        message_id = f"stub-{chat_id}"

        if not self.mcp_adapter_url:
            LOG.info("TODO M1 proxy not wired; stub send to %s: %s", chat_id, content)
            return SendResult(success=True, message_id=message_id)

        payload = {
            "device_id": chat_id,
            "text": content,
            "kind": "chat",
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.mcp_adapter_url}/tools/show_text",
                    json=payload,
                )
                response.raise_for_status()
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            LOG.warning("xiaozhi M1 sidecar unreachable: %s", exc)
            return SendResult(success=True, message_id=f"degraded-{chat_id}")

        return SendResult(success=True, message_id=f"sent-{chat_id}")

    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        return {"name": f"XiaoZhi-{chat_id}", "type": "dm"}


def register(ctx) -> None:
    ctx.register_platform(
        name=PLATFORM_NAME,
        label="XiaoZhi",
        adapter_factory=lambda cfg: XiaozhiAdapter(cfg),
        check_fn=lambda: True,
        required_env=["XIAOZHI_WEBHOOK_PORT", "XIAOZHI_WEBHOOK_SECRET"],
        install_hint="装 httpx (Hermes 自带)",
        emoji="🤖",
        max_message_length=4096,
        platform_hint=(
            "You are speaking through a physical desktop robot with a 240x240 "
            "LCD screen. Reply concisely (≤30 Chinese chars per chunk)."
        ),
    )


__all__ = [
    "MessageEvent",
    "MessageType",
    "XiaozhiAdapter",
    "register",
]
