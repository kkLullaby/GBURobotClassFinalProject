"""FastAPI app for the H018 OpenAI-compatible shim spike."""

from typing import List, Optional

from fastapi import Depends, FastAPI, Header
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from .echo_backend import EchoBackend, TextBackend
from .sse import chat_completion_sse


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False


app = FastAPI(title="openai-shim")
_backend: TextBackend = EchoBackend()


def get_backend() -> TextBackend:
    return _backend


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    authorization: Optional[str] = Header(default=None),
    backend: TextBackend = Depends(get_backend),
):
    del authorization
    if not request.stream:
        return JSONResponse(
            status_code=503,
            content={"error": "non-streaming unsupported in spike"},
        )

    text_deltas = backend.stream_response(request.messages, request.model)
    return StreamingResponse(
        chat_completion_sse(text_deltas=text_deltas, model=request.model),
        media_type="text/event-stream",
    )
