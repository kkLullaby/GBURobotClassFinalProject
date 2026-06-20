"""Lark/Feishu OpenAPI client with tenant_access_token caching + open_id lookup.

Reads credentials from environment (loaded by main.py from ~/.config/lark-mcp/.env):
- LARK_APP_ID          : cli_xxxxxxxxxxxxxxxx
- LARK_APP_SECRET      : 32-char hex secret
- LARK_USER_MOBILE     : default recipient phone (11 digits)
- LARK_HOST            : https://open.feishu.cn (CN) or https://open.larksuite.com (intl)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

DEFAULT_HOST = "https://open.feishu.cn"
TOKEN_TTL_SAFETY_S = 60  # refresh 60s before real expiry


class LarkError(RuntimeError):
    """Wrapped Lark OpenAPI error with code + message."""

    def __init__(self, code: int, msg: str, *, http_status: Optional[int] = None) -> None:
        super().__init__(f"Lark API error {code}: {msg}")
        self.code = code
        self.msg = msg
        self.http_status = http_status


@dataclass
class LarkClient:
    """Thin async wrapper over Lark OpenAPI v1.

    Caches tenant_access_token in-memory; refreshes on demand.
    Resolves user mobile → open_id once and caches that too.
    """

    app_id: str
    app_secret: str
    host: str = DEFAULT_HOST
    _token: Optional[str] = field(default=None, init=False, repr=False)
    _token_expires_at: float = field(default=0.0, init=False, repr=False)
    _open_id_cache: dict = field(default_factory=dict, init=False, repr=False)

    @classmethod
    def from_env(cls) -> "LarkClient":
        app_id = os.environ.get("LARK_APP_ID")
        app_secret = os.environ.get("LARK_APP_SECRET")
        if not app_id or not app_secret:
            raise RuntimeError(
                "LARK_APP_ID and LARK_APP_SECRET must be set in environment. "
                "Put them in ~/.config/lark-mcp/.env."
            )
        host = os.environ.get("LARK_HOST", DEFAULT_HOST).rstrip("/")
        return cls(app_id=app_id, app_secret=app_secret, host=host)

    # ------------------------------------------------------------------ token

    async def _fetch_token(self, client: httpx.AsyncClient) -> str:
        url = f"{self.host}/open-apis/auth/v3/tenant_access_token/internal"
        resp = await client.post(
            url,
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10.0,
        )
        data = resp.json()
        code = data.get("code", -1)
        if code != 0:
            raise LarkError(code, data.get("msg", "unknown"), http_status=resp.status_code)
        self._token = data["tenant_access_token"]
        # Lark returns expire in seconds (typ. 7200)
        self._token_expires_at = time.monotonic() + max(60, int(data.get("expire", 7200)) - TOKEN_TTL_SAFETY_S)
        return self._token

    async def _token_for(self, client: httpx.AsyncClient) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token
        return await self._fetch_token(client)

    # ------------------------------------------------------------------ user lookup

    async def open_id_by_mobile(self, mobile: str) -> str:
        """Look up open_id for a phone number; cached after first call."""
        if mobile in self._open_id_cache:
            return self._open_id_cache[mobile]
        async with httpx.AsyncClient() as client:
            token = await self._token_for(client)
            url = f"{self.host}/open-apis/contact/v3/users/batch_get_id?user_id_type=open_id"
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json={"mobiles": [mobile]},
                timeout=10.0,
            )
            data = resp.json()
            if data.get("code", -1) != 0:
                raise LarkError(
                    data.get("code", -1),
                    data.get("msg", "open_id lookup failed"),
                    http_status=resp.status_code,
                )
            users = (data.get("data") or {}).get("user_list") or []
            for u in users:
                if u.get("mobile") == mobile and u.get("user_id"):
                    open_id = u["user_id"]
                    self._open_id_cache[mobile] = open_id
                    return open_id
            raise LarkError(
                -1,
                f"mobile {mobile} not found in tenant (app must have contact:user.id:readonly perm "
                "AND the user must be in the same tenant as the app)",
            )

    # ------------------------------------------------------------------ message send

    async def send_text_to_open_id(self, open_id: str, text: str) -> dict:
        """POST /im/v1/messages with receive_id_type=open_id, msg_type=text."""
        async with httpx.AsyncClient() as client:
            token = await self._token_for(client)
            url = f"{self.host}/open-apis/im/v1/messages?receive_id_type=open_id"
            payload = {
                "receive_id": open_id,
                "msg_type": "text",
                # Lark wants content as JSON-encoded string, not nested object.
                "content": _text_content_json(text),
            }
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=10.0,
            )
            data = resp.json()
            if data.get("code", -1) != 0:
                raise LarkError(
                    data.get("code", -1),
                    data.get("msg", "send failed"),
                    http_status=resp.status_code,
                )
            return data.get("data") or {}


def _text_content_json(text: str) -> str:
    """Lark `content` field MUST be a JSON string, not an object. Escape accordingly."""
    import json

    return json.dumps({"text": text}, ensure_ascii=False)
