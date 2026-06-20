"""Handle one inbound Lark `im.message.receive_v1` event.

1. Filter out the bot's own messages (would otherwise loop forever, since
   `lark_send_message_to_self` posts to the same private chat the bot is
   listening on).
2. Filter out chat_type != "p2p" (skip group chats this round — out of scope).
3. Parse the message text. Only message_type=="text" is supported MVP;
   stickers/cards/images logged and ignored.
4. Build a prompt that instructs hermes to call `lark_send_message_to_self`
   to reply.
5. Spawn `hermes -z <prompt> --yolo --accept-hooks` exactly the way
   `openai_shim.hermes_agent_backend` does. Capture stdout/stderr; log both.

Idempotency: the LRU dedup of `message_id` lives in the listener client
(handler-level state) so retries of the same event from feishu reconnects
don't double-spawn.
"""

from __future__ import annotations

import asyncio
import collections
import json
import logging
import os
import shlex
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from lark_oapi.api.im.v1.model.p2_im_message_receive_v1 import P2ImMessageReceiveV1


LOG = logging.getLogger("lark_event_listener.handler")

DEFAULT_HERMES_BIN = os.environ.get("HERMES_BIN", "hermes")
DEFAULT_TIMEOUT_S = float(os.environ.get("LARK_LISTENER_HERMES_TIMEOUT_S", "180"))
DEFAULT_DEDUP_LRU = int(os.environ.get("LARK_LISTENER_DEDUP_LRU", "256"))


def _extract_text(message_type: str, content_json: str) -> Optional[str]:
    """Lark wraps message body as JSON string. Pull out plain text for type=text."""
    if message_type != "text":
        return None
    try:
        content = json.loads(content_json or "{}")
    except json.JSONDecodeError:
        LOG.warning("non-JSON content payload: %r", content_json[:200])
        return None
    text = content.get("text")
    if not text:
        return None
    return str(text).strip() or None


def _build_prompt(user_text: str, sender_open_id: str) -> str:
    """The prompt fed to hermes.

    Critical: instruct hermes to USE the lark_send_message_to_self tool to
    reply — otherwise hermes just prints to stdout and the user never sees it
    on 飞书. We do NOT want hermes to wax-lyrical to stdout for 90s; one
    succinct tool call is the whole job.
    """
    return (
        f"用户在飞书私聊里给你 (ottagent 机器人) 发了一条消息:\n"
        f"\n"
        f"  「{user_text}」\n"
        f"\n"
        f"请用最多 80 个汉字、纯口语、无 markdown 的方式拟一句回复,"
        f"然后**必须**调用 `lark_send_message_to_self` 工具,"
        f"把这句回复发回给该用户。不要在终端 stdout 多说别的,只调一次工具。"
    )


class EventDeduplicator:
    """Cheap LRU set on message_id to swallow retransmits."""

    def __init__(self, capacity: int = DEFAULT_DEDUP_LRU) -> None:
        self._seen: "collections.OrderedDict[str, None]" = collections.OrderedDict()
        self._capacity = capacity

    def seen(self, message_id: str) -> bool:
        if not message_id:
            return False
        if message_id in self._seen:
            self._seen.move_to_end(message_id)
            return True
        self._seen[message_id] = None
        if len(self._seen) > self._capacity:
            self._seen.popitem(last=False)
        return False


def _hermes_env() -> dict:
    """Build env for hermes subprocess.

    Listener itself runs with proxy unset (feishu must direct, fake-ip pool
    will eat it otherwise — bitter lesson #45). But hermes calls DeepSeek
    which lives on `api.deepseek.com`, also in the fake-ip pool when clash
    is on. So we re-inject proxy here, but with `NO_PROXY=feishu` so any
    feishu calls hermes spawn (via lark tool subprocess) still go direct.

    Override via env: HERMES_SPAWN_PROXY=socks5://127.0.0.1:7897 (default),
    HERMES_SPAWN_NO_PROXY=open.feishu.cn,open.larksuite.com (default).
    Set HERMES_SPAWN_PROXY='' to disable injection.
    """
    proxy = os.environ.get("HERMES_SPAWN_PROXY", "socks5://127.0.0.1:7897")
    no_proxy = os.environ.get(
        "HERMES_SPAWN_NO_PROXY",
        "localhost,127.0.0.1,open.feishu.cn,open.larksuite.com",
    )
    env = {**os.environ}
    if proxy:
        # http(s)_proxy may stay scheme=http even with socks upstream because
        # most clients route via proxychains-style; mirror what start_shim.sh
        # does to be safe.
        env["ALL_PROXY"] = proxy
        env["all_proxy"] = proxy
        env["HTTPS_PROXY"] = proxy if proxy.startswith("http") else "http://127.0.0.1:7897"
        env["HTTP_PROXY"] = env["HTTPS_PROXY"]
        env["https_proxy"] = env["HTTPS_PROXY"]
        env["http_proxy"] = env["HTTPS_PROXY"]
        env["NO_PROXY"] = no_proxy
        env["no_proxy"] = no_proxy
    return env


