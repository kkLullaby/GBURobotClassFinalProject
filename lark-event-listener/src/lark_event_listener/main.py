"""Long-connection entry: subscribe im.message.receive_v1 → MessageHandler.

Usage:
    pyx -m lark_event_listener.main

Reads from `~/.config/lark-mcp/.env` (or path in LARK_ENV_FILE env):
    LARK_APP_ID
    LARK_APP_SECRET
    LARK_HOST (default https://open.feishu.cn)

Long-connection mode does NOT require LARK_ENCRYPT_KEY /
LARK_VERIFICATION_TOKEN — those are for the webhook path. The ws transport
handles auth via app_id/app_secret + a server-issued conn_url.

The listener is a foreground process under nohup (see
`scripts/start_lark_listener.sh`). `lark_oapi.ws.Client(auto_reconnect=True)`
handles disconnects internally.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv


LOG = logging.getLogger("lark_event_listener.main")


def _load_env() -> None:
    """Load .env from LARK_ENV_FILE or default ~/.config/lark-mcp/.env."""
    env_file = os.environ.get("LARK_ENV_FILE", "~/.config/lark-mcp/.env")
    path = Path(os.path.expanduser(env_file))
    if path.is_file():
        load_dotenv(path, override=False)
        LOG.info("loaded env from %s", path)
    else:
        LOG.warning("env file not found: %s (continuing with shell env)", path)


def _require(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise SystemExit(f"missing required env var: {name}")
    return val


def _select_domain(host: str):
    """Map LARK_HOST string to lark_oapi domain const."""
    import lark_oapi as lark

    if "larksuite" in host:
        return lark.LARK_DOMAIN
    return lark.FEISHU_DOMAIN


def _make_client(handler):
    """Build ws.Client with EventDispatcherHandler wired to our MessageHandler."""
    import lark_oapi as lark

    app_id = _require("LARK_APP_ID")
    app_secret = _require("LARK_APP_SECRET")
    host = os.environ.get("LARK_HOST", "https://open.feishu.cn")

    # The SDK callback is sync (Callable[[Event], None]) — schedule async
    # handle() on the running loop. We expose this as a closure so tests
    # don't need the real SDK to inject MessageHandler.
    def _on_message(event) -> None:
        try:
            asyncio.get_event_loop().create_task(handler.handle(event))
        except RuntimeError:
            # No running loop (unlikely in ws.Client context) — run inline
            asyncio.run(handler.handle(event))

    dispatcher = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(_on_message)
        .build()
    )

    client = lark.ws.Client(
        app_id=app_id,
        app_secret=app_secret,
        event_handler=dispatcher,
        domain=_select_domain(host),
        log_level=lark.LogLevel.INFO,
    )
    return client


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _load_env()

    from .handler import MessageHandler

    bot_open_id = os.environ.get("LARK_BOT_OPEN_ID") or None
    handler = MessageHandler(bot_open_id=bot_open_id)

    client = _make_client(handler)

    # Graceful shutdown: SIGTERM/SIGINT → log and exit; Client doesn't expose
    # a clean stop(), but SIGTERM kills the asyncio loop, which is acceptable
    # given the listener is stateless beyond the in-memory dedup LRU.
    def _bye(signum, _frame):
        LOG.info("received signal %s, exiting", signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _bye)
    signal.signal(signal.SIGINT, _bye)

    LOG.info("lark_event_listener starting (long-connection)...")
    client.start()  # blocks forever; auto_reconnect=True by default


if __name__ == "__main__":
    main()
