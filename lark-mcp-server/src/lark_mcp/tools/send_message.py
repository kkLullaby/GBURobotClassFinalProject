"""Tool: lark_send_message_to_self — send a text msg to the owner's Lark account."""

from __future__ import annotations

import os
from typing import Optional

from ..client import LarkClient, LarkError


async def lark_send_message_to_self(text: str, mobile: Optional[str] = None) -> dict:
    """Send `text` as a private Lark message to the configured user (LARK_USER_MOBILE).

    Args:
        text: message body (plain text; emoji ok; max ~30KB).
        mobile: override recipient phone. Defaults to env LARK_USER_MOBILE.

    Returns:
        {"ok": True, "message_id": "om_xxx", "open_id": "ou_xxx"} on success.

    Raises:
        RuntimeError if env not set; LarkError on API failure.
    """
    target_mobile = mobile or os.environ.get("LARK_USER_MOBILE")
    if not target_mobile:
        raise RuntimeError(
            "No recipient mobile. Set LARK_USER_MOBILE in ~/.config/lark-mcp/.env "
            "or pass mobile= argument."
        )

    client = LarkClient.from_env()
    open_id = await client.open_id_by_mobile(target_mobile)
    result = await client.send_text_to_open_id(open_id, text)
    return {
        "ok": True,
        "message_id": result.get("message_id"),
        "open_id": open_id,
        "preview": text[:80],
    }
