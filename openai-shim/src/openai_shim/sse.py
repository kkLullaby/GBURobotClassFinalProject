"""SSE helpers for OpenAI-compatible chat completion chunks."""

import time
import uuid
from typing import AsyncIterator, Tuple

from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta


async def _mark_last(chunks: AsyncIterator[str]) -> AsyncIterator[Tuple[str, bool]]:
    sentinel = object()
    previous = sentinel
    async for chunk in chunks:
        if previous is not sentinel:
            yield str(previous), False
        previous = chunk
    if previous is sentinel:
        yield "", True
    else:
        yield str(previous), True


def _chat_chunk(
    *,
    completion_id: str,
    created: int,
    model: str,
    content: str,
    is_last: bool,
) -> ChatCompletionChunk:
    return ChatCompletionChunk(
        id=completion_id,
        choices=[
            Choice(
                delta=ChoiceDelta(content=content),
                finish_reason="stop" if is_last else None,
                index=0,
            )
        ],
        created=created,
        model=model,
        object="chat.completion.chunk",
    )


async def chat_completion_sse(
    *,
    text_deltas: AsyncIterator[str],
    model: str,
) -> AsyncIterator[str]:
    completion_id = "chatcmpl-" + uuid.uuid4().hex
    created = int(time.time())

    async for content, is_last in _mark_last(text_deltas):
        chunk = _chat_chunk(
            completion_id=completion_id,
            created=created,
            model=model,
            content=content,
            is_last=is_last,
        )
        yield "data: " + chunk.model_dump_json() + "\n\n"

    yield "data: [DONE]\n\n"
