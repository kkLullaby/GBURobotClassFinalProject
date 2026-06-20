---
id: 2026-06-20-m2-hybrid-backend-router-035
from: planner
to: planner
parent: 2026-06-20-m2-hermes-agent-backend-033
supersedes:
status: done
created: 2026-06-20
artifacts:
  - openai-shim/src/openai_shim/router.py (新, 路由判定)
  - openai-shim/src/openai_shim/raw_deepseek_proxy.py (新, openai SDK stream + tools 透传)
  - openai-shim/src/openai_shim/app.py (改, OPENAI_SHIM_BACKEND=hybrid 分支)
  - openai-shim/tests/test_router.py (新, 9 case)
---

## Why now

H033 落地后, 物理实测发现 **voice 控舵机能力丢失**: 对机器人讲 "向前走" /
"挥挥手", 喇叭只回 "我不能直接控制硬件" — root cause: HermesAgentBackend
完全忽略 xinnan-tech 发的 request.tools (14 个 ESP32 MCP tool), hermes-z
agent 完全不知道 self.otto.action 存在.

H033 后看 docker server log 真把 14 tools (self_otto_action 26 动作 +
self_otto_show_emoji + ... + 4 device) 灌进每个 LLM call.
xinnan-tech 完全没改, 是 shim 截了请求只 forward content text. 老 baseline
舵机能动是因为 shim 不存在时 xinnan-tech 直连 DeepSeek + tools.

## Objective

写一个 router: 看到 user text 是 motor 类话 (走/动/转/跳/挥/摆/坐/...) →
raw-proxy 到 DeepSeek 带完整 tools (舵机能动); 否则 → HermesAgentBackend
(H033 高光, hermes-z + 本机 tool).

## What I Did

### 1. `router.py` (新 ~80 LOC + 9 case 测)

- `MOTOR_KEYWORDS` 中英文 80+ 个 keyword (走 转 跳 挥 坐 站 笑 wave walk turn ...)
- `_last_user_message_text` 走 messages 反序找 last user message text
- `_has_motor_keyword` boolean
- `_has_otto_tools` 检测 tools 数组里有没 `self.otto.*` (兼容 nested + flat)
- `should_route_raw_deepseek` 简单 rule: motor keyword → raw, 其余 → hermes

测试 9 case, 包括 motor zh/en, 非 motor, otto tools nested/flat/empty,
route motor / route chat / route tool query (有 otto tools 但 user 没说动作).

### 2. `raw_deepseek_proxy.py` (新 ~100 LOC)

**第一版 httpx async stream** 抛 `ConnectError('')` — 后查是 conda env
httpx 0.28.1 + DeepSeek TLS = `SSL: UNEXPECTED_EOF_WHILE_READING` (sync 复现).
但 cURL 同 endpoint OK + openai SDK 用 httpx 内部不抛错 → openai SDK 一定
配了什么 magic.

**最终版** 改用 `AsyncOpenAI.chat.completions.create(stream=True)`:
- 收 `tools=[...]` `tool_choice` `temperature` `top_p` `max_tokens` 等
  OpenAI 兼容字段透传 (`_scrub_request`)
- 强制 `stream=True`
- 拿到的 `ChatCompletionChunk.model_dump_json()` 完整 wire format
  yield 回 SSE 流, 含 `tool_calls` deltas + `finish_reason="tool_calls"`
- 异常完整 log + emit error SSE chunk + [DONE]

实测验证 (用 `self_otto_action` underscore tool name):
```
TC chunk 2 ... tool_calls=[{name:"self_otto_action", arguments:"{\"action\": "}]
TC chunk 9-14 ... arguments incrementally builds: hand_wave
TC chunk 14 ... finish_reason: "tool_calls"
DONE at chunk 15
```

### 3. `app.py` 改

- 读 raw body 一次 (不能 .json() 两次)
- 解析 pydantic ChatCompletionRequest 做 router decision
- `OPENAI_SHIM_BACKEND=hybrid` 模式下:
  - `router.should_route_raw_deepseek(messages, tools)` → True 走
    `stream_raw_deepseek` 直接返 SSE StreamingResponse
  - False 走 `backend.stream_response` 老路径 (HermesAgentBackend)
- log `[hybrid] route=raw_deepseek/hermes_agent user=<...>`

### 4. 物理实测

**重启 shim with hybrid + DeepSeek key** 后第一次 "挥挥手" 成功:
```
docker server: 执行工具: self_otto_action，参数: {'action': 'hand_wave', 'direction': 1, 'speed': 700}
```
**手真挥** ✅

