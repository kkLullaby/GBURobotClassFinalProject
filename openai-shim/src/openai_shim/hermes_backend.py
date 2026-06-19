"""Hermes transcript fork backend."""

import asyncio
import logging
import time
import uuid
from typing import Any, AsyncIterator, List, Optional, Set

import httpx

from .echo_backend import EchoBackend, TextBackend


LOG = logging.getLogger(__name__)


def _message_role(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("role", ""))
    return str(getattr(message, "role", ""))


def _message_content(message: Any) -> str:
    if isinstance(message, dict):
        content = message.get("content", "")
    else:
        content = getattr(message, "content", "")
    return content if isinstance(content, str) else ""


def _last_user_text(messages: List[Any]) -> str:
    for message in reversed(messages):
        if _message_role(message) == "user":
            return _message_content(message)
    return ""


class HermesBackend:
    """Wrap a text backend and fork completed transcripts to Hermes."""

    def __init__(
        self,
        inner: Optional[TextBackend] = None,
        transcript_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.inner = inner or EchoBackend()
        self.transcript_url = transcript_url
        self.http_client = http_client
        self._inflight_tasks: Set[asyncio.Task] = set()

    async def stream_response(
        self,
        messages: List[Any],
        model: str,
    ) -> AsyncIterator[str]:
        user_text = _last_user_text(messages)
        assistant_parts: List[str] = []

        async for delta in self.inner.stream_response(messages, model):
            assistant_parts.append(delta)
            yield delta

        if not self.transcript_url:
            return

        payload = {
            "user": user_text,
            "assistant": "".join(assistant_parts),
            "model": model,
            "session": "chatcmpl-" + uuid.uuid4().hex,
            "timestamp_unix": int(time.time()),
        }
        task = asyncio.create_task(self._post_transcript(payload))
        self._inflight_tasks.add(task)
        task.add_done_callback(self._inflight_tasks.discard)

    async def _post_transcript(self, payload: dict) -> None:
        try:
            if self.http_client is not None:
                response = await self.http_client.post(self.transcript_url, json=payload)
            else:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(self.transcript_url, json=payload)
            response.raise_for_status()
        except asyncio.CancelledError as exc:
            LOG.warning("Hermes transcript fork cancelled: %s", exc)
        except httpx.HTTPError as exc:
            LOG.warning("Hermes transcript fork failed: %s", exc)
        except Exception as exc:  # pragma: no cover - defensive fire-and-forget guard
            LOG.warning("Hermes transcript fork failed unexpectedly: %s", exc)
