---
id: 2026-06-19-mcp-transcript-egress-spike-010
from: planner
to: executor
status: done
parent: 2026-06-18-mcp-transcript-egress-spike-007
supersedes: 2026-06-18-mcp-transcript-egress-spike-007
created: 2026-06-19
artifacts:
  - docs/research-notes/m1-mcp-transcript-egress.md  (新建)
---

## Objective

同 [007](2026-06-18-mcp-transcript-egress-spike-007.md)（007 因 cosmetic error
被 blocked，本 handoff supersede 它并显式放大 error-tolerance）：

回答 **"xinnan-tech `xiaozhi-esp32-server` 把 ASR 完整 transcript 暴露
给外部消费者（M1 / 任何 MCP client）的官方出口是什么？"**

verdict ∈ {(a) tool-call / (b) event-stream / (c) no-public-egress /
(d) other}，至少 3 条 file:line 证据 + M3 工作量影响一段。

## What changed vs 007

007 接手后跑了一条上游 docs 路径**拼错**的 `nl` 命令 → executor 按
"任何步骤报错立刻 status: blocked" 字面规则停下。这是 planner 写
H004 / H005 时埋下的过严约束的遗症。

本版用 §Error-handling discipline 段把 substantive vs cosmetic 错的处
理分开，cosmetic 错应该自己改命令重试，不能阻塞整个 spike。

007 的 What I Did 段（including 那条拼错的 `nl`）留 trace；本 handoff
独立从头开始，**不**要求 executor 续上 007 的探索路径——给一个 fresh
start，避免 priming。

## Constraints

- **只读 spike**：不写任何上游代码、不起 docker、不连真设备
- 上游已 clone 在 `/tmp/upstream-clones/xiaozhi-esp32-server/`（commit
  `a1973e07`）；如果被清掉，重新 clone 时记录新 commit hash
