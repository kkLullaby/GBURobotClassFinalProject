# ADR Index

> The project's decision history. Changing the architecture
> means writing a new ADR that supersedes the old; don't edit
> old ADRs directly.

## Active decisions

- [0001](0001-adopt-agent-arch.md) — 采纳 agent-loop-evolution-spec 三角色架构（2026-06-16）
- [0002](0002-week0-baseline-correction.md) — Week 0 基线修正：submodule 状态、首次烧录路径、本机烧录链路验证拆段（2026-06-16 created, 2026-06-19 activated）
- [0003](0003-executor-runs-in-main-loop.md) — Executor 跑在独立 Claude Code 主会话，不通过 Task subagent（2026-06-16 created, 2026-06-19 activated）
- [0004](0004-voice-input-callback-discord-only-confirmed.md) — 确认 _voice_input_callback 为 Discord-specific，降级 ADR-0001 pitfall #4，关闭 Week 3 Day 16 hard-stop（2026-06-18 created, 2026-06-19 activated）
- [0005](0005-openai-compat-transcript-egress.md) — M3 transcript 走 OpenAI-compat `messages`（M2 升级为 transcript 入口）；M3 工作量 5-6 → 1-2 天（2026-06-19）
- [0006](0006-hermes-agent-backend-voice-replace-llm.md) — HermesAgentBackend：shim 把 LLM 整个换成 `hermes -z` subprocess，让 voice → tool-call → 喇叭真说出 hermes 处理结果；ADR-0005 plugin fork 仍兼容堆叠不被 supersede（2026-06-20）
- [0007](0007-hybrid-backend-router.md) — HybridBackend router：motor 类话走 raw DeepSeek + tools 透传（舵机真动），其余走 HermesAgentBackend（H033 高光）；ADR-0006 不被 supersede，只是 hybrid 模式让两路并存（2026-06-20）
- [0008](0008-lark-mcp-server-integration.md) — lark-mcp-server：把飞书 OpenAPI 暴露成 stdio MCP server 接入 hermes，让 voice "发个飞书消息"真到达；ADR-0007 hybrid 不动（2026-06-20）
- [0009](0009-lark-inbound-long-connection.md) — lark-event-listener：长连接接飞书 IM event → spawn hermes -z → 调 lark tool 回复，把飞书闭环成双向 channel；D1 spike 决定砍 xiaozhi_say（2026-06-20）

## Drafts pending review

<!-- list ADRs with status: draft, as a reminder to review -->

(none)

## Superseded / Rejected

<!-- collapsed zone, history preserved -->

(none)

---

## Conventions

- Numbering: 4-digit, monotonically increasing, **never reused**
- Filename: `NNNN-<kebab-case-title>.md`
- Status: draft → active → superseded-by-NNNN
- Never deleted (even when wrong, only marked superseded)
- One ADR per decision; don't bundle
