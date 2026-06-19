"""FastAPI app for the H018 OpenAI-compatible shim spike."""

import os
from typing import List, Optional

from fastapi import Depends, FastAPI, Header
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict

from .deepseek_backend import DeepSeekBackend
from .echo_backend import EchoBackend, TextBackend
from .hermes_backend import HermesBackend
from .sse import chat_completion_sse


class ChatMessage(BaseModel):
    # 允许 tool_calls / tool_call_id / name / function_call 等 OpenAI 完整字段
    # (H022 实测发现 xinnan-tech 会发 role=tool 的 message 带 tool_call_id)
    model_config = ConfigDict(extra="allow")
    role: str
    content: Optional[object] = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str
    messages: List[ChatMessage]
    stream: bool = False


app = FastAPI(title="openai-shim")


def _build_backend() -> TextBackend:
    backend_kind = os.environ.get("OPENAI_SHIM_BACKEND", "echo").lower()
    if backend_kind == "deepseek":
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY required when OPENAI_SHIM_BACKEND=deepseek"
            )
        inner = DeepSeekBackend(
            api_key=api_key,
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
    else:
        inner = EchoBackend()

    transcript_url = os.environ.get("HERMES_TRANSCRIPT_URL")
    if transcript_url:
        return HermesBackend(inner, transcript_url)
    return inner


_backend: TextBackend = _build_backend()


async def get_backend() -> TextBackend:
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
