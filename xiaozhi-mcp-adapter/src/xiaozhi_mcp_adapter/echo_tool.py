"""A minimal MCP stdio server exposing echo(text)."""

import asyncio
from typing import Any, Dict, List

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions


server = Server("xiaozhi-echo-tool")


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    """Return the single echo tool."""
    return [
        types.Tool(
            name="echo",
            description='Return "echoed: " plus the input text.',
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to echo.",
                    }
                },
                "required": ["text"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle echo tool calls."""
    if name != "echo":
        raise ValueError("unknown tool: {0}".format(name))

    text = arguments.get("text") if isinstance(arguments, dict) else None
    if not isinstance(text, str):
        raise ValueError("echo requires a string text argument")

    return [types.TextContent(type="text", text="echoed: " + text)]


async def run() -> None:
    """Run the MCP server over stdio."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="xiaozhi-echo-tool",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
