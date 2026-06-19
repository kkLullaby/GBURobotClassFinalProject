import pytest
import httpx
from openai import APIStatusError, AsyncOpenAI

from openai_shim.app import app


def _openai_client(http_client):
    client = AsyncOpenAI(
        api_key="sk-fake",
        base_url="http://testserver/v1",
        http_client=http_client,
    )
    # Avoid OpenAI SDK platform probing through a threadpool in sandboxed tests.
    client._platform = "Linux"
    return client


@pytest.mark.asyncio
async def test_streaming_echo_roundtrip():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as http_client:
        client = _openai_client(http_client)

        stream = await client.chat.completions.create(
            model="echo",
            messages=[{"role": "user", "content": "hi"}],
            stream=True,
        )

        content = []
        finish_reason = None
        async for chunk in stream:
            choice = chunk.choices[0]
            if choice.delta.content:
                content.append(choice.delta.content)
            if choice.finish_reason:
                finish_reason = choice.finish_reason

        assert "".join(content) == "echoed: hi"
        assert finish_reason == "stop"


@pytest.mark.asyncio
async def test_non_streaming_returns_503():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as http_client:
        client = _openai_client(http_client)

        with pytest.raises(APIStatusError) as exc_info:
            await client.chat.completions.create(
                model="echo",
                messages=[{"role": "user", "content": "hi"}],
                stream=False,
            )

        assert exc_info.value.status_code == 503
        assert exc_info.value.response.json() == {
            "error": "non-streaming unsupported in spike"
        }
