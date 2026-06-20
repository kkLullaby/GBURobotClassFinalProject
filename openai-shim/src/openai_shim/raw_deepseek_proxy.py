"""Raw OpenAI-compat passthrough to DeepSeek — for requests carrying `tools` schema.

Why this exists (H035 root cause):
- DeepSeekBackend.stream_response() only extracts `content` text deltas; it
  drops `tools`/`tool_calls`/`tool_choice` on the way in and `tool_calls`
  on the way out.
- xinnan-tech server registers 14 ESP32 MCP tools (`self.otto.action`,
  `self.otto.show_emoji`, ...) into every LLM call's `tools=[...]`, and
  expects streaming `tool_calls` deltas back so it can dispatch motor moves.
- The text-only backend abstraction can't carry tool_calls without major
  re-engineering of `chat_completion_sse`. The pragmatic fix is to bypass
  the backend abstraction entirely for tool-bearing requests and do raw
  reverse-proxy SSE relay.

Implementation (revised 2026-06-20 after httpx TLS bug):
- Direct httpx async stream to DeepSeek raises `ConnectError('')` —
  conda env httpx 0.28.1 + DeepSeek TLS = SSL UNEXPECTED_EOF_WHILE_READING.
- Workaround: use openai SDK's `AsyncOpenAI.chat.completions.create(stream=True)`
  which works (verified). Then **re-serialize** each ChatCompletionChunk into
  OpenAI SSE wire format so xinnan-tech (which expects raw SSE) parses it.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from openai import AsyncOpenAI


LOG = logging.getLogger("openai_shim.raw_deepseek_proxy")


def _scrub_request(body: Dict[str, Any]) -> Dict[str, Any]:
    """Pass through OpenAI-compat fields openai SDK accepts."""
    keep = {
        "model", "messages", "stream", "tools", "tool_choice",
        "temperature", "top_p", "max_tokens", "n", "stop",
        "frequency_penalty", "presence_penalty", "seed",
        "response_format", "user",
    }
    return {k: v for k, v in body.items() if k in keep}


async def stream_raw_deepseek(
    *,
    api_key: str,
    base_url: str,
    body: bytes,
    timeout_s: float = 60.0,
    model_override: Optional[str] = None,
) -> AsyncIterator[bytes]:
    """Spawn a DeepSeek streaming chat completion, yield SSE bytes back."""
    try:
        body_dict = json.loads(body)
    except Exception as exc:
        LOG.error("invalid raw body for DeepSeek proxy: %s", exc)
        yield b"data: {\"error\":\"invalid_body\"}\n\n"
        yield b"data: [DONE]\n\n"
        return

    payload = _scrub_request(body_dict)
    if model_override:
        payload["model"] = model_override
    payload["stream"] = True

    LOG.info(
        "DeepSeek raw proxy: model=%s tools=%d msgs=%d",
        payload.get("model"),
        len(payload.get("tools") or []),
        len(payload.get("messages") or []),
    )

    client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout_s)

    try:
        stream = await client.chat.completions.create(**payload)
    except Exception as exc:
        LOG.error("DeepSeek raw proxy create error: %s %r", type(exc).__name__, exc)
        yield (
            b"data: {\"error\":\"deepseek_upstream\",\"detail\":"
            + json.dumps(str(exc)).encode()
            + b"}\n\n"
        )
        yield b"data: [DONE]\n\n"
        return

    chunk_count = 0
    tool_calls_seen = False
    try:
        async for chunk in stream:
            # ChatCompletionChunk.model_dump_json() emits the exact OpenAI wire format
            chunk_json = chunk.model_dump_json()
            yield b"data: " + chunk_json.encode() + b"\n\n"
            chunk_count += 1
            # Detect tool_calls in delta for logging
            if not tool_calls_seen:
                for choice in chunk.choices or []:
                    if choice.delta and getattr(choice.delta, "tool_calls", None):
                        tool_calls_seen = True
                        break
        yield b"data: [DONE]\n\n"
        LOG.info(
            "DeepSeek raw proxy: %d chunks streamed, tool_calls=%s",
            chunk_count, tool_calls_seen,
        )
    except Exception as exc:
        LOG.exception("DeepSeek raw proxy stream interrupted")
        yield (
            b"data: {\"error\":\"deepseek_stream_interrupted\",\"detail\":"
            + json.dumps(str(exc)).encode()
            + b"}\n\n"
        )
        yield b"data: [DONE]\n\n"
    finally:
        try:
            await client.close()
        except Exception:
            pass
