import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
import websockets


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


async def _recv_matching(websocket, msg_id):
    while True:
        raw = await asyncio.wait_for(websocket.recv(), timeout=10)
        payload = json.loads(raw)
        if payload.get("id") == msg_id:
            return payload


async def _send_request(websocket, msg_id, method, params=None):
    payload = {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": method,
    }
    if params is not None:
        payload["params"] = params
    await websocket.send(json.dumps(payload))
    return await _recv_matching(websocket, msg_id)


async def _mock_mcp_endpoint(websocket):
    initialize = await _send_request(
        websocket,
        1,
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {},
            },
            "clientInfo": {
                "name": "XiaozhiMCPEndpointClient",
                "version": "1.0.0",
            },
        },
    )
    assert initialize["result"]["serverInfo"]["name"] == "xiaozhi-echo-tool"

    await websocket.send(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }
        )
    )

    tools = await _send_request(websocket, 2, "tools/list")
    tool_names = [tool["name"] for tool in tools["result"]["tools"]]
    assert "echo" in tool_names

    call = await _send_request(
        websocket,
        3,
        "tools/call",
        {"name": "echo", "arguments": {"text": "hi"}},
    )
    assert call["result"]["content"] == [{"type": "text", "text": "echoed: hi"}]


@pytest.mark.asyncio
async def test_pipe_echo_roundtrip():
    done = asyncio.Event()
    errors = []

    async def handler(websocket, *_args):
        try:
            await _mock_mcp_endpoint(websocket)
        except Exception as exc:  # pragma: no cover - re-raised below
            errors.append(exc)
        finally:
            done.set()

    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        env = os.environ.copy()
        env["MCP_ENDPOINT"] = "ws://127.0.0.1:{0}".format(port)
        env["PYTHONPATH"] = str(SRC)

        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "xiaozhi_mcp_adapter.pipe",
            cwd=str(ROOT),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            await asyncio.wait_for(done.wait(), timeout=15)
            if errors:
                raise errors[0]
        finally:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()

        stderr = await proc.stderr.read()
        assert b"Traceback" not in stderr
