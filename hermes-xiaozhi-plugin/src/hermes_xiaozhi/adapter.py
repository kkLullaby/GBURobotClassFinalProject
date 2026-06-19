"""XiaoZhi platform adapter for Hermes Agent."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

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

        self.webhook_port = int(
            os.getenv(
                "XIAOZHI_WEBHOOK_PORT",
                str(extra.get("webhook_port", DEFAULT_WEBHOOK_PORT)),
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

    async def connect(self) -> bool:
        # TODO(H028.bis): start the signed webhook listener on webhook_port.
        return True

    async def disconnect(self) -> None:
        return None

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
                await client.post(
                    f"{self.mcp_adapter_url}/tools/show_text",
                    json=payload,
                )
        except Exception as exc:  # pragma: no cover - defensive Stage A stub
            LOG.warning("XiaoZhi M1 proxy send failed: %s", exc)

        return SendResult(success=True, message_id=message_id)

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
