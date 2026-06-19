"""HTTP sidecar for XiaoZhi host-side MCP proxy calls."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from .show_text_proxy import call_show_text


app = FastAPI(title="xiaozhi-mcp-adapter sidecar")
_PIPE = None


class ShowTextRequest(BaseModel):
    device_id: str
    text: str
    kind: str = "notification"


@app.post("/tools/show_text")
async def post_show_text(request: ShowTextRequest):
    result = await call_show_text(
        _PIPE,
        request.device_id,
        request.text,
        request.kind,
    )
    return {"ok": True, "echo": result}
