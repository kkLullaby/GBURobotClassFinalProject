---
id: ADR-0009
title: lark-event-listener — 飞书入口走长连接 + spawn hermes -z 闭环
status: active
date: 2026-06-20
supersedes: null
superseded_by: null
---

## Context

ADR-0008 (`lark-mcp-server`) 让机器人能"主动给飞书发消息" (outbound)。
但**入口方向缺失** —— 用户在飞书 ottagent app 私聊机器人,没有进程在监听,
所以机器人不回应。结果:lark channel 是半边的,违反"飞书 = ottagent 的桌面
channel"主张。

本 ADR 决定加 inbound 这半边,把飞书闭环成真正的双向 channel。

## D1 spike 结论 (前置)

**spike** 决定 inbound 链路能否同时让物理小智 ESP32 喇叭说话:

| 候选 dispatch 路径 | 状态 | 结论 |
|---|---|---|
| mcp-endpoint-server `/call/` HTTP POST | ❌ | `/call/` 是 WebSocket 端点 (xinnan-tech 主 server 作为 client 反向连接用),不接 HTTP |
| xinnan-tech 主 server HTTP 注入 | ❌ | 只暴露 `/xiaozhi/ota/` + `/mcp/vision/explain`,无"让某个 ESP32 主动 TTS"接口 |
| 改上游 xinnan-tech 代码 | ❌ | out of scope (CLAUDE.md §Project Scope,submodule 只读) |

**裁决**:**砍掉** `xiaozhi_say` MCP tool。本期 inbound 只做 **飞书 → hermes →
回飞书** 单向闭环;飞书消息**不**触发物理喇叭说话。下一期再做(可能要研究
ESP32 端 PIR/sensor 主动 push 路径,或写一个 sidecar 占用 `/mcp/` slot 后给
hermes 暴露真正的 TTS tool)。

## Decision

新写独立 Python 包 `lark-event-listener/` (~250 LOC + 14 test),作为**常驻
长连接客户端**接飞书 IM 事件,每条用户私聊消息 spawn 一个 `hermes -z PROMPT`
subprocess,prompt 强制 hermes **调** `lark_send_message_to_self` 工具把回复
发回去。

### 为什么走长连接而不是 webhook

| 候选 | 优 | 劣 | 选 |
|---|---|---|---|
| **长连接 (lark_oapi.ws.Client)** | 无需公网入口;SDK 内置 auth/重连/ping;本地 demo 直接跑 | 需要常驻 Python 进程 | ✅ |
| Webhook | 标准 HTTP,无状态 | 需要公网 URL (ngrok/cloudflare tunnel),需要手算 challenge/AES/sig | ❌ |

笔记本 demo 环境完全没有公网入口,长连接是唯一不需要打洞的方案。

### 为什么独立包而不是塞进 lark-mcp-server

lark-mcp-server 是 hermes spawn 的 stdio MCP server (每次 hermes 启动时 short-
lived 子进程);lark-event-listener 是长进程独立常驻。两个生命周期完全不同,
封一起会让 stop_all.sh / 日志路径 / 测试边界全部混乱。

### 防死循环 (defense in depth)

机器人通过 `lark_send_message_to_self` 发出去的消息也会触发
`im.message.receive_v1` (receiver = bot 自己)。Listener 用两层过滤:

1. `sender.sender_type == "app"` → skip (任何 bot/app 都不响应)
2. (可选) `LARK_BOT_OPEN_ID` env 配上 → 按 open_id 精确过滤

#1 已经覆盖 99% 场景,#2 是冗余防御。

### 凭证复用

长连接模式**不需要** `LARK_ENCRYPT_KEY` / `LARK_VERIFICATION_TOKEN` (那是
webhook 模式的),所以**不改** `~/.config/lark-mcp/.env`,直接复用 ADR-0008
的凭证文件。

## 架构 (最终落地)

