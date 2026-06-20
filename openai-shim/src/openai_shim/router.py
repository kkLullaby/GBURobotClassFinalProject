"""H035 HybridRouter: route request to motor-aware raw proxy or hermes-z agent.

Decision matrix:

| user text contains motor keyword | request.tools has self.otto.* | route |
|----------------------------------|-------------------------------|-------|
| yes                              | yes                           | RAW (DeepSeek + tools, 喇叭说 + 舵机动) |
| yes                              | no                            | RAW  (degraded: no tools to call, but user phrasing implies motor — still let DeepSeek handle) |
| no                               | yes                           | HERMES (chat/query — hermes-z with tool-call to local shell/file/...) |
| no                               | no                            | HERMES |

The `tools` field is what xinnan-tech sends — if the server registered no
ESP32 tools (e.g. ESP32 offline), no motor route is possible regardless of
intent.

Motor keywords: walk/turn/jump/swing/bend/sit/dance/wave/handsup/handsdown/...
Chinese: 走/动/转/跳/挥/摆/坐/起/站/抬/笑/扭/弯/跑/跺/踢/伸/弓/扭/招手/敬礼/...
"""

from __future__ import annotations

from typing import Any, List


# 中文 + 英文动作 keyword. 命中任意一个就视为 motor intent.
# 注意: "现在几点" 不含, "去看看" 含 "去" 但去不算 motor — 保守加 boundary.
MOTOR_KEYWORDS = (
    # 中文 — 动作动词
    "走", "动一动", "转身", "转一下", "转圈", "跳", "蹲", "坐下", "站起",
    "站立", "起立", "起来", "起身", "挥手", "招手", "招呼", "打招呼", "摆手", "摆动",
    "扭一扭", "扭扭", "弯腰", "弯下", "跺脚", "踢", "伸展", "举起", "举手", "举高",
    "放下", "放低", "敬礼", "鞠躬", "握手", "拥抱", "撒娇", "撒花", "鼓掌",
    "拍手", "前进", "后退", "左转", "右转", "向前", "向后", "向左", "向右",
    "上下", "摇摆", "摇头", "点头", "颤抖", "抖动", "震荡", "演示", "展示动作",
    "回家", "复位", "归位", "回原位", "原地", "停下", "停止", "别动",
    "跑步", "跑起来", "广播体操", "健身", "做操", "大风车", "魔力转圈圈",
    "太空步", "月球漫步", "旋风腿", "摇腿", "握手",
    # 中文 — 名词触发 (笑/cool/...)
    "笑一", "笑笑", "笑个", "笑脸", "做表情", "表情", "卖萌", "害羞", "酷一",
    # 英文
    "walk", "turn", "jump", "swing", "bend", "sit", "dance", "wave",
    "stand", "hands up", "hands down", "moonwalk", "windmill", "fitness",
    "greeting", "shake leg", "showcase", "home position", "stop",
    "left", "right", "forward", "backward", "front", "back",
    "raise", "lower", "salute", "bow", "clap", "applause",
)


def _last_user_message_text(messages: List[Any]) -> str:
    """Walk messages in reverse to find the last user message's plain text."""
    for m in reversed(messages):
        if isinstance(m, dict):
            role = m.get("role", "")
            content = m.get("content", "")
        else:
            role = getattr(m, "role", "")
            content = getattr(m, "content", "")
        if str(role) != "user":
            continue
        if isinstance(content, str):
            return content
        # OpenAI 多模态: content 可能是 list[dict{"type":"text","text":...}]
        if isinstance(content, list):
            parts = []
            for p in content:
                if isinstance(p, dict) and p.get("type") == "text":
                    parts.append(str(p.get("text", "")))
            return " ".join(parts)
        return str(content)
    return ""


def _has_motor_keyword(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(kw in t or kw in text for kw in MOTOR_KEYWORDS)


def _has_otto_tools(tools: Any) -> bool:
    """tools 字段是 OpenAI tools=[{type:"function","function":{name:"self.otto.*",...}}, ...]"""
    if not tools or not isinstance(tools, list):
        return False
    for t in tools:
        if not isinstance(t, dict):
            continue
        fn = t.get("function") or {}
        name = fn.get("name", "") if isinstance(fn, dict) else ""
        if name.startswith("self.otto."):
            return True
        # 兼容 xinnan-tech 可能扁平: {name: "self.otto.action", ...}
        if str(t.get("name", "")).startswith("self.otto."):
            return True
    return False


def should_route_raw_deepseek(*, messages: List[Any], tools: Any) -> bool:
    """True → raw passthrough to DeepSeek (with tools), 舵机能动.
    False → HermesAgentBackend (chat/query, hermes-z 本机 tool-call).
    """
    user_text = _last_user_message_text(messages)
    return _has_motor_keyword(user_text)
