---
id: 0005
title: M3 transcript 出口走 OpenAI-compatible messages，不走 MCP-client callback
status: active
created: 2026-06-19
author: planner
supersedes:
---

## Context

### 触发

[H010](../handoffs/archive/2026-06-19-mcp-transcript-egress-spike-010.md) 出
verdict `(d) other`：xinnan-tech server **没有** "把 ASR 完整 transcript 通过
MCP-client callback 推出去" 这条路径。详细证据见
[research-notes/m1-mcp-transcript-egress.md](../research-notes/m1-mcp-transcript-egress.md)。

简言之 server 内部 ASR transcript 的实际去向有三条：

1. **device WS 帧** `{"type":"stt","text":<去标点 emoji>}` —— 是 display
   提示，不是完整 transcript（已被 `sanitize_text` 削过）
2. **LLM `messages`** —— `core/providers/llm/openai/openai.py:94-115` 用
   OpenAI SDK 把完整 user message 发往 `base_url`，这是**唯一含完整
   transcript 的外部出口**
3. **可选 manager-api 上报** `POST /agent/chat-history/report` —— 仅当 server
   配置 manage_api，本项目 minimal 模式不开

而 **MCP 接入点** (`mcp_endpoint/*`) **只是 tools/call 的反向通道**，
跟 transcript 无关。原本 [ADR-0001](0001-adopt-agent-arch.md) §pitfall #4
（_voice_input_callback Discord-only）已经在 [ADR-0004](0004-voice-input-callback-discord-only-confirmed.md)
里降级；本 ADR 进一步把它**关闭**：M3 不需要任何"callback hook"机制，
直接吃 OpenAI-compat 的 `messages` 即可。

### Project 拓扑变化

```
原计划（roadmap Week 1-2）：
   ESP32 ↔ xinnan-tech server  ←──(MCP 接入点)──  M1  ←──→  Hermes
                                                                 ↑
                                                      M3 hook? (未知)

实际（本 ADR 落地后）：
   ESP32 ↔ xinnan-tech server  ←──(OpenAI-compat /v1/chat/completions)──  M2 openai-shim  ←──→  Hermes
                                ↑                                                                   ↑
                          (MCP 接入点, M1, 用于反向 tool 调用)                                  (transcript 从 M2 流入)
```

**核心转变**：M2 不仅是"shim"，**它就是 transcript 的入口**。M1 仍存在但**作用变窄**——只负责
让 Hermes 的工具暴露给 server。M3 进一步收缩到"把 Hermes session 和 M2 接起来 + 把
ESP32 channel 注册进 Hermes 的 platform 列表"。

## Decision

1. **M3 transcript 出口**：走 OpenAI-compatible `/v1/chat/completions` (SSE)，
   **不**实现任何 MCP-client / `_voice_input_callback` 机制
2. **M2 升级为 transcript 入口**：openai-shim 不再只是"中转 LLM 调用"，
   它要在 `chat.completions.create` handler 里 **fork 出一份 transcript** 给
   Hermes（同时仍要回传 SSE 给 server 用作 LLM 输出）
3. **M1 工作量减少**：只需注册 ESP32 硬件能力 (MCP tools)，**不**做 transcript
   egress
4. **M3 工作量减少**：从原 5-6 天 ([ADR-0004 §3](0004-voice-input-callback-discord-only-confirmed.md))
   降到 **1-2 天**——只是 "Hermes session id ↔ ESP32 device_id" 映射 +
   `BasePlatformAdapter` 子类化的薄壳
5. **`features.mcp: true` 在 ESP32 hello 里保留**：因为 M4 还要走 §4.1
   `type:"mcp"` 子帧路径暴露硬件 tool

## Consequences

### Positive

- **M3 工作量 5-6 天 → 1-2 天**：~3 天节省，可挪给 M4 加更多硬件 tool 或答辩 polish
- **零私有协议**：M2 走 OpenAI Chat Completions 标准 SSE，可直接被任何
  OpenAI-compat 客户端 (Codex / Cursor / LangChain) 测试；这本身就是本项目
  对 Hermes 社区的核心 PR 价值
