# ADR Index

> The project's decision history. Changing the architecture
> means writing a new ADR that supersedes the old; don't edit
> old ADRs directly.

## Active decisions

- [0001](0001-adopt-agent-arch.md) — 采纳 agent-loop-evolution-spec 三角色架构（2026-06-16）
- [0002](0002-week0-baseline-correction.md) — Week 0 基线修正：submodule 状态、首次烧录路径、本机烧录链路验证拆段（2026-06-16 created, 2026-06-19 activated）
- [0003](0003-executor-runs-in-main-loop.md) — Executor 跑在独立 Claude Code 主会话，不通过 Task subagent（2026-06-16 created, 2026-06-19 activated）
- [0004](0004-voice-input-callback-discord-only-confirmed.md) — 确认 _voice_input_callback 为 Discord-specific，降级 ADR-0001 pitfall #4，关闭 Week 3 Day 16 hard-stop（2026-06-18 created, 2026-06-19 activated）

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
