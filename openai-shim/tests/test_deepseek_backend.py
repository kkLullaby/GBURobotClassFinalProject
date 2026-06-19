import asyncio
import json

import httpx
import openai
import pytest
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

from openai_shim.app import _build_backend
from openai_shim.deepseek_backend import DeepSeekBackend
from openai_shim.echo_backend import EchoBackend
from openai_shim.hermes_backend import HermesBackend


def _sse_chunk(content, model="deepseek-chat"):
    return {
        "id": "chatcmpl-fake",
        "object": "chat.completion.chunk",
        "created": 1781870000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content},
                "finish_reason": None,
            }
        ],
    }


def _sse_stop(model="deepseek-chat"):
    return {
        "id": "chatcmpl-fake",
        "object": "chat.completion.chunk",
        "created": 1781870000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
    }


async def _fake_deepseek_stream(parts, model="deepseek-chat"):
    for part in parts:
        yield "data: " + json.dumps(_sse_chunk(part, model=model)) + "\n\n"
    yield "data: " + json.dumps(_sse_stop(model=model)) + "\n\n"
    yield "data: [DONE]\n\n"


def _deepseek_backend(http_client, base_url="http://fake-deepseek"):
    backend = DeepSeekBackend(
        api_key="sk-fake",
        base_url=base_url,
        http_client=http_client,
    )
    # Avoid OpenAI SDK platform probing through a threadpool in sandboxed tests.
    backend.client._platform = "Linux"
    backend.client.max_retries = 0
    return backend


async def _collect_backend(backend, content="hello"):
    return [
        delta
        async for delta in backend.stream_response(
            [{"role": "user", "content": content}],
            "deepseek-chat",
        )
    ]


async def _wait_for_inflight(backend):
    if backend._inflight_tasks:
        await asyncio.gather(*list(backend._inflight_tasks), return_exceptions=True)


async def _close_deepseek_client(backend):
    inner = backend.inner if isinstance(backend, HermesBackend) else backend
    if isinstance(inner, DeepSeekBackend):
        await inner.client.close()


@pytest.mark.asyncio
async def test_deepseek_backend_yields_real_stream_chunks():
    received = []
    parts = ["Deep", "Seek", " ok"]
    fake_deepseek = FastAPI()

    @fake_deepseek.post("/chat/completions")
    async def chat_completions(request: Request):
        received.append(await request.json())
        return StreamingResponse(
            _fake_deepseek_stream(parts),
            media_type="text/event-stream",
        )

    deepseek_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fake_deepseek),
        base_url="http://fake-deepseek",
    )
    backend = _deepseek_backend(deepseek_client)
    async with deepseek_client:
        deltas = await _collect_backend(backend)

    assert deltas == parts
    assert "".join(deltas) == "DeepSeek ok"
    assert received[0]["model"] == "deepseek-chat"
    assert received[0]["messages"] == [{"role": "user", "content": "hello"}]


@pytest.mark.asyncio
async def test_hermes_wraps_deepseek_forks_real_assistant_text():
    parts = ["real ", "assistant"]
    received = []
    fake_deepseek = FastAPI()
    fake_hermes = FastAPI()

    @fake_deepseek.post("/chat/completions")
    async def chat_completions():
        return StreamingResponse(
            _fake_deepseek_stream(parts),
            media_type="text/event-stream",
        )

    @fake_hermes.post("/webhooks/xiaozhi-transcript")
    async def receive_transcript(request: Request):
        received.append(await request.json())
        return {"ok": True}

    deepseek_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fake_deepseek),
        base_url="http://fake-deepseek",
    )
    hermes_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fake_hermes),
        base_url="http://fake-hermes",
    )
    deepseek = _deepseek_backend(deepseek_client)
    backend = HermesBackend(
        deepseek,
        "http://fake-hermes/webhooks/xiaozhi-transcript",
        hermes_client,
    )

    async with deepseek_client, hermes_client:
        deltas = await _collect_backend(backend, content="hi")
        await _wait_for_inflight(backend)

    assert "".join(deltas) == "real assistant"
    assert len(received) == 1
    assert received[0]["user"] == "hi"
    assert received[0]["assistant"] == "real assistant"
    assert received[0]["assistant"] != "echoed: hi"


@pytest.mark.asyncio
async def test_build_backend_with_env_matrix(monkeypatch):
    for key in (
        "OPENAI_SHIM_BACKEND",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "HERMES_TRANSCRIPT_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    backend = _build_backend()
    assert isinstance(backend, EchoBackend)

    monkeypatch.setenv("OPENAI_SHIM_BACKEND", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake")
    backend = _build_backend()
    try:
        assert isinstance(backend, DeepSeekBackend)
    finally:
        await _close_deepseek_client(backend)

    monkeypatch.setenv("HERMES_TRANSCRIPT_URL", "http://fake-hermes/webhooks/x")
    backend = _build_backend()
    try:
        assert isinstance(backend, HermesBackend)
        assert isinstance(backend.inner, DeepSeekBackend)
    finally:
        await _close_deepseek_client(backend)

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        _build_backend()
    assert str(exc_info.value) == (
        "DEEPSEEK_API_KEY required when OPENAI_SHIM_BACKEND=deepseek"
    )


@pytest.mark.asyncio
async def test_deepseek_api_error_propagates():
    fake_deepseek = FastAPI()

    @fake_deepseek.post("/chat/completions")
    async def chat_completions():
        return Response(status_code=500, content='{"error":"boom"}')

    deepseek_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fake_deepseek),
        base_url="http://fake-deepseek",
    )
    backend = _deepseek_backend(deepseek_client)

    async with deepseek_client:
        with pytest.raises(openai.APIError):
            await _collect_backend(backend)