- **测试更容易**：M2 单测可直接用 `openai.OpenAI(base_url=...)` 验，不用
  起整套 ESP32/server
- **降低 ADR-0001 pitfall #4 风险残值**：原来还担心 "M3 需要私有 callback
  机制"，现在彻底无关

### Negative

- **M2 责任变重**：除 SSE 转换还要做 transcript fork + Hermes session
  注入。**M2 不再是 "1-2 文件"**（roadmap Week 1 估时仍准但描述要改）
- **transcript 经过 LLM 链路**：意味着 transcript 永远会经过 M2 才进 Hermes，
  M2 down → 机器人不能跟 Hermes 对话（也就不能跟机器人对话）。**单点**。
  缓解：M2 必须有 healthcheck + retry；M2 自身实现尽量简单 (< 200 LOC)
- **`/v1/chat/completions` 既是"LLM 出口"又是"transcript 入口"** 的双重用途
  可能在 demo 答辩里需要解释清楚，否则评委误以为是 hack
- **ESP32 端的 `type:"stt"` 帧仍发**：display 还会用它显示 user 输入，
  这部分代码我们不动；只是说**transcript 的"权威"副本走 OpenAI-compat**

### Trade-off

- **VS 改 xinnan-tech server 加 ASR event 通知**：那条路 ~1-2 天 server 端
  patch + 维护 fork。本 ADR 选 "完全不碰 server"，吃 OpenAI-compat 这条
  天然出口，更符合"零私有协议"的项目宗旨
- **VS 走 manage-api `/agent/chat-history/report`**：那条路要起 MySQL +
  redis（minimal 模式没装），打破 H011 选 minimal 的初衷
- **VS 让 Hermes 直接当 LLM provider（绕过 M2）**：Hermes 不是 OpenAI-compat
  服务器，强行套会写一坨胶水；M2 反正要写 shim，加点 transcript fork 成本
  最小

## References

- 上游证据：[research-notes/m1-mcp-transcript-egress.md](../research-notes/m1-mcp-transcript-egress.md)
  （H010 verdict 出处）
- LLM 调用链：[research-notes/xinnan-tech-openai-and-mcp.md](../research-notes/xinnan-tech-openai-and-mcp.md)
  §1 + §3 (M2 必须的 SSE 字段表)
- Contract：[contracts/api/v1/esp32-to-server-handshake.md](../contracts/api/v1/esp32-to-server-handshake.md)
  §4.3（说明 `type:"mcp"` 子帧和 MCP 接入点不冲突，M4 仍走子帧）
- Roadmap 对应段（**需要补 obsolete banner**，由后续 docs alignment handoff
  做）：
  - `docs/roadmap.md` §Week 1 §1.3 "shim 集成进 Hermes" — 升级描述
  - `docs/roadmap.md` §Week 3 §M3 工作量估算 — 5-6 天 → 1-2 天
- 相关 ADR：
  - [ADR-0001](0001-adopt-agent-arch.md) §pitfall #4 _voice_input_callback
  - [ADR-0004](0004-voice-input-callback-discord-only-confirmed.md) §3 已经
    把 Day 16 hard-stop 关了；本 ADR 进一步说明"为什么 callback 完全不需要"
- Related handoffs：
  - [H007 → H010](../handoffs/archive/2026-06-19-mcp-transcript-egress-spike-010.md)
    — 触发本决策的 spike

## Bitter lesson 候选

记一条："**先看 server 给 LLM 的 messages，再去找'专门的 callback 路径'**"。

Roadmap 写的时候默认了"transcript 出口必然有一个 dedicated channel"，
其实它就在 LLM 调用本身——只是大家没把 LLM call **本身**当成出口。
凡 ASR/voice → LLM 的系统，下次再问"transcript 在哪"，**第一站是 LLM provider
被调时的 messages 入参**，不是单独的 event 总线。
