"""Smoke test: bypass MCP, call send_message directly to verify Lark creds work.

Usage:
    pyx -m lark_mcp.smoke "你好,这是 ottagent 自检消息"

Exits 0 on success, 1 on Lark error (with code+msg), 2 on env error.
"""

from __future__ import annotations

import asyncio
import sys

from .client import LarkError
from .main import _check_env, _load_env
from .tools.send_message import lark_send_message_to_self


async def _run(text: str) -> int:
    try:
        result = await lark_send_message_to_self(text=text)
    except LarkError as e:
        sys.stderr.write(
            f"[lark-mcp smoke] FAILED: Lark API code={e.code} msg={e.msg}\n"
        )
        return 1
    except RuntimeError as e:
        sys.stderr.write(f"[lark-mcp smoke] FAILED: {e}\n")
        return 2
    print(f"OK message_id={result.get('message_id')} open_id={result.get('open_id')}")
    print(f"   preview: {result.get('preview')}")
    return 0


def main() -> None:
    _load_env()
    _check_env()
    text = " ".join(sys.argv[1:]).strip() or "ottagent smoke test"
    rc = asyncio.run(_run(text))
    sys.exit(rc)


if __name__ == "__main__":
    main()
