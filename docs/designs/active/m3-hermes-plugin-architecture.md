---
status: current
created: 2026-06-19
author: planner
period: Week 3 prep (Week 0/1 闭环后)
---

# M3 Hermes-xiaozhi Plugin — 架构设计

> 配合 [ADR-0005](../../adr/0005-openai-compat-transcript-egress.md) +
> [H020](../../handoffs/archive/2026-06-19-real-hermes-transcript-handshake-020.md)
> +
> [H025](../../handoffs/archive/2026-06-19-m2-hermes-hmac-sign-025.md) 实测
> 阅读。本文是 H028 spike 之前的设计快照——可能在 spike 后修正。

## §0 前提（已经成立的事实）

1. **transcript 入口已通**：M2 shim (`openai-shim/`) 的 HermesBackend
   会把 user transcript + assistant 回复 POST 到
   `http://127.0.0.1:8644/webhooks/<route>`，HMAC `X-Hub-Signature-256` 签好。
   H020 实测：Hermes 真 spawn agent session
   `20260619_205520_be1c7197`，session log 里有 transcript。
2. **session 形态**：当前 Hermes 把每个 transcript POST 当作"新建临时
   session"——这就是默认 webhook platform 的行为，没有 chat 历史的概念。
3. **M3 缺什么**：
   - **send() 反向**：Hermes 想"主动跟机器人说话"（cron 早安 / 工具调用结果
     返回）时，没有任何路径走回 ESP32。webhook platform 当前是**单向**的。
   - **chat 持久化**：device_id 维度的 session 复用——同一机器人多轮对话
     上下文一致。
   - **first-class platform name**：现在叫 "webhook"，没法在 cron job
     `deliver=xiaozhi` 这种地方引用，也没法被 `hermes channels` 列出。

## §1 Hermes plugin 加载机制（已 read）

Hermes (`uv tool install hermes-agent` v0.16.0) 扫 3 个目录：

1. **bundled** `<site-packages>/plugins/` — 上游自带，**别动**
2. **user** `~/.hermes/plugins/<name>/plugin.yaml` — ✨ **本项目用这条**
3. **project** `./.hermes/plugins/` — 需要 `HERMES_ENABLE_PROJECT_PLUGINS=1`

每个 plugin 必含 `plugin.yaml` (`kind: platform` 标识) + `__init__.py`
导出 `register(ctx)` 函数；ctx 实际是 `PluginContext`（定义在
`hermes_cli/plugins.py:289`）；`ctx.register_platform(...)` 写入
`gateway.platform_registry.platform_registry` 单例，gateway run 时实例化。

**最小参考**：`plugins/platforms/ntfy/` (593 LOC adapter + 60 LOC plugin.yaml)
和 `plugins/platforms/irc/` (968 LOC) — 都是单文件 adapter。

## §2 M3 拓扑

```
                          [ESP32 OttoRobot]
                          ↑ Opus audio + JSON + MCP frame
                          ↓
                ┌────────────────────────────┐
                │ xinnan-tech server (LLM)   │
                │  ↓ POST /v1/chat/completions│
                └────────────────────────────┘
                          ↓ SSE (delta) ↑ messages[]
                ┌────────────────────────────┐
                │ M2 openai-shim             │
                │  - DeepSeekBackend (LLM)   │
                │  - HermesBackend (fork)    │ ──HMAC POST──┐
                └────────────────────────────┘                │
                          ↑ M1 pipe (反向 tool)               │
                          │                                     ↓
                          │              ┌────────────────────────────────┐
                          │              │ Hermes gateway (webhook :8644) │
                          │              │  + ★ M3 XiaozhiAdapter ★       │
                          │              │  (replaces generic webhook)    │
                          │              └────────────────────────────────┘
                          │                              ↓ send()
                          │                              ↓
                          └─────[ M1 reverse channel ]───┘
                          (Hermes.send("show this on robot screen"))
```

## §3 send() 的 3 个候选路径 — 选 (b)

| # | 方案 | 优 | 劣 | 选择 |
|---|---|---|---|---|
| **(a)** | adapter.send → xinnan-tech outbound TTS API | 真发声 | xinnan-tech 没暴露此 API，要 fork | ❌ |
| **(b)** | adapter.send → M1 pipe → ESP32 MCP tool `show_text(kind=chat)` | M4 已实现 show_text；M1 pipe 本来就有；零新协议 | 视觉而非声音；用户得看屏幕 | ✅ **spike** |
| **(c)** | adapter.send → 缓存到 shim → 假装下一轮 SSE | 不需要新连接 | 跟 LLM call 耦合；时机不可控；hacky | ❌ |

**(b) 落地**：M4 已加 `self.otto.show_text("text", "chat")`（H024 done）
直接复用。M1 pipe 把 stdio MCP tool 暴露给 xinnan-tech → 调链
Hermes → M3 → M1 stdio → xinnan-tech tool → ESP32。

