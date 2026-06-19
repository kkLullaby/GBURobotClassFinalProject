"""Proxy helpers for ESP32 `self.otto.show_text` MCP calls."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Dict


MAX_TEXT_CHARS = 30
ALLOWED_KINDS = {"notification", "chat"}


def _normalize_text(text: str) -> str:
    if len(text) <= MAX_TEXT_CHARS:
        return text
    return text[: MAX_TEXT_CHARS - 3] + "..."


def _normalize_kind(kind: str) -> str:
    if kind in ALLOWED_KINDS:
        return kind
    return "notification"


def build_show_text_jsonrpc(
    device_id: str,
    text: str,
    kind: str = "notification",
) -> Dict[str, Any]:
    """Build a JSON-RPC tools/call payload for ESP32 show_text."""
    del device_id
    return {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "self.otto.show_text",
            "arguments": {
                "text": _normalize_text(text),
                "kind": _normalize_kind(kind),
            },
        },
        "id": uuid.uuid4().hex,
    }


async def call_show_text(
    pipe,
    device_id: str,
    text: str,
    kind: str = "notification",
) -> Dict[str, Any]:
    """Send a show_text JSON-RPC line through a stdio pipe and parse one reply."""
    if pipe is None:
        raise RuntimeError("xiaozhi MCP pipe is not configured")

    stdin = getattr(pipe, "stdin", None)
    stdout = getattr(pipe, "stdout", None)
    if stdin is None or stdout is None:
        raise RuntimeError("xiaozhi MCP pipe must expose stdin and stdout")

    payload = build_show_text_jsonrpc(device_id, text, kind)
    stdin.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    stdin.flush()

    loop = asyncio.get_running_loop()
    line = await loop.run_in_executor(None, stdout.readline)
    if line == "":
        raise RuntimeError("xiaozhi MCP pipe stdout closed")
    return json.loads(line)
