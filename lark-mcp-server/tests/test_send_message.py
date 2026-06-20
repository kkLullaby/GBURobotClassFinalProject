"""Pytest cases for lark_send_message_to_self — mocks Lark OpenAPI via respx.

Covers:
  1. happy path: token fetch + open_id lookup + send → ok
  2. token cache: 2 consecutive sends share one token fetch
  3. token API error (code != 0) → LarkError with code
  4. send 5xx HTTP → LarkError (raised from non-zero code in body)
  5. mobile not found in batch_get_id user_list → LarkError(-1)
  6. content field is JSON-encoded string (Lark requires this)
  7. missing env (no LARK_APP_ID) → RuntimeError from from_env
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from lark_mcp.client import LarkClient, LarkError
from lark_mcp.tools.send_message import lark_send_message_to_self


TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
BATCH_ID_URL = (
    "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id?user_id_type=open_id"
)
SEND_URL = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"


def _token_route(respx_mock):
    return respx_mock.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={"code": 0, "msg": "ok", "tenant_access_token": "t-fake-1", "expire": 7200},
        )
    )


def _batch_id_route(respx_mock, *, mobile="13800000000", open_id="ou_test_oid"):
    return respx_mock.post(BATCH_ID_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "code": 0,
                "msg": "ok",
                "data": {
                    "user_list": [
                        {"mobile": mobile, "user_id": open_id},
                    ]
                },
            },
        )
    )


def _send_route(respx_mock, *, message_id="om_test_mid"):
    return respx_mock.post(SEND_URL).mock(
        return_value=httpx.Response(
            200, json={"code": 0, "msg": "ok", "data": {"message_id": message_id}}
        )
    )


@respx.mock
async def test_happy_path():
    _token_route(respx.mock)
    _batch_id_route(respx.mock)
    send = _send_route(respx.mock)

    result = await lark_send_message_to_self(text="hello from ottagent")

    assert result["ok"] is True
    assert result["message_id"] == "om_test_mid"
    assert result["open_id"] == "ou_test_oid"
    assert send.called

    # Verify content is JSON-encoded string (Lark requirement)
    body = json.loads(send.calls.last.request.content)
    assert body["msg_type"] == "text"
    assert isinstance(body["content"], str)
    assert json.loads(body["content"]) == {"text": "hello from ottagent"}


@respx.mock
async def test_token_cached_across_calls():
    token_route = _token_route(respx.mock)
    _batch_id_route(respx.mock)
    _send_route(respx.mock)

    # Use shared client so cache survives both calls
    client = LarkClient.from_env()
    open_id = await client.open_id_by_mobile("13800000000")
    await client.send_text_to_open_id(open_id, "first")
    await client.send_text_to_open_id(open_id, "second")

    # Token endpoint hit only once thanks to cache
    assert token_route.call_count == 1


@respx.mock
async def test_token_api_error():
    respx.mock.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"code": 99991663, "msg": "app ticket invalid"}
        )
    )
    with pytest.raises(LarkError) as exc_info:
        await lark_send_message_to_self(text="will fail at token")
    assert exc_info.value.code == 99991663


@respx.mock
async def test_send_returns_nonzero_code():
    _token_route(respx.mock)
    _batch_id_route(respx.mock)
    respx.mock.post(SEND_URL).mock(
        return_value=httpx.Response(
            200, json={"code": 230001, "msg": "receive_id invalid"}
        )
    )
    with pytest.raises(LarkError) as exc_info:
        await lark_send_message_to_self(text="bad recipient")
    assert exc_info.value.code == 230001


@respx.mock
async def test_mobile_not_in_tenant():
    _token_route(respx.mock)
    # user_list comes back empty (mobile not bound to any tenant user)
    respx.mock.post(BATCH_ID_URL).mock(
        return_value=httpx.Response(200, json={"code": 0, "data": {"user_list": []}})
    )
    with pytest.raises(LarkError) as exc_info:
        await lark_send_message_to_self(text="who am i sending to?")
    assert "not found in tenant" in exc_info.value.msg


@respx.mock
async def test_content_is_json_encoded_string():
    """Regression guard: Lark `content` MUST be a JSON-stringified object, not nested."""
    _token_route(respx.mock)
    _batch_id_route(respx.mock)
    send = _send_route(respx.mock)

    await lark_send_message_to_self(text="带中文 emoji 😀 的消息")

    body = json.loads(send.calls.last.request.content)
    # content is a string (not dict)
    assert isinstance(body["content"], str)
    # ...but parses back into the expected shape
    parsed = json.loads(body["content"])
    assert parsed == {"text": "带中文 emoji 😀 的消息"}


def test_from_env_missing_keys(monkeypatch):
    monkeypatch.delenv("LARK_APP_ID", raising=False)
    monkeypatch.delenv("LARK_APP_SECRET", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        LarkClient.from_env()
    assert "LARK_APP_ID" in str(exc_info.value)


@respx.mock
async def test_explicit_mobile_overrides_env():
    _token_route(respx.mock)
    _batch_id_route(respx.mock, mobile="18800000001", open_id="ou_other")
    _send_route(respx.mock)

    result = await lark_send_message_to_self(text="hi", mobile="18800000001")
    assert result["open_id"] == "ou_other"
