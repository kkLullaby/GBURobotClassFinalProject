"""DeepSeek streaming backend for the OpenAI-compatible shim."""

from typing import Any, AsyncIterator, List, Optional

import httpx
from openai import AsyncOpenAI


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


def _message_payload(message: Any) -> dict:
    return {
        "role": _message_role(message),
        "content": _message_content(message),
    }


class DeepSeekBackend:
    """Proxy text deltas from DeepSeek's OpenAI-compatible streaming API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model_override: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.model_override = model_override
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client,
        )

    async def stream_response(
        self,
        messages: List[Any],
        model: str,
    ) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model_override or model,
            messages=[_message_payload(message) for message in messages],
            stream=True,
        )

        async for chunk in stream:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            if content:
                yield content