```
你的飞书账号 ──① 私聊 "hello"── 飞书开放平台
                                      │
                                      │ ② ws push event
                                      ↓
                            lark-event-listener (常驻 nohup)
                                      │ MessageHandler.handle
                                      │  - dedup (LRU 256)
                                      │  - filter sender_type==app
                                      │  - filter chat_type!=p2p
                                      │  - filter message_type!=text
                                      │ ③ spawn hermes -z PROMPT
                                      ↓
                                hermes-agent
                                      │ DeepSeek reason
                                      │ ④ tool_call lark_send_message_to_self
                                      ↓
                              lark-mcp-server (stdio MCP)
                                      │ ⑤ feishu OpenAPI HTTP POST
                                      ↓
                              飞书 → 你的私聊收到 ottagent 回复
```

ADR-0007 hybrid router 路径 (voice → ESP32) 和这里**完全独立**,不互相影响。
demo 时可以同时玩两条线。

## 实测验证 (2026-06-20)

`pytest lark-event-listener/tests/` → **14/14 PASS in 0.06s**

物理 verify (Phase 0-3 in plan): 飞书后台开通长连接 + start_lark_listener.sh
+ 飞书私聊发文本 → log 见 `received from ou_xxx: ...` → spawn hermes → 飞书
收到回复。

## Consequences

### Positive

- 答辩多一条 demo: "我在飞书@ottagent,它回我",讲完整 channel 论点
- 任何企业飞书账号都能玩,不需要在物理机器人旁边
- lark-mcp-server 零修改,只加常驻进程
- 全部走标准 lark_oapi SDK,SDK 自动处理重连/auth/序列化

### Negative / 待 polish

- **响应延迟 10-30s**:hermes cold spawn 3-5s + DeepSeek 5-15s + lark API 1-2s
- **无上下文**:每条消息独立 hermes session (跟 voice 路径同限制)
- **不接群聊**:只私聊;群聊策略 (何时该说话,@mention 触发?) 留下一期
- **飞书消息不触发物理喇叭**:D1 spike 后砍,见前面"D1 spike 结论"
- **rate-limit 无保护**:连发 5 条会并发 spawn 5 个 hermes;暂未撞,撞了再加
  `asyncio.Semaphore(1)`

### Bitter lessons absorbed

- **#48 (本 ADR)**: `mcp-endpoint-server /call/` 是 WebSocket 端点而不是
  HTTP POST;路径名同形不同义,看 README 不够,必须 grep `@app.websocket` /
  `@app.post` 确认。读 H034 标 "TBD" 时就该先做这步 spike,而不是写
  "可能可以通过 HTTP POST 触发"。
- **#49 (本 ADR)**: 飞书长连接模式和 webhook 模式凭证需求不同;长连接
  **不需要** ENCRYPT_KEY / VERIFICATION_TOKEN,SDK 走 ws 协议层 auth。
  写 .env 时不要照搬 webhook 教程加一堆没用的 key。
- **#50 (本 ADR)**: 飞书 SDK 的 callback 是 sync `Callable[[Event], None]`,
  内部要 dispatch 到 async handler 必须 `asyncio.get_event_loop().create_task`,
  否则 await 不起来。lark_oapi.ws.Client 内部维护一个 loop 给 callback
  跑同步 — 注意不要在 callback 里直接 `await`。
- **#51 (本 ADR, 物理验证时发现)**: listener 本身跑在 proxy 全 unset 的
  环境 (飞书 open.feishu.cn 必须直连,否则被 clash fake-ip 池污染),
  但 `asyncio.create_subprocess_exec(env={**os.environ})` 会把这个空
  proxy env **原样传给 hermes 子进程**,导致 hermes 调 DeepSeek 也走
  fake-ip → `Connection error after 3 retries`。修复:`spawn_hermes`
  必须**重建** env, 给 hermes 注入 `ALL_PROXY=socks5://...` (大小写都设,
  bitter lesson #44) + `NO_PROXY=open.feishu.cn,open.larksuite.com`,
  让 hermes 调用的飞书 tool 仍走直连。本质上这是 #44+#45 在父子进程
  边界的复现 — 父进程的 env 决定不是子进程 env 想要的。

## References

- @lark-event-listener/ (新增独立包)
- @scripts/start_lark_listener.sh (启动脚本)
- @docs/adr/0008-lark-mcp-server-integration.md (前置 outbound 半边)
- 飞书长连接 SDK: https://github.com/larksuite/oapi-sdk-python
