---
id: ADR-0006
title: voice-driven Hermes-as-LLM (HermesAgentBackend) 替换 DeepSeek 直答
status: active
date: 2026-06-20
supersedes: null
superseded_by: null
---

## Context

ADR-0005 把 transcript 出口定位在 OpenAI-compat `messages`（shim 是 transcript
**入口**），HermesBackend 把每轮对话**单向 fork** 给 Hermes plugin webhook,
plugin → hermes agent → adapter.send → sidecar → ESP32 屏幕显字。

H030 + H030.bis 实测发现两个限制:

1. **屏幕显字这条 dispatch 链**走 sidecar → mcp_endpoint(/mcp/) → ESP32 的
   路径不通, 因 `/mcp/` 注册角色是 "MCP 服务器", sidecar 不能反向发
   `tools/call` 给 ESP32 端 (bitter lesson #27).
2. **plugin webhook fork** 走通了, 但喇叭说的是 DeepSeek 直答 (xinnan-tech
   LLM provider 路径), hermes 的回复只能到 (不通的) 屏幕路径 → 用户感知不到
   hermes 在做事.

但 H033 实测意外发现一条**更直接的链路**: 把 openai-shim 的 LLM backend 整个
**替换** 成 hermes-z subprocess. xinnan-tech 调 shim 的 /v1/chat/completions
不再调 DeepSeek, 而是 spawn `hermes -z PROMPT` → hermes agent 真用 tool
(shell/file/browser/MCP servers) 完成任务 → stdout 流回喇叭 → 用户听到的
就是 hermes-with-tools 处理后的结果.

## Decision

**采纳 HermesAgentBackend 作为项目最终物理形态的主链路**:

```
ESP32 voice → STT (xinnan-tech ASR)
            → docker server LLM call
            → openai-shim /v1/chat/completions
            → HermesAgentBackend.stream_response()
                ↓ asyncio.create_subprocess_exec
              'hermes -z PROMPT --yolo --accept-hooks'
                ↓ (hermes agent 循环, 内含 tool-call: shell/file/browser/...)
              stdout (纯文本回复)
                ↓ chunked SSE deltas
            → docker server TTS
            → ESP32 喇叭 真说
```

**实测延迟**: 5-25s (取决于是否调 tool); xinnan-tech timeout 默认 30s+ 兜得住.

**实测验证 (2026-06-20 12:30)**:
- voice "帮我看看 final 文件夹里面有什么目录" (411.35s)
- 喇叭真说 (421.36s, +10s): "final文件夹里有五个目录: docs文档、esp固件、
  hermes小智插件、openai-shim接口层、还有xiaozhi-mcp-adapter适配器"
- 端到端 ~20s; hermes 真跑 `ls /home/kk/code/robot_class/final_pro_xiaozhi_robot/`
  + DeepSeek 总结为口语化中文.

## Why this beats ADR-0005 plugin-webhook fork for the demo

| 维度 | ADR-0005 fork (HermesBackend) | ADR-0006 LLM-replace (HermesAgentBackend) |
|---|---|---|
| 用户感知 | 喇叭说 DeepSeek 直答, hermes 仅记 transcript | 喇叭直接说 hermes 处理后的结果 |
| Tool-call | hermes 调 tool 后 → adapter.send → 屏幕 (现 dispatch 挂) | hermes 调 tool 后 → stdout → 喇叭 (通) |
| Latency | DeepSeek 2-4s | hermes 5-25s (含 tool) |
| Demo 张力 | "机器人在听" | "机器人在为我做事" |
| 答辩主张 | xiaozhi → hermes 旁路 | xiaozhi = hermes agent 物理化身 |

## Consequences

### Positive

- **答辩高光成立**: "对机器人讲话, 它真用电脑的工具帮你做事." 不再是
  "智能音箱 + DeepSeek".
- **后端无关性证明**: hermes 内部的 LLM provider/tool 都是可配的, 不绑
  DeepSeek/不绑特定 MCP server.
- **拓扑创新落地**: ESP32 = hermes 的 voice channel, 跟 hermes 的
  discord/whatsapp channel 平级.

### Negative / 待 polish

- **No conversation memory**: 当前每次 voice 起一个新 hermes session;
  下一步用 `hermes -z --continue <id>` 按 chat_id (xiaozhi:MAC) 串 session.
- **Latency 上限**: hermes 调 tool 链可能 10+ s; 用户体验上需要在 ESP32
  端加 "正在思考..." 占位音 (M4 polish).
- **HermesBackend (ADR-0005) 仍可堆叠**: 现实现是 `HermesAgentBackend` 替
  内层 LLM, `HermesBackend` transcript fork 仍可包外层, 让 plugin 收到
  额外副本. ADR-0005 不被 supersede, 只是不再是主链路.
- **屏幕显字 dispatch 链 (H030.bis bitter lesson #27)** 留作 H034 polish
  (sidecar 改走 /call/ 或绕 mcp_endpoint 直发 xinnan-tech).

### Bitter lessons absorbed

- **#28**: DeepSeek key 单一来源 = docker `data/.config.yaml`, command
  template 直接 grep 取, 不让 user 手 paste 占位符.
- **#29**: voice→hermes-z 比 voice→fork→hermes 更直接, 这才是项目最终形态.

## Implementation

- File: `openai-shim/src/openai_shim/hermes_agent_backend.py` (~115 LOC)
- Env switch: `OPENAI_SHIM_BACKEND=hermes_agent`
- Env vars: `HERMES_BIN` (default `hermes`), `HERMES_AGENT_TIMEOUT_S` (60),
  `HERMES_AGENT_CHUNK_SIZE` (20)
- Hermes flags: `--yolo --accept-hooks` (TTS 模式不能交互确认)
- Prompt wrap: 强制"最多 80 汉字纯口语无 markdown" (TTS 不读长 markdown)

## References

- commit a141541 (HermesAgentBackend)
- commit 07c62f4 (M1 H031 sidecar 真接 pipe)
- @docs/handoffs/active/2026-06-20-m3-physical-esp32-loop-030bis.md (实测)
- @docs/adr/0005-openai-compat-transcript-egress.md (前置, 仍 active)
