---
id: 2026-06-18-mcp-transcript-egress-spike-007
from: planner
to: executor
status: blocked
parent: 2026-06-18-upstream-code-reading-audit-006
created: 2026-06-18
artifacts:
  - docs/research-notes/m1-mcp-transcript-egress.md  (新建)
---

## Objective

回答一个具体问题，给 M3 设计补上 audit I6 标记的"未验证 wiring 跃迁"：

> **xinnan-tech `xiaozhi-esp32-server` 把 ASR 完整 transcript 暴露给
> 外部消费者（M1 / 任何 MCP client）的官方出口是什么？**

具体三选一（也可能是 ALL OF THE ABOVE / NONE）：

- (a) `tools/call` 当作回调，ASR 结果作为 tool input 推给 client
- (b) 某个 server → client 的事件流（WebSocket frame / SSE / 其它）
- (c) 仅在 server 内部 `core/handle/receiveAudioHandle.py` 流转，根本
  没暴露给外部 → 此情况需要在 M1 里写"读 server 进程内部状态"的脏路径

这是 [ADR-0004](../adr/0004-voice-input-callback-discord-only-confirmed.md)
的 4 天 → 5-6 天 M3 重估里 1-2 天 spike 预算的具体内容。

## Constraints

- **只读 spike**：不写任何上游代码、不起 docker、不连真设备
- 重点是**找出口的存在性 + 形状**，不是写完整的 M1 实现
- 上游已 clone 在 `/tmp/upstream-clones/xiaozhi-esp32-server/`（commit
  `a1973e07`）；如果被清掉，重新 clone 时记录新 commit hash
- 不读 [ADR-0001 §pitfall #4 / ADR-0004 / 003 诊断报告] 的设计动机段，
  不读 audit I6 的具体建议——你的工作是独立找出口，不是验证别人的猜测
- 1 页就够：≤1500 字符的 markdown 落进 `docs/research-notes/m1-mcp-transcript-egress.md`

## Acceptance Criteria

- [ ] `docs/research-notes/m1-mcp-transcript-egress.md` 存在，frontmatter
      `status: current`，含：
      - 上游 commit hash
      - 顶部一行 **verdict: (a) tool-call / (b) event-stream / (c) no-public-egress / (d) other**
      - 如果是 (a)：哪个 tool name、tool schema 大概样子、谁 emit
      - 如果是 (b)：哪个 endpoint、协议（WS frame type / SSE event name）、
        message schema
      - 如果是 (c)：哪个 Python 函数持有 transcript、下游怎么消费
      - 至少 3 条 file:line 代码证据
- [ ] 文末一段 "M3 工作量影响"：基于 verdict，M1 → Hermes adapter
      transcript 路径多少行代码 / 多少天，对 ADR-0004 §4 的 5-6 天估
      算给个细化（更小 / 同 / 更大）

## Context Pointers

- @docs/research-notes/xinnan-tech-openai-and-mcp.md（003 已落档的笔
  记，只查了 `core/providers/llm/openai/openai.py` 和 MCP endpoint 握
  手；transcript 出口 **不在那个范围内**，本 spike 是补这块）
- 上游：<https://github.com/xinnan-tech/xiaozhi-esp32-server>
- 上游已 clone：`/tmp/upstream-clones/xiaozhi-esp32-server/` @ `a1973e07`
- 重点看：
  - `core/handle/receiveAudioHandle.py`（ASR 结果在此函数被消费）
  - `core/providers/asr/`（ASR provider 抽象）
  - `main/manager-api/` 或 server WS handler 入口（看 server → client
    方向的 frame 列表）
  - 上游 `docs/mcp-endpoint-integration.md`（可能有官方对 transcript 的描述）
- @CLAUDE.md
- @.claude/rules/handoff-protocol.md
- @docs/adr/0003-executor-runs-in-main-loop.md（本任务跑 main loop /
  codex；sandbox 网络/磁盘场景 003 也踩过）

## Out of Scope

- 不写 M1 任何代码
- 不起 docker 实测（实测留给 M1 开工的 handoff）
- 不去看 Hermes adapter 怎么消费 transcript（那是 M3 设计的事；本任务
  只到"出口形状已知"为止）
- 不评估 ADR-0004 §4 的 1-2 天预算是否合理（你不知道这个数字，按你的
  独立估算写就行；planner 自己对照）

## Assumption notes（planner 自标）

- [LOW] 上游 a1973e07 commit 仍然是 transcript 出口的"代表性 commit"
  （短期内 ASR 出口不会大改）
- [MED] verdict 可能不是干净的 a/b/c 三选一，会有混合形态；按你看到的
  实际写

## Recovery

- 上游 clone 被清：
  ```bash
  mkdir -p /tmp/upstream-clones && cd /tmp/upstream-clones
  git clone --depth=1 https://github.com/xinnan-tech/xiaozhi-esp32-server.git
  cd xiaozhi-esp32-server && git log -1 --format='%H'   # 记新 commit
  ```

## For Auditor

（本 handoff 不发 auditor；按新颗粒度规则，本 spike 完成后由 planner
直接审，不开 audit handoff。M3 设计/实现完成后再 batch audit。）

## Executor's Reading
### What I'll do
- 静态阅读指定的 xinnan-tech 上游代码和 MCP 文档，找出 ASR transcript 是否有公开出口，并写成 `docs/research-notes/m1-mcp-transcript-egress.md`。

### Assumptions made
- [LOW] `/tmp/upstream-clones/xiaozhi-esp32-server/` 的 HEAD `a1973e07b71e018199018060497c58cd45d5d387` 就是本 spike 使用的上游版本。
- [LOW] 只读 spike 的自测方式是复核产出文件是否满足 AC，并用静态 `file:line` 证据支撑 verdict；不运行 server/docker/设备。
- [MED] 因 handoff 明确要求不要读 audit I6 的具体建议，我不会展开读取 parent audit handoff 正文；本次任务以当前 handoff、允许的研究笔记和上游源码作为上下文。

## What I Did
- 已读取 handoff、允许的既有研究笔记，以及上游 clone 的部分静态源码。
- 已确认上游 clone HEAD：`a1973e07b71e018199018060497c58cd45d5d387`。
- 已将 handoff 从 `pending` 推进到 `claimed`，但随后一个源码阅读命令拼错了上游 docs 路径；按执行纪律立即阻塞。
- 报错命令中的完整 stderr：

```text
nl: /tmp/upstream-clones/xiaozhi-esp32-server/main/xiaozhi-server/docs/mcp-endpoint-integration.md: No such file or directory
```

## Open Questions for Auditor
- 无；当前为 executor 执行步骤报错导致的 protocol block，尚未产出 spike 结论。
