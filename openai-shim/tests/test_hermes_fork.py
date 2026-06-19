import asyncio

import httpx
import pytest
from fastapi import FastAPI, Request, Response
from openai import AsyncOpenAI

from openai_shim.app import app, get_backend
from openai_shim.echo_backend import EchoBackend
from openai_shim.hermes_backend import HermesBackend


def _openai_client(http_client):
    client = AsyncOpenAI(
        api_key="sk-fake",
        base_url="http://testserver/v1",
        http_client=http_client,
    )
    # Avoid OpenAI SDK platform probing through a threadpool in sandboxed tests.
    client._platform = "Linux"
    return client


def _override_backend(backend):
    async def override():
        return backend

    return override


async def _collect_stream(client):
    stream = await client.chat.completions.create(
        model="echo",
        messages=[{"role": "user", "content": "hi"}],
        stream=True,
    )

    content = []
    async for chunk in stream:
        choice = chunk.choices[0]
        if choice.delta.content:
            content.append(choice.delta.content)
    return "".join(content)


async def _wait_for_inflight(backend):
    if backend._inflight_tasks:
        await asyncio.gather(*list(backend._inflight_tasks), return_exceptions=True)


@pytest.mark.asyncio
async def test_transcript_posted_when_hermes_url_set():
    received = []
    fake_hermes = FastAPI()

    @fake_hermes.post("/webhooks/xiaozhi-transcript")
    async def receive_transcript(request: Request):
        received.append(await request.json())
        return {"ok": True}

    hermes_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fake_hermes),
        base_url="http://fake-hermes",
    )
    backend = HermesBackend(
        EchoBackend(),
        "http://fake-hermes/webhooks/xiaozhi-transcript",
        hermes_client,
    )
    app.dependency_overrides[get_backend] = _override_backend(backend)
    try:
        async with hermes_client:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as http_client:
                content = await _collect_stream(_openai_client(http_client))

            await _wait_for_inflight(backend)
    finally:
        app.dependency_overrides.clear()

    assert content == "echoed: hi"
    assert len(received) == 1
    body = received[0]
    assert body["user"] == "hi"
    assert body["assistant"] == "echoed: hi"
    assert body["model"] == "echo"
    assert body["session"].startswith("chatcmpl-")
    assert isinstance(body["timestamp_unix"], int)


@pytest.mark.asyncio
async def test_sse_still_works_when_hermes_returns_500():
    fake_hermes = FastAPI()

    @fake_hermes.post("/webhooks/xiaozhi-transcript")
    async def receive_transcript():
        return Response(status_code=500)

    hermes_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fake_hermes),
        base_url="http://fake-hermes",
    )
    backend = HermesBackend(
        EchoBackend(),
        "http://fake-hermes/webhooks/xiaozhi-transcript",
        hermes_client,
    )
    app.dependency_overrides[get_backend] = _override_backend(backend)
    try:
        async with hermes_client:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as http_client:
                content = await _collect_stream(_openai_client(http_client))

            await _wait_for_inflight(backend)
    finally:
        app.dependency_overrides.clear()

    assert content == "echoed: hi"


@pytest.mark.asyncio
async def test_no_fork_when_hermes_url_unset(monkeypatch):
    monkeypatch.delenv("HERMES_TRANSCRIPT_URL", raising=False)
    backend = EchoBackend()
    app.dependency_overrides[get_backend] = _override_backend(backend)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as http_client:
            content = await _collect_stream(_openai_client(http_client))
    finally:
        app.dependency_overrides.clear()

    assert content == "echoed: hi"
