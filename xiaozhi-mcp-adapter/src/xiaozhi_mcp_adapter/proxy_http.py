"""HTTP sidecar for XiaoZhi host-side MCP proxy calls."""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from pydantic import BaseModel

from . import pipe as pipe_module
from . import show_text_proxy
from .show_text_proxy import call_show_text


LOG = logging.getLogger("xiaozhi_mcp_adapter.proxy_http")
app = FastAPI(title="xiaozhi-mcp-adapter sidecar")


class ShowTextRequest(BaseModel):
    device_id: str
    text: str
    kind: str = "notification"


@app.on_event("startup")
async def start_pipe() -> None:
    endpoint = os.environ.get("MCP_ENDPOINT")
    if not endpoint:
        LOG.warning("MCP_ENDPOINT is not set; xiaozhi sidecar pipe disabled")
        show_text_proxy._PIPE = None
        return

    show_text_proxy._PIPE = await pipe_module.connect(endpoint)
    LOG.info("xiaozhi sidecar connected to MCP endpoint")


@app.on_event("shutdown")
async def stop_pipe() -> None:
    current_pipe = show_text_proxy._PIPE
    if current_pipe is not None:
        await current_pipe.close()
    show_text_proxy._PIPE = None


@app.post("/tools/show_text")
async def post_show_text(request: ShowTextRequest):
    result = await call_show_text(
        show_text_proxy._PIPE,
        request.device_id,
        request.text,
        request.kind,
    )
    return {"ok": True, "echo": result}
