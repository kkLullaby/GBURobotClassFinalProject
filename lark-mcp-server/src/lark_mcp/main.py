"""lark-mcp-server stdio entrypoint.

Run:
    pyx -m lark_mcp.main

Hermes wires it as:
    hermes mcp add lark --command pyx --args '-m,lark_mcp.main' \\
        --env-file ~/.config/lark-mcp/.env

Reads .env from $LARK_ENV_FILE (default ~/.config/lark-mcp/.env) on startup.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

# python-dotenv is lazy-imported so that environments with deps pre-baked
# (e.g. Hermes passing --env-file) can skip it.
def _load_env() -> None:
    env_path_str = os.environ.get("LARK_ENV_FILE", "~/.config/lark-mcp/.env")
    env_path = Path(env_path_str).expanduser()
    if not env_path.is_file():
        # Not fatal — env vars may already be set externally (e.g. hermes --env-file).
        return
    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError:  # pragma: no cover - dotenv is a hard dep but guard anyway
        return
    load_dotenv(env_path, override=False)


def _check_env() -> None:
    missing = [k for k in ("LARK_APP_ID", "LARK_APP_SECRET", "LARK_USER_MOBILE") if not os.environ.get(k)]
    if missing:
        sys.stderr.write(
            f"[lark-mcp-server] FATAL: missing env vars: {missing}. "
            f"Put them in ~/.config/lark-mcp/.env or pass via --env-file.\n"
        )
        sys.exit(2)


async def _serve_stdio() -> None:
    """Run the MCP stdio server. Imports mcp lazily so unit tests don't need it."""
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    from .tools.send_message import lark_send_message_to_self

    server: Server = Server("lark-mcp-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="lark_send_message_to_self",
                description=(
                    "Send a private Lark/Feishu text message to the owner of this MCP server. "
                    "Use this when the user asks the robot to notify them, leave a memo, "
                    "or push something to their phone. Returns message_id on success."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Message body. Plain text. Emoji ok. Keep under 1KB for TTS-friendly demos.",
                        },
                        "mobile": {
                            "type": "string",
                            "description": "Override recipient mobile (11 digits). Defaults to LARK_USER_MOBILE env.",
                        },
                    },
                    "required": ["text"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name != "lark_send_message_to_self":
            raise ValueError(f"unknown tool: {name}")
        text = arguments.get("text", "")
        mobile = arguments.get("mobile")
        result = await lark_send_message_to_self(text=text, mobile=mobile)
        return [
            TextContent(
                type="text",
                text=f"OK: message {result.get('message_id')} sent to open_id={result.get('open_id')}",
            )
        ]

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> None:
    _load_env()
    _check_env()
    asyncio.run(_serve_stdio())


if __name__ == "__main__":
    main()
