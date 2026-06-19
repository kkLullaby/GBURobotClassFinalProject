"""DeepSeek streaming backend for the OpenAI-compatible shim."""

from typing import Any, AsyncIterator, List, Optional

import httpx
from openai import AsyncOpenAI


def _message_payload(message: Any) -> dict:
    """把 pydantic ChatMessage / dict 透传为完整 OpenAI message dict。

    H022 实测发现: xinnan-tech server 在多轮 tool calling 后会发 role=tool 的
    message, 必须保留 tool_call_id / tool_calls / name / function_call 等
    OpenAI 兼容字段, 否则 DeepSeek 400. 用 .model_dump(exclude_none=True)
    把 pydantic ChatMessage (extra=allow) 完整序列化, 字典则原样透传。
    """
    if isinstance(message, dict):
        # 已经是 dict, 滤掉 None 字段
        return {k: v for k, v in message.items() if v is not None}
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)
    # 兜底: 至少 role+content
    return {
        "role": str(getattr(message, "role", "")),
        "content": getattr(message, "content", ""),
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
