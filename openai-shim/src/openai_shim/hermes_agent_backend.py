"""Hermes-as-LLM backend: voice prompt → `hermes -z` subprocess → stream stdout back to xinnan-tech.

Unlike `HermesBackend` (which forks transcripts to the plugin webhook one-way),
this backend MAKES Hermes the LLM. The speaker reads whatever Hermes' agent
loop produces — including tool-call results (shell, browser, filesystem) — so
the user can voice-drive Hermes from the robot.

Flow:
  ESP32 voice → STT → xinnan-tech LLM call → openai-shim ← HermesAgentBackend
                                                              ↓
                                                       `hermes -z PROMPT`
                                                              ↓ (tool calls inside hermes)
                                                       full text reply
                                                              ↓
                                                       chunked SSE deltas
                                                              ↓
                                              xinnan-tech TTS → robot speaker

Tradeoffs:
- Wall-clock 5-30s (vs DeepSeek direct 2-4s); ESP32 client must tolerate.
- Hermes session is per-call (no convo memory across voice turns yet);
  use `--continue` in a later iteration to thread sessions by chat_id.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
from typing import Any, AsyncIterator, List

from .echo_backend import _chunk_text, _message_content, _message_role


LOG = logging.getLogger("openai_shim.hermes_agent_backend")

DEFAULT_HERMES_BIN = os.environ.get("HERMES_BIN", "hermes")
DEFAULT_TIMEOUT_S = float(os.environ.get("HERMES_AGENT_TIMEOUT_S", "60"))
DEFAULT_CHUNK_SIZE = int(os.environ.get("HERMES_AGENT_CHUNK_SIZE", "20"))


def _last_user_text(messages: List[Any]) -> str:
    for message in reversed(messages):
        if _message_role(message) == "user":
            return _message_content(message)
    return ""


class HermesAgentBackend:
    """Run `hermes -z PROMPT` per request and stream the reply as text deltas."""

    def __init__(
        self,
        hermes_bin: str = DEFAULT_HERMES_BIN,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        extra_args: List[str] | None = None,
    ) -> None:
        self.hermes_bin = hermes_bin
        self.timeout_s = timeout_s
        self.chunk_size = chunk_size
        # 默认 --yolo: 跳 destructive 确认 (voice 模式不能交互)
        # 默认 --accept-hooks: 自动接受未见过的 hook
        self.extra_args = extra_args or ["--yolo", "--accept-hooks"]

    async def stream_response(
        self,
        messages: List[Any],
        model: str,
    ) -> AsyncIterator[str]:
        del model
        prompt = _last_user_text(messages).strip()
        if not prompt:
            yield "(无 prompt)"
            return

        # 让 hermes 简洁回答 (TTS 不读长 markdown)
        wrapped = (
            "用最多 80 个汉字、纯口语、无 markdown 回答下面这个问题；"
            "如果需要工具就直接用，但最终输出只给口语化总结：\n\n"
            + prompt
        )

        cmd = [self.hermes_bin, "-z", wrapped, *self.extra_args]
        LOG.info("spawning hermes oneshot: %s", shlex.join(cmd[:3]) + " ...")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ},
            )
        except FileNotFoundError as exc:
            LOG.error("hermes binary not found: %s", exc)
            yield f"(hermes not found: {exc})"
            return

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout_s
            )
        except asyncio.TimeoutError:
            LOG.warning("hermes oneshot timeout after %.1fs", self.timeout_s)
            proc.kill()
            await proc.wait()
            yield f"(超时 {self.timeout_s:.0f}s)"
            return

        text = (stdout_bytes or b"").decode("utf-8", errors="replace").strip()

        if proc.returncode != 0:
            stderr = (stderr_bytes or b"").decode("utf-8", errors="replace")
            LOG.error(
                "hermes exit=%s stderr=%r stdout=%r",
                proc.returncode,
                stderr[:500],
                text[:200],
            )
            # 兜底：还是把 stdout 流出去 (可能有部分内容)
            if not text:
                yield f"(hermes 失败: exit={proc.returncode})"
                return

        if not text:
            yield "(hermes 无输出)"
            return

        for chunk in _chunk_text(text, size=self.chunk_size):
            yield chunk