- 不读 [ADR-0001 §pitfall #4 / ADR-0004 / 003 诊断报告 / 006 audit] 的
  设计动机段；不读 007 的 What I Did（避免被前一次未完成探索 priming）
- 1 页就够：≤1500 字符 markdown 落进 `docs/research-notes/m1-mcp-
  transcript-egress.md`
- 错误处理纪律见 §Error-handling discipline；不要因 cosmetic 错 block

## Error-handling discipline（**关键，本 handoff 区别于 007 的核心**）

- **substantive error**（命令成功执行后产生的语义错误：文件**真的不
  存在但你查过应该有**、权限拒绝、network refuse、git operation
  冲突、上游代码结构跟 003 笔记完全对不上） → status: blocked + 完
  整 stderr + 当前状态说明
- **cosmetic error**（你自己命令打错：路径拼错、引号缺一只、flag 名
  写错、shell quoting 问题、文件名记不全） → **不要 block**，自己
  改正命令重试，What I Did 加一行 "重试 N 次后用 <修正后命令>"，继
  续
- **路径不存在但你不确定是哪种**：先 `ls -la <父目录>` 看清楚再判断；
  父目录存在但文件名错 = cosmetic，父目录都没有 = substantive
- **重复同类 substantive error ≥3 次**（你已经改 3 次还在错同一个）
  → status: blocked，承认是 substantive
- 改 status 之前先问自己："如果 planner 看到这条 block，第一句话会
  不会是 '这只是你打错命令'？" yes → 不要 block

## Acceptance Criteria

- [ ] `docs/research-notes/m1-mcp-transcript-egress.md` 存在，frontmatter
      `status: current`，含：
      - 上游 commit hash
      - 顶部一行 **verdict: (a) tool-call / (b) event-stream / (c) no-
        public-egress / (d) other**
      - 如果是 (a)：哪个 tool name、tool schema 大概样子、谁 emit
      - 如果是 (b)：哪个 endpoint、协议（WS frame type / SSE event
        name）、message schema
      - 如果是 (c)：哪个 Python 函数持有 transcript、下游怎么消费
      - 至少 3 条 file:line 代码证据
- [ ] 文末一段 "M3 工作量影响"：基于 verdict，M1 → Hermes adapter
      transcript 路径多少行代码 / 多少天，对 ADR-0004 §4 的 5-6 天估
      算给个细化（更小 / 同 / 更大）

## Context Pointers

- @docs/research-notes/xinnan-tech-openai-and-mcp.md（003 已落档；只查
  了 `core/providers/llm/openai/openai.py` 和 MCP endpoint 握手；
  transcript 出口**不在那个范围内**，本 spike 是补这块）
- 上游：<https://github.com/xinnan-tech/xiaozhi-esp32-server>
- 上游已 clone：`/tmp/upstream-clones/xiaozhi-esp32-server/` @ `a1973e07`
- 重点看（**这些是参考方向不是穷举**，路径以你 `ls` 看到的实际为准）：
  - `core/handle/receiveAudioHandle.py`（ASR 结果在此函数被消费）
  - `core/providers/asr/`（ASR provider 抽象）
  - server WS handler 入口（实际路径在你 clone 树里找；可能是
    `core/connection.py` / `core/websocket.py` / `main/manager-api/` /
    `xiaozhi-server/` 等，**自己 `find . -name "*.py" -path "*handle*"`
    找**，不要赌路径）
  - 上游 docs 目录（可能是 `docs/` 或 `main/xiaozhi-server/docs/` 或
    `README.md` 引向 wiki；`find . -name "*.md" | head` 看）
- @CLAUDE.md @.claude/rules/handoff-protocol.md
- @docs/adr/0003-executor-runs-in-main-loop.md（main loop / codex 跑）

## Out of Scope

- 不写 M1 任何代码
- 不起 docker 实测（H008 干这个）
- 不看 Hermes adapter 怎么消费 transcript（M3 设计的事）
- 不评估 ADR-0004 §4 的预算是否合理

## Assumption notes（planner 自标）

- [LOW] 上游 a1973e07 commit 仍能代表当前 transcript 出口路径
- [MED] verdict 可能是混合形态（如 a + b 同时存在）；按看到的实际写
- [MED] 上游 docs 路径可能在不同子目录；spike 头 5 分钟应该用 `find`
  / `ls -R` 把代码树拓扑搞清楚，不要赌路径

## Recovery

- 上游 clone 被清：
  ```bash
  mkdir -p /tmp/upstream-clones && cd /tmp/upstream-clones
  git clone --depth=1 https://github.com/xinnan-tech/xiaozhi-esp32-server.git
  cd xiaozhi-esp32-server && git log -1 --format='%H'   # 记新 commit
  ```
- 找不到 ASR transcript 流的入口（ripgrep 全仓也没 hit "transcript"
  / "asr_result" / "user_text" / "stt_result"）：把搜索过的关键字 +
  树拓扑（`find . -type d -maxdepth 3`）贴 What I Did，status: blocked
  让 planner 重定方向

## For Auditor

不发 auditor。planner 自审，结合 ADR-0004 §4 细化 M3 时间预算。

## Executor's Reading
### What I'll do
- 静态阅读 xinnan-tech 上游 clone 的 ASR、WS、MCP endpoint 和相关 docs，判断 ASR transcript 是否有官方外部出口，并写入 `docs/research-notes/m1-mcp-transcript-egress.md`。

### Assumptions made
- [LOW] `/tmp/upstream-clones/xiaozhi-esp32-server/` 的 HEAD 可作为本 spike 的上游版本；实际 hash 会写入研究笔记。
- [LOW] 本任务的验证方式是静态代码证据复核，不运行 docker、不连设备。
- [LOW] `docs/research-notes/m1-mcp-transcript-egress.md` 是本 handoff 明确指定的新建产物，允许写入。
- [MED] 为避免 007 未完成探索 priming，我不会读取 007 的 `What I Did`；H010 已完整重述目标和新的错误处理纪律。

## What I Did
- 新建 `docs/research-notes/m1-mcp-transcript-egress.md`，frontmatter `status: current`，记录上游 commit `a1973e07b71e018199018060497c58cd45d5d387`。
- verdict 写为 `(d) other`：ASR transcript 没有官方 MCP-client callback；实际出口是 OpenAI-compatible LLM `messages`，另有设备 WS `type:"stt"` 展示帧和可选 `/agent/chat-history/report` 上报。
- 静态复核了上游 `core/providers/asr/base.py`、`core/handle/receiveAudioHandle.py`、`core/handle/sendAudioHandle.py`、`core/connection.py`、`core/providers/llm/openai/openai.py`、`core/handle/reportHandle.py`、`config/manage_api_client.py`、`core/providers/tools/mcp_endpoint/*` 的相关行号。
- 自检命令：
  - `sed -n '1,220p' docs/research-notes/m1-mcp-transcript-egress.md`
  - `wc -m docs/research-notes/m1-mcp-transcript-egress.md` → `1429`
- 未运行 docker、未连设备、未修改上游代码；本 handoff 写明不发 auditor。
