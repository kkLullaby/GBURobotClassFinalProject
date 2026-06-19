"""WebSocket-to-stdio MCP pipe for the H015 echo spike."""

import asyncio
import logging
import os
import random
import signal
import subprocess
import sys
from typing import List, Optional

import websockets


LOG = logging.getLogger("xiaozhi_mcp_adapter.pipe")
MAX_BACKOFF_SECONDS = 600.0


class StopRequested(Exception):
    """Raised when SIGINT/SIGTERM asks the pipe to stop."""


def _default_child_command() -> List[str]:
    return [sys.executable, "-m", "xiaozhi_mcp_adapter.echo_tool"]


def _jittered_delay(base_delay: float) -> float:
    jitter = random.uniform(-0.1, 0.1)
    return max(0.0, base_delay * (1.0 + jitter))


def _install_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()

    def request_stop() -> None:
        LOG.info("shutdown requested")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_stop)
        except NotImplementedError:
            signal.signal(sig, lambda _signum, _frame: request_stop())


def _start_child() -> subprocess.Popen:
    command = _default_child_command()
    LOG.info("starting child process: %s", " ".join(command))
    return subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )


async def _readline(stream) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, stream.readline)


async def _ws_to_child(websocket, child: subprocess.Popen, stop_event: asyncio.Event) -> None:
    assert child.stdin is not None
    async for message in websocket:
        if stop_event.is_set():
            break
        if not isinstance(message, str):
            LOG.debug("ignoring non-text websocket frame")
            continue
        child.stdin.write(message)
        if not message.endswith("\n"):
            child.stdin.write("\n")
        child.stdin.flush()


async def _child_to_ws(websocket, child: subprocess.Popen, stop_event: asyncio.Event) -> None:
    assert child.stdout is not None
    while not stop_event.is_set():
        line = await _readline(child.stdout)
        if line == "":
            LOG.info("child stdout closed")
            break
        await websocket.send(line.rstrip("\n"))


async def _child_stderr_to_log(child: subprocess.Popen, stop_event: asyncio.Event) -> None:
    assert child.stderr is not None
    while not stop_event.is_set():
        line = await _readline(child.stderr)
        if line == "":
            break
        LOG.info("child stderr: %s", line.rstrip())


async def _terminate_child(child: subprocess.Popen) -> None:
    if child.poll() is not None:
        return
    child.terminate()
    try:
        loop = asyncio.get_running_loop()
        await asyncio.wait_for(loop.run_in_executor(None, child.wait), timeout=5)
    except asyncio.TimeoutError:
        child.kill()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, child.wait)


async def _pipe_once(uri: str, stop_event: asyncio.Event) -> None:
    child: Optional[subprocess.Popen] = None
    try:
        child = _start_child()
        async with websockets.connect(uri) as websocket:
            LOG.info("connected to MCP endpoint: %s", uri)
            tasks = [
                asyncio.create_task(_ws_to_child(websocket, child, stop_event)),
                asyncio.create_task(_child_to_ws(websocket, child, stop_event)),
                asyncio.create_task(_child_stderr_to_log(child, stop_event)),
            ]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                exc = task.exception()
                if exc is not None:
                    raise exc
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
    finally:
        if child is not None:
            await _terminate_child(child)


async def run_forever() -> None:
    endpoint = os.environ.get("MCP_ENDPOINT")
    if not endpoint:
        raise SystemExit("MCP_ENDPOINT is required")

    stop_event = asyncio.Event()
    _install_signal_handlers(stop_event)

    backoff = 1.0
    while not stop_event.is_set():
        try:
            await _pipe_once(endpoint, stop_event)
            if stop_event.is_set():
                break
            backoff = 1.0
        except (OSError, websockets.WebSocketException) as exc:
            if stop_event.is_set():
                break
            delay = _jittered_delay(backoff)
            LOG.warning(
                "MCP endpoint connection failed: %s; reconnecting in %.2fs",
                exc,
                delay,
            )
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2.0, MAX_BACKOFF_SECONDS)
        except StopRequested:
            break


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