但很快 ESP32 重连后 mcp_endpoint 报 "智能体没有连接的MCP服务器" →
舵机动作失败. **Root cause**: M1 sidecar 用 `MCP_ENDPOINT=ws://.../mcp/`
注册成了 "MCP 服务器" 占了 ESP32 自己的 server slot, **两者抢占同一个**
single_module 角色. 先到的赢.

**修法**: 杀掉 sidecar (`pkill -9 -f xiaozhi_mcp_adapter`), 让 ESP32 RST
重新注册. 再讲 motor query 稳定动作.

H035 之后, sidecar (H031 ↔ 屏幕显字 dispatch) 永久不再起 — 屏幕显字链路
被 H035 hybrid backend 路径完全替代 (motor + voice → hermes-z 两路都不需要
sidecar).

## Bitter Lessons (for H027 retro batch)

- **#30** httpx async stream + 某些服务器 TLS 1.3 = `ConnectError('')`
  (空 message); 同 endpoint cURL/openai SDK OK. fix: 用 openai SDK 而非
  raw httpx. 早期 raw_deepseek_proxy.py v1 走错.
- **#31** Sync httpx 是 debug 神器: async 抛空异常时, **同样请求 sync
  跑一次**就能看到完整 SSL trace ("UNEXPECTED_EOF_WHILE_READING").
- **#32** mcp_endpoint `/mcp/` slot 单一 — M1 sidecar 接 pipe 会**占掉
  ESP32 自己的 server 角色**, 导致 voice tool dispatch fail. H030/H031
  都没暴露因为没人在 sidecar 接 pipe 的同时测舵机. **Sidecar 不应该跟
  ESP32 共存**, 设计上 mutual exclusive: 要么走 sidecar 屏幕路径 (H030.bis
  bitter lesson #27 留 H034 polish), 要么走 hybrid + ESP32 真接 mcp_endpoint.
- **#33** "一次能, 再次不能" 通常是状态污染 / 抢占, 不是代码 bug. **第一直觉
  应该是看进程列表 + ESP32 boot log + mcp_endpoint 连接表** 而非改代码.
  本次幸运一发查到了, 但若先去改代码会浪费 20 min+.
- **#34** Function name pattern: DeepSeek 要求 `^[a-zA-Z0-9_-]+$`, **`.`
  会 400**. xinnan-tech 已经把 `self.otto.action` 转成 `self_otto_action`,
  但单元测试时手写 tool 容易写错引入误导.

## What 答辩 Demo 真正能演 (H035 后)

| Take | 讲话 | 路由 | 喇叭 / 物理 |
|---|---|---|---|
| 1 (T1 H033) | "帮我看 final 文件夹有什么目录" | hermes_agent | 喇叭说真目录名 |
| 2 (T2 H033) | "用 git log 看最近三次提交" | hermes_agent | 喇叭说 commit summary |
| 3 (T3 H033) | "读 README 告诉我项目目标" | hermes_agent | 喇叭说 elevator pitch |
| **4 (T4 H035)** | **"挥挥手"** | **raw_deepseek** | **手真挥** ✅ |
| **5 (T5 H035)** | **"向前走两步"** | **raw_deepseek** | **真走 + walk 动作** ✅ |
| **6 (T6 H035)** | **"坐下"** | **raw_deepseek** | **真坐** ✅ |

**这才是完整的"机器人 = Hermes 化身, 还会动"**: H033 给认知能力, H035
保留物理能力, hybrid router 自动分流.

## For Auditor

留 H032 batch (M3 + M2 H033 + H035 一起 review).

## Bitter Lesson 编号汇总 (待 H027 batch retro)

- #17-#25 在 H027 时第一批回灌
- #26 codex TestClient lifespan hang in sandbox (H031)
- #27 mcp_endpoint /mcp/ vs /call/ 角色分工 (H030.bis)
- #28 DeepSeek key 单一来源 = docker config (H030.bis)
- #29 voice→hermes-z 是项目最终形态 (H033)
- **#30 httpx async stream + TLS 空 ConnectError → 用 openai SDK** (H035)
- **#31 Sync httpx 是 debug 神器** (H035)
- **#32 mcp_endpoint /mcp/ slot 单一, sidecar + ESP32 mutual exclusive** (H035)
- **#33 "一次能再次不能" 第一直觉看进程/抢占, 不是改代码** (H035)
- **#34 DeepSeek function name pattern `^[a-zA-Z0-9_-]+$`** (H035)