async def spawn_hermes(prompt: str, *, timeout_s: float = DEFAULT_TIMEOUT_S) -> tuple[int, str, str]:
    """Spawn `hermes -z PROMPT --yolo --accept-hooks`, capture all output.

    Returns (returncode, stdout, stderr). Pattern mirrors
    `openai_shim.hermes_agent_backend.HermesAgentBackend.stream_response`,
    plus re-injects proxy for DeepSeek (bitter lesson #51, see ADR-0009).
    """
    cmd = [DEFAULT_HERMES_BIN, "-z", prompt, "--yolo", "--accept-hooks"]
    LOG.info("spawn hermes: %s ...", shlex.join(cmd[:3]))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_hermes_env(),
    )
    try:
        out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except asyncio.TimeoutError:
        LOG.warning("hermes timeout after %.0fs; killing", timeout_s)
        proc.kill()
        await proc.wait()
        return -1, "", f"(timeout {timeout_s:.0f}s)"

    return (
        proc.returncode if proc.returncode is not None else -1,
        (out_b or b"").decode("utf-8", errors="replace"),
        (err_b or b"").decode("utf-8", errors="replace"),
    )


class MessageHandler:
    """Per-listener handler bundling dedup, sender filter, and hermes spawn."""

    def __init__(
        self,
        bot_open_id: Optional[str] = None,
        dedup: Optional[EventDeduplicator] = None,
        spawner=spawn_hermes,
    ) -> None:
        # bot_open_id is the open_id assigned to THIS app, used as the most
        # reliable "did I send this myself" filter. May be None at construction
        # time — the listener can backfill once it sees a sender_type=="app"
        # event with the app's own id (best effort).
        self.bot_open_id = bot_open_id
        self.dedup = dedup or EventDeduplicator()
        self._spawner = spawner

    def _should_skip(self, event: "P2ImMessageReceiveV1") -> Optional[str]:
        """Return None to process, else a string reason to skip (logged)."""
        data = event.event
        if data is None:
            return "no event.data"
        message = data.message
        sender = data.sender
        if message is None or sender is None:
            return "missing message or sender"

        if message.message_id and self.dedup.seen(message.message_id):
            return f"dup message_id={message.message_id}"

        # Chat-type gate: only p2p (private chat) this round.
        if message.chat_type and message.chat_type != "p2p":
            return f"non-p2p chat_type={message.chat_type}"

        # Sender filter — defense-in-depth:
        # (a) sender_type == "app" means a bot/app sent it (including ourselves)
        # (b) sender.sender_id.open_id == our bot's open_id
        if sender.sender_type and sender.sender_type.lower() == "app":
            return f"sender_type=app open_id={getattr(sender.sender_id, 'open_id', None)}"
        if (
            self.bot_open_id
            and sender.sender_id
            and sender.sender_id.open_id == self.bot_open_id
        ):
            return f"sender is bot itself open_id={self.bot_open_id}"

        if message.message_type != "text":
            return f"unsupported message_type={message.message_type}"
        return None

    async def handle(self, event: "P2ImMessageReceiveV1") -> None:
        skip = self._should_skip(event)
        if skip:
            LOG.info("skip event: %s", skip)
            return

        message = event.event.message
        sender = event.event.sender
        sender_open_id = (
            sender.sender_id.open_id if sender and sender.sender_id else "unknown"
        )

        text = _extract_text(message.message_type or "", message.content or "")
        if not text:
            LOG.info("skip empty text content for message_id=%s", message.message_id)
            return

        LOG.info(
            "received from %s (chat=%s msg_id=%s): %s",
            sender_open_id,
            message.chat_id,
            message.message_id,
            text[:200],
        )

        prompt = _build_prompt(text, sender_open_id)
        rc, out, err = await self._spawner(prompt)
        if rc != 0:
            LOG.error(
                "hermes exit=%s stderr=%r stdout=%r",
                rc,
                err[:400],
                out[:400],
            )
        else:
            LOG.info("hermes done (rc=0). stdout_head=%r", out[:200])