但 **M1 当前只有 echo_tool**（H015 done）；M3 落地前需要让 M1 知道
"ESP32 端有 show_text"，即 M1 注册一个 proxy stdio tool
`show_text_proxy(device_id, text, kind)` 转发给 ESP32。这是 M3 的子任务。

## §4 chat_id 设计

- **chat_id = ESP32 device_id = MAC address** (eg `ac:a7:04:30:91:78`)
- session_store 内每个 chat_id 维护一个 Hermes session（沿用 Hermes 默认
  逻辑，无需改）
- M2 shim 在 fork transcript 时已经在 webhook payload 带 device_id
  (H020 实测 webhook body 内含 `device_id`)，M3 adapter 拿来当 chat_id

## §5 M3 plugin 文件清单（H028 spike 目标）

```
hermes-xiaozhi-plugin/                     # 本项目内
├── pyproject.toml                         # 单依赖 httpx (Hermes 已有)
├── README.md                              # 装法 + env vars
├── src/hermes_xiaozhi/
│   ├── __init__.py                        # 导出 register
│   ├── adapter.py                         # XiaozhiAdapter(BasePlatformAdapter)
│   └── plugin.yaml                        # name=xiaozhi, kind=platform
└── tests/
    ├── test_register.py                   # register(ctx mock) 验通
    └── test_adapter_send.py               # send() → fake-mcp 验

# 安装到 ~/.hermes/plugins/xiaozhi 用符号链接（dev 期）：
ln -s $(realpath hermes-xiaozhi-plugin/src/hermes_xiaozhi) \
      ~/.hermes/plugins/xiaozhi
```

## §6 H028 spike 范围（最小可工作）

**Goal**：Hermes 启动看到 `Platform 'xiaozhi'` 注册成功 + 一个 e2e mock
test 验证 webhook IN + send OUT 两条路径。

**Stage A (sandbox-friendly)**：
1. 包骨架 + plugin.yaml + adapter.py 骨架
2. `register(ctx)` 写好，ctx mock 通过
3. `connect()` 启个 aiohttp server 监听 webhook (复制 ntfy adapter
   的 server 启动逻辑)
4. `send()` 写桩，先 print 不真发
5. 2 pytest case (register + roundtrip mock)

**Stage B (后续 H028.bis user-led)**：
- 真装 plugin 到 `~/.hermes/plugins/xiaozhi`
- `hermes gateway run` 看 platform 注册日志
- Shim env 改 `HERMES_TRANSCRIPT_URL=http://127.0.0.1:???/webhooks/xiaozhi`
  指向 adapter 而非 generic webhook
- ESP32 voice → Hermes session 自动 fork ✅
- TUI 输 `send xiaozhi:ac:a7... "hello"` → adapter.send 走桩 print ✅

**Stage C (M3 finish, H029)**：
- M1 加 `show_text_proxy` stdio tool
- adapter.send 接 M1 (httpx stdio? 还是新走 MCP HTTP transport?)
- e2e: TUI 让 Hermes 主动发"嗨" → 机器人屏幕弹"嗨"

## §7 Out of scope（明确不做）

- TTS 上行（Hermes 主动让机器人**说话**）：架构允许，但需 xinnan-tech 改
- 多 robot 支持：spike 只验单机 (`ac:a7:04:30:91:78`)
- session 持久化跨 hermes restart：用 Hermes 默认 session_store
- ack / retry / queue：spike 是 fire-and-forget
- 隐私 / 权限：device MAC 当 chat_id 是 "trusted single-tenant" 假设

## §8 风险

| 风险 | 概率 | 缓解 |
|---|---|---|
| Hermes plugin loader 不认 user dir 下符号链接 | 中 | spike 时若 fail 改用 `cp` |
| `BasePlatformAdapter` ABC 强约束 4 个 abstract method (`connect / disconnect / send / get_chat_info`)，spike 时漏了一个 → ImportError | 中 | adapter.py 第一版**全写**，body 全 `raise NotImplementedError` 也行 |
| webhook port 占用 (8644 已被 generic webhook 用) | 低 | adapter 自己选 8645 |
| Hermes 版本升级 break ABC | 低 | 钉死 v0.16.0 + 在 README pin |

## §9 H028 跟前 work 的关系

- 复用 H020 实测的 HMAC handshake + Hermes session spawn 行为
- 复用 H025 加好的 X-Hub-Signature-256 签名
- 复用 H024 加好的 `self.otto.show_text` MCP tool（Stage C）
- 不动 M2 shim (除 env URL 切换)
- 不动 xinnan-tech 任何文件

## §10 决策 log

- 2026-06-19 设计完，**送 H028 让 executor codex 跑 Stage A**
- 后续：H028.bis (user-led 真装 + Hermes 启动验)；H029 (M1 proxy + 真 send)
