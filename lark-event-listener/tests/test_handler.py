"""Verify the dedup/filter/spawn pipeline without booting the real ws client."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import List

import pytest

from lark_event_listener.handler import (
    EventDeduplicator,
    MessageHandler,
    _build_prompt,
    _extract_text,
)


def _make_event(
    *,
    message_id: str = "om_test_1",
    chat_type: str = "p2p",
    message_type: str = "text",
    text: str = "你好 ottagent",
    sender_type: str = "user",
    sender_open_id: str = "ou_user_external",
):
    """Mimic the P2ImMessageReceiveV1 attribute tree the SDK passes."""
    content = json.dumps({"text": text})
    return SimpleNamespace(
        event=SimpleNamespace(
            sender=SimpleNamespace(
                sender_type=sender_type,
                sender_id=SimpleNamespace(open_id=sender_open_id, user_id=None, union_id=None),
                tenant_key="tk",
            ),
            message=SimpleNamespace(
                message_id=message_id,
                chat_id="oc_test_chat",
                chat_type=chat_type,
                message_type=message_type,
                content=content,
                root_id=None,
                parent_id=None,
                thread_id=None,
            ),
        )
    )


class _FakeSpawner:
    def __init__(self, rc: int = 0, out: str = "OK", err: str = ""):
        self.rc = rc
        self.out = out
        self.err = err
        self.calls: List[str] = []

    async def __call__(self, prompt: str, *, timeout_s: float = 5.0):
        self.calls.append(prompt)
        return self.rc, self.out, self.err


def test_extract_text_strips_and_returns():
    assert _extract_text("text", json.dumps({"text": "  hi  "})) == "hi"


def test_extract_text_non_text_returns_none():
    assert _extract_text("image", json.dumps({"image_key": "k"})) is None


def test_extract_text_bad_json_returns_none():
    assert _extract_text("text", "{not json") is None


def test_build_prompt_contains_user_text_and_tool_name():
    p = _build_prompt("你好", "ou_xxx")
    assert "你好" in p
    assert "lark_send_message_to_self" in p


def test_dedup_blocks_repeats():
    d = EventDeduplicator(capacity=4)
    assert d.seen("a") is False
    assert d.seen("a") is True
    assert d.seen("b") is False
    assert d.seen("b") is True


def test_dedup_lru_evicts():
    d = EventDeduplicator(capacity=2)
    d.seen("a")
    d.seen("b")
    d.seen("c")   # evicts "a"
    assert d.seen("a") is False  # re-admitted after eviction


@pytest.mark.asyncio
async def test_handle_text_message_spawns_hermes_with_user_text():
    spawner = _FakeSpawner()
    h = MessageHandler(spawner=spawner)
    await h.handle(_make_event(text="今天天气怎么样"))
    assert len(spawner.calls) == 1
    assert "今天天气怎么样" in spawner.calls[0]
    assert "lark_send_message_to_self" in spawner.calls[0]


@pytest.mark.asyncio
async def test_handle_skips_bot_self_by_sender_type_app():
    spawner = _FakeSpawner()
    h = MessageHandler(spawner=spawner)
    await h.handle(_make_event(sender_type="app"))
    assert spawner.calls == []


@pytest.mark.asyncio
async def test_handle_skips_bot_self_by_open_id():
    spawner = _FakeSpawner()
    h = MessageHandler(bot_open_id="ou_bot_self", spawner=spawner)
    await h.handle(_make_event(sender_open_id="ou_bot_self"))
    assert spawner.calls == []


@pytest.mark.asyncio
async def test_handle_skips_group_chats():
    spawner = _FakeSpawner()
    h = MessageHandler(spawner=spawner)
    await h.handle(_make_event(chat_type="group"))
    assert spawner.calls == []


@pytest.mark.asyncio
async def test_handle_skips_non_text():
    spawner = _FakeSpawner()
    h = MessageHandler(spawner=spawner)
    await h.handle(_make_event(message_type="image"))
    assert spawner.calls == []


@pytest.mark.asyncio
async def test_handle_dedups_repeat_message_id():
    spawner = _FakeSpawner()
    h = MessageHandler(spawner=spawner)
    await h.handle(_make_event(message_id="om_dup"))
    await h.handle(_make_event(message_id="om_dup"))
    assert len(spawner.calls) == 1


@pytest.mark.asyncio
async def test_handle_logs_hermes_failure_but_does_not_raise(caplog):
    spawner = _FakeSpawner(rc=1, out="", err="oops")
    h = MessageHandler(spawner=spawner)
    with caplog.at_level("ERROR"):
        await h.handle(_make_event())
    assert any("exit=1" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_handle_skips_empty_text_payload():
    spawner = _FakeSpawner()
    h = MessageHandler(spawner=spawner)
    await h.handle(_make_event(text="   "))
    assert spawner.calls == []
