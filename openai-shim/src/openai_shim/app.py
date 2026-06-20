"""FastAPI app for the H018 OpenAI-compatible shim spike.

H035 update: when OPENAI_SHIM_BACKEND=hybrid (recommended for full demo),
incoming requests are routed via `router.should_route_raw_deepseek()`:
- motor intent → raw passthrough to DeepSeek with tools (舵机能动)
- everything else → HermesAgentBackend (voice→hermes-z→tool→喇叭真说)
"""

import json
import logging
import os
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict

from .deepseek_backend import DeepSeekBackend
from .echo_backend import EchoBackend, TextBackend
from .hermes_agent_backend import HermesAgentBackend
from .hermes_backend import HermesBackend
from .raw_deepseek_proxy import stream_raw_deepseek
from .router import should_route_raw_deepseek
from .sse import chat_completion_sse


LOG = logging.getLogger("openai_shim.app")


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
    elif backend_kind == "hermes_agent":
        # voice → hermes -z → tool calls → speak result
        # (HermesBackend transcript fork still applies on top if HERMES_TRANSCRIPT_URL set)
        inner = HermesAgentBackend()
    elif backend_kind == "hybrid":
        # H035: motor intent → raw deepseek (舵机能动); 其余 → hermes-z (tool-call)
        # 实际 raw deepseek 路径在 endpoint 里短路，inner 只服务非 motor 路径。
        inner = HermesAgentBackend()
    else:
        inner = EchoBackend()

    transcript_url = os.environ.get("HERMES_TRANSCRIPT_URL")
    if transcript_url:
        webhook_secret = os.environ.get("HERMES_WEBHOOK_SECRET")
        return HermesBackend(inner, transcript_url, webhook_secret=webhook_secret)
    return inner


_backend: TextBackend = _build_backend()


async def get_backend() -> TextBackend:
    return _backend


@app.post("/v1/chat/completions")
async def chat_completions(
    raw_request: Request,
    authorization: Optional[str] = Header(default=None),
    backend: TextBackend = Depends(get_backend),
):
    del authorization

    # 读完整 raw body 一次, 后续 hybrid raw proxy 路径要用 (不能再 .json() 两次)
    raw_body = await raw_request.body()
    try:
        body_dict = json.loads(raw_body)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "invalid json"})

    # 解析为 pydantic 以做 router decision + backend.stream_response
    try:
        request_obj = ChatCompletionRequest.model_validate(body_dict)
    except Exception as exc:
        return JSONResponse(
            status_code=400, content={"error": f"invalid request: {exc}"}
        )

    if not request_obj.stream:
        return JSONResponse(
            status_code=503,
            content={"error": "non-streaming unsupported in spike"},
        )

    # H035 router: hybrid 模式下 motor intent 走 raw deepseek passthrough,
    # 让 DeepSeek 看到 tools=[14 个 self.otto.*] 并真返回 tool_calls 给 xinnan-tech
    backend_kind = os.environ.get("OPENAI_SHIM_BACKEND", "echo").lower()
    if backend_kind == "hybrid":
        if should_route_raw_deepseek(
            messages=body_dict.get("messages", []),
            tools=body_dict.get("tools"),
        ):
            api_key = os.environ.get("DEEPSEEK_API_KEY")
            base_url = os.environ.get(
                "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
            )
            if not api_key:
                LOG.error("hybrid motor route requires DEEPSEEK_API_KEY")
                return JSONResponse(
                    status_code=500,
                    content={"error": "DEEPSEEK_API_KEY required for hybrid motor route"},
                )
            LOG.info(
                "[hybrid] route=raw_deepseek user=%r",
                _peek_user(body_dict)[:80],
            )
            return StreamingResponse(
                stream_raw_deepseek(
                    api_key=api_key, base_url=base_url, body=raw_body
                ),
                media_type="text/event-stream",
            )
        else:
            LOG.info(
                "[hybrid] route=hermes_agent user=%r",
                _peek_user(body_dict)[:80],
            )

    text_deltas = backend.stream_response(request_obj.messages, request_obj.model)
    return StreamingResponse(
        chat_completion_sse(text_deltas=text_deltas, model=request_obj.model),
        media_type="text/event-stream",
    )


def _peek_user(body_dict: dict) -> str:
    """For log line — pull last user text (best effort)."""
    for m in reversed(body_dict.get("messages") or []):
        if isinstance(m, dict) and m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                return c
    return ""
