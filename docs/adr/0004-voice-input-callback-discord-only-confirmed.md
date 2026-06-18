---
id: 0004
title: 确认 _voice_input_callback 为 Discord-specific，降级 ADR-0001 pitfall #4，关闭 Week 3 Day 16 hard-stop
status: active
created: 2026-06-18
activated: 2026-06-19
author: planner
supersedes:
---

## Context

ADR-0001 §"本项目特有 pitfall" #4 把 `_voice_input_callback` 是否
Discord-specific 列为本项目"最大未知 (🔥🔥)"，决定 M3 工作量从 8 天
还是 18 天，roadmap §Week 3 风险 1 给了"降级方案 B"作为兜底，并把
Day 16（Week 3 第 2 天）钉为"硬性确认日"。

Week 0 第 4 天（2026-06-18），由 executor 完成 handoff
[2026-06-16-upstream-code-reading-003](../handoffs/archive/2026-06-16-upstream-code-reading-003.md)，
落档 [docs/diagnoses/2026-06-16-voice-input-callback-discord-coupling.md](../diagnoses/2026-06-16-voice-input-callback-discord-coupling.md)
（verdict: **YES**，4 条代码证据）。

随后由 auditor 完成 [2026-06-18-upstream-code-reading-audit-006](../handoffs/archive/2026-06-18-upstream-code-reading-audit-006.md)：

> Outcome: **pass** · Recommendation: **accept** · verdict YES 独立成立（且被加强证据进一步强化）

具体加强证据：
- 关键证据 4（`gateway/run.py:8061-8067` 通用 VOICE path）独立核对通过
- 反向证据：**15+ 个 adapter 均 emit `MessageType.VOICE`**，这条 audit
  自己挖出来的旁证比诊断本身的论证更强
- `rg voice_input_callback` 在 `gateway/platforms/base.py` 0 命中、在
  10 个非-discord adapter 0 命中、全部命中限于 discord/adapter.py +
  gateway/run.py + tests
- 诊断引用的两个上游 commit（`426f321e` / `a1973e07`）经 line-aligned 核对一致

### Audit 提出的 6 个 minor issue 中的 1 个对本 ADR 有影响

**I6（M3 4-day 重估按 §Open questions 标 PARTIAL）**：

> 其中 "M1 → XiaozhiAdapter.handle_message 0.5 天" 暗设 M1 的 MCP 表面
> 会 emit transcript —— 但 xinnan 笔记自己只查到 tools/call 平面，没证
> transcript 是怎么出来的，是一个未验证的 wiring 跃迁。verdict YES 本
> 体不受影响，只是 cost premise 弱。

planner 接受 I6 评估：**4 天是诊断的乐观估算，本 ADR 不照搬**。M3 的
合理时间预算应该把"transcript 出口未验证"这一未知按 ~1-2 天 spike
预算计入。

## Decision

### 1. 降级 ADR-0001 pitfall #4

`_voice_input_callback` 已确认为 Discord-specific，但 Hermes 通用 voice
ingest path 已存在（adapter 内部完成 STT，自己构造
`MessageEvent(MessageType.VOICE)`，调 `handle_message()`），15+ adapter
已用此路径。

ADR-0001 pitfall #4 status 由 "🔥🔥 最大未知" → **"已解，已确认 + 已
有通用替代"**。原 #4 条目保留不删（按 ADR-0001 §"演化时机" 段：演进
留痕，不静默修改），本 ADR 即其 supersession 节点。

### 2. 关闭 Week 3 Day 16 hard-stop checkpoint

roadmap §"全程关键检查点"第 4 行 "Week 3 第 2 天 / 第 16 天 /
_voice_input_callback Discord-specific 已确认 → 立刻执行降级方案 B"
**整条作废**——因为：

- 已确认 = YES
- 但降级方案 B 不需要触发（通用 voice ingest 已存在）

→ Day 16 不再是硬节点。M3 按通用 path 直接开工。

### 3. roadmap §Week 3 §风险 1 + §降级方案 A/B 整段标 obsolete

roadmap §Week 3 §风险 1 的"降级方案 A（fork Hermes 通用化 callback）"
+ "降级方案 B（xiaozhi 只做下行 channel）"两条，由本 ADR 替代为单一
方案：

> **M3 直接走通用 `MessageEvent(VOICE)` path，不创建任何 callback wire。**
> XiaozhiAdapter 内部持有 transcript 入口（建议命名
> `_on_xiaozhi_transcript`，**不复用** `_voice_input_callback` 这个名字），
> 拿到 transcript 后构造 MessageEvent 直接调 `handle_message()`。

