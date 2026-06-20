"""H035 router unit tests."""

from openai_shim.router import (
    _has_motor_keyword,
    _has_otto_tools,
    should_route_raw_deepseek,
)


def test_motor_keyword_zh():
    assert _has_motor_keyword("向前走两步")
    assert _has_motor_keyword("挥手")
    assert _has_motor_keyword("坐下")
    assert _has_motor_keyword("笑一个")
    assert _has_motor_keyword("跳一下")


def test_motor_keyword_en():
    assert _has_motor_keyword("walk forward")
    assert _has_motor_keyword("wave your hand")
    assert _has_motor_keyword("sit down")


def test_non_motor_text():
    assert not _has_motor_keyword("现在几点了")
    assert not _has_motor_keyword("帮我看看 final 文件夹有什么")
    assert not _has_motor_keyword("读一下 README")
    assert not _has_motor_keyword("用 git log 看最近三次提交")


def test_has_otto_tools_nested():
    tools = [
        {"type": "function", "function": {"name": "self.otto.action", "description": ""}}
    ]
    assert _has_otto_tools(tools)


def test_has_otto_tools_flat():
    # xinnan-tech 实测可能扁平
    tools = [{"name": "self.otto.show_emoji"}]
    assert _has_otto_tools(tools)


def test_has_otto_tools_empty():
    assert not _has_otto_tools(None)
    assert not _has_otto_tools([])
    assert not _has_otto_tools([{"function": {"name": "google_search"}}])


def test_route_motor_intent():
    """User 说动作 → raw deepseek."""
    msgs = [{"role": "user", "content": "向前走两步"}]
    assert should_route_raw_deepseek(messages=msgs, tools=[])


def test_route_chat_intent():
    """User 问问题 → hermes_agent."""
    msgs = [{"role": "user", "content": "现在几点了"}]
    assert not should_route_raw_deepseek(messages=msgs, tools=[])


def test_route_tool_query_intent():
    """User 让查文件 → hermes_agent (虽然有 self.otto tools, user 没说动作)."""
    msgs = [{"role": "user", "content": "帮我读 README"}]
    tools = [{"function": {"name": "self.otto.action"}}]
    assert not should_route_raw_deepseek(messages=msgs, tools=tools)