### 4. M3 时间预算修正：4 天 → 5-6 天（带 1-2 天 transcript 出口 spike）

按 audit I6 的 PARTIAL 警告。诊断报告里的 4 天估算依赖 "M1 / mcp-pipe
表面 emit transcript" 这个未验证假设，必须先 spike 才能定终值。

为此 planner 同步起一个轻量研究 handoff（待开）：

> **handoff: M1/mcp-pipe transcript 出口 spike**
> 目标：确认 xinnan-tech server / xiaozhi MCP接入点的哪个出口能让
> Hermes adapter 拿到 ASR 完整 transcript（而不是只有 tools/call 表
> 面）；spike 结果回灌进 M3 设计。
> 预算：1-2 天。在 Week 1 M2 开工前必须完成。

完成后 M3 时间预算定型（4 / 5 / 6 / 8 中选一），可能引出 ADR-0005。

### 5. ADR-0001 §"项目特有 pitfall" #4 末尾追加确认行

planner 后续在 ADR-0001 §"项目特有 pitfall" #4 末尾追加：

> **2026-06-18 确认**：诊断 verdict YES，audit pass；通用 path 已存在，
> 不触发降级方案 B。详见 [ADR-0004](0004-voice-input-callback-discord-only-confirmed.md)。

（这一行不是"修改原 pitfall"，是"在末尾追加确认事实"，符合 ADR-0001
§"演化时机" 段。）

## Consequences

### Positive

- 本项目最大未知（🔥🔥）在 Week 0 第 4 天解锁，比 roadmap 计划的 Day 16
  提前 12 天 —— Week 3 那个钉死节点消失
- M3 时间预算从 18 → 5-6 天，**Week 3 至少多出 1 周 buffer**，可以挪给
  Week 4 demo 打磨或某个场景二的精细化（如 `listen_ambient` 红 LED）
- roadmap §Week 3 §"降级方案 B" 整段作废 → docs 复杂度下降，少一条
  "答辩时怕被问到怎么解释"
- 三角色协作得到一次真实的"翻盘类诊断 + audit pass"验证 → 验证了
  ADR-0001 §"启用 auditor 的理由"是站得住的

### Negative

- M3 时间从 4 天 → 5-6 天，多出来的 1-2 天用在 transcript 出口 spike
  上 —— 不是诊断报告原始 4 天估算的"净 buffer"
- 关闭 Day 16 hard-stop 后失去一个 forcing function；如果 spike 揭示
  transcript 出口不存在（极小概率），届时已是 M3 中段，再退回降级方
  案 B 的成本比 Day 16 退回高 → **缓解**：transcript spike 在 Week 1
  开头做，**在 M2 还能改方向时就 spike 完**

### Trade-off

- 本 ADR 承担了 audit I6 的 PARTIAL 警告（4 天估算太乐观）：选择**不
  无视警告也不否定 verdict**，采取"verdict 接受 + cost 重估 +
  补 spike"的折中
- ADR-0001 pitfall #4 不删（演进留痕），新读者需多读一个 ADR 才能
  理解全貌；可接受，符合本项目"决策史可审计"的核心理念

## References

- 触发证据：
  - 诊断报告：@docs/diagnoses/2026-06-16-voice-input-callback-discord-coupling.md
  - 上游精读笔记：@docs/research-notes/hermes-discord-adapter.md
  - audit 结论：@docs/handoffs/archive/2026-06-18-upstream-code-reading-audit-006.md
  - 完成的 handoff：@docs/handoffs/archive/2026-06-16-upstream-code-reading-003.md
- 相关 ADR：
  - [ADR-0001](0001-adopt-agent-arch.md) §"本项目特有 pitfall" #4（本
    ADR 降级它；不静默修改）
  - [ADR-0003](0003-executor-runs-in-main-loop.md)（main-loop executor
    使本次诊断成为可能；从 sandbox 走不通）
- roadmap 影响：
  - @docs/roadmap.md §Week 3 §风险 1 + §"全程关键检查点" Day 16 行 →
    本 ADR active 后另起小 handoff 把 roadmap 这两段标 obsolete
- 上游 commit pin（本 ADR 决策时间点）：
  - hermes-agent: `426f321e84062e00fd5e6e9271aef48263cafffb`
  - xinnan-tech: `a1973e07b71e018199018060497c58cd45d5d387`
