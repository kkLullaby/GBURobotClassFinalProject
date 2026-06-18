---
id: 2026-06-16-upstream-code-reading-003
from: planner
to: executor
status: done
parent:
created: 2026-06-16
artifacts:
  - docs/research-notes/hermes-discord-adapter.md       (新建)
  - docs/research-notes/xinnan-tech-openai-and-mcp.md   (新建)
  - docs/diagnoses/2026-06-16-voice-input-callback-discord-coupling.md (新建)
---

## Objective

落两份**可口述**的上游代码精读笔记 + 一份**早期诊断报告**：

1. `docs/research-notes/hermes-discord-adapter.md`：把 Hermes 的
   `plugins/platforms/discord/adapter.py`（或等价文件）读完，能用 1
   分钟口述"VoiceReceiver 如何处理音频帧、消息回调如何注入 agent
   loop"
2. `docs/research-notes/xinnan-tech-openai-and-mcp.md`：把 xinnan-tech
   `xiaozhi-esp32-server` 的 `core/providers/llm/openai/openai.py`
   + `docs/mcp-endpoint-integration.md` 读完，能解释"`base_url` 替换
   点"和"MCP 接入点握手流程"
3. `docs/diagnoses/2026-06-16-voice-input-callback-discord-coupling.md`：
   **明确回答** `_voice_input_callback`（roadmap 第 16 天的 🔥🔥 风险）
   是不是 Discord-specific。这是本项目最大未知，把判断提前到 Week 0
   出结论 → ADR-0001 pitfall #4 的"高方差未知"在 Week 0 末就能解锁

## Constraints

- **只读，不动任何上游代码**。所有读到的内容用本仓库内的 markdown
  文件落档，不在上游目录写 patch
- 3 份文档总长不超过 1500 字 / 文件；超长说明你在抄代码而不是消化
- 落档路径必须严格按 artifacts 段；如果 Hermes 把 discord adapter
  放在别处（如 `hermes/plugins/...` 而不是 `plugins/platforms/...`），
  在文档里写清楚**实际看的是哪个文件 + 哪个 commit / branch**
- 诊断报告必须给出 **YES Discord-specific / NO 通用 / PARTIAL** 三档
  明确判断，并附 ≥3 条代码侧证据（行号/函数名/类型签名）
- 看不懂或上游仓库被改了结构、找不到对应文件 → status: blocked，把
  实际找到的文件结构贴到 Open Questions

## Acceptance Criteria

- [ ] `docs/research-notes/hermes-discord-adapter.md` 存在，包含
      - 实际读的文件路径（含 commit hash 或读取时间）
      - 关键类/函数清单（≤10 个）+ 一句话作用
      - "VoiceReceiver → 音频帧 → agent loop"的数据流图（ASCII 即可）
      - 标注哪些点**像是 Discord-specific**（依赖 `discord.py` 的某个
        类型 / Voice Gateway WS 协议字段 / Opus 解码器 API 等）
- [ ] `docs/research-notes/xinnan-tech-openai-and-mcp.md` 存在，包含
      - `core/providers/llm/openai/openai.py` 关键路径（base_url 是
        在哪行读、SSE chunk 解析在哪个函数、failure path 是什么）
      - MCP endpoint 握手序列（client hello / auth token / tools/list
        / tools/call 各一步是什么）
      - 一份**字段对照表**：xinnan-tech 期望的 SSE chunk JSON schema
        vs OpenAI 官方 streaming 文档；标出哪些字段是 strict 哪些可
        以缺失（这是 roadmap 风险 §1.2 SSE 严格对齐的预研）
- [ ] `docs/diagnoses/2026-06-16-voice-input-callback-discord-coupling.md`
      存在，frontmatter 含 `verdict: YES | NO | PARTIAL`，body 必须有
      - 至少 3 条代码证据（file:line 引用形式）
      - "如果是 YES，roadmap 降级方案 B 的成本估算"或"如果是 NO，怎
        么把它接到 xiaozhi 音频流"的初步思路一段
- [ ] 三份文档的 frontmatter 都有 `status: current` 或 `status: draft`
      (诊断报告 status: current；笔记 status: draft 都行)
- [ ] 不修改 `docs/research-notes.md`（注意它是单文件，不是目录；本
      handoff 创建的是**`docs/research-notes/` 新子目录**下的两份新
      文件，**避免**冲突）

## Context Pointers

- 上游 Hermes：<https://github.com/NousResearch/hermes-agent>，重点看
  `plugins/platforms/discord/` 整个目录（CLAUDE.md / tech-stack 也指
  名要抄这个）
- 上游 xinnan-tech：<https://github.com/xinnan-tech/xiaozhi-esp32-server>
  重点看：
  - `core/providers/llm/openai/openai.py`
  - `docs/mcp-endpoint-integration.md`
  - （可能也要瞥一眼）`core/providers/asr/` 找到 ASR 触发处
- @docs/architecture.md（§Hermes channel 抽象 / §xinnan-tech 选型）
- @docs/roadmap.md（§Week 3 风险 1 + §Week 0 §0.6 §0.7）
- @docs/adr/0001-adopt-agent-arch.md §"本项目特有 pitfall" #4 / #5 / #7
- @.claude/memory/shared/tech-stack.md（§关键参考实现 段）
- `_voice_input_callback` 是 ADR-0001 pitfall #4 名字；它在 Hermes 哪
  里、是不是 Discord-specific 是本任务的核心问题

## Out of Scope

- 不动上游代码（只读）
- 不写 M2 openai-shim 的任何 spike 代码（这是 H 系列后续 handoff 的事）
- 不去碰 Hermes 的 MCP server 模式（那是 Week 2 M1 的事）
- 不写完整的 SSE chunk 实现，只写**调研结论**（哪些字段必须、哪些不
  必须）
- 不去重新评估 ADR-0001 的整体决策，本任务只产新证据，由 planner 决
  定要不要起新 ADR

## Candidate Root Causes

不是 bug-class，无 root cause 段。

## Suggested Steps

1. 在 `/tmp/upstream-clones/` 下 clone 两个上游 repo（**不放进本仓
   库**，临时阅读用），记下 clone 时的 commit hash
2. 先读 Hermes，重点：
   - `find . -path '*platforms/discord*' -name '*.py'`
   - 找 `voice_input_callback` 字面量出现位置（`rg -i voice_input_callback`），
     看它在哪定义、被谁调用
   - 看是否在 `base.py` / `abstract.py` 之类的抽象类里也有签名（→ 通用），
     还是只在 discord 子目录里（→ Discord-specific）
3. 写 `hermes-discord-adapter.md`
4. 切到 xinnan-tech，看 OpenAI provider + MCP endpoint 文档
5. 写 `xinnan-tech-openai-and-mcp.md`
6. 综合两边证据写 diagnoses 报告，给 verdict
7. 若 verdict = YES（Discord-specific），在报告末尾加一段"对 ADR-0001
   pitfall #4 的影响 + 是否建议提前启动 roadmap 降级方案 B 的讨论"，
   **不**自己决定走不走 B，只列证据让 planner 起 ADR

## Assumption notes（planner 自标）

- [MED] `_voice_input_callback` 这个字面名字源自 ADR-0001，可能上游
  改过名字 / 拆过函数。executor 要按"语义"搜（任何处理音频→触发 agent
  的回调），不只搜字面
- [LOW] 上游可能要 auth 才能 clone（一般是 public，没问题）

## For Auditor

（本 handoff 不发 auditor；diagnoses 报告由 planner 审完决定要不要
起新 ADR）

## Executor's Reading
### What I'll do
- I will clone/read the two upstream repositories under `/tmp/upstream-clones/`, inspect Hermes Discord voice ingestion and xinnan-tech OpenAI/MCP paths read-only, then create the three requested markdown artifacts with concise evidence and a clear `YES` / `NO` / `PARTIAL` verdict.

### Assumptions made
- [LOW] Creating `docs/research-notes/` as a directory is intended even though `docs/research-notes.md` already exists as a separate file; I will not modify the existing single-file notes.
- [LOW] Existing dirty/untracked project scaffolding is unrelated to this handoff and should be left untouched except for the handoff, index, and the three requested docs.
- [MED] Upstream symbol names may have changed, so I will search both literal names and semantic audio-to-agent-loop paths before deciding the verdict.
- [MED] GitHub clone/network access may fail in this executor environment; if either clone fails, I will stop, mark blocked, and record the exact command/stderr.

## What I Did
- Claimed the handoff and recorded Executor's Reading.
- Prepared the requested temporary clone root under `/tmp/upstream-clones/`.
- Stopped on the first upstream clone failure:
  ```text
  $ mkdir -p /tmp/upstream-clones && git clone https://github.com/NousResearch/hermes-agent.git /tmp/upstream-clones/hermes-agent
  Cloning into '/tmp/upstream-clones/hermes-agent'...
  fatal: unable to access 'https://github.com/NousResearch/hermes-agent.git/': Failed to connect to 127.0.0.1 port 7897 after 0 ms: Could not connect to server
  ```
- Blocked reason: executor environment cannot reach GitHub through the configured local proxy (`127.0.0.1:7897`), so the required `/tmp/upstream-clones/` read-only upstream clones cannot be created here.
- I did not modify upstream code, did not create the three research/diagnosis artifacts, and did not modify `docs/research-notes.md`.

## Open Questions for Auditor
- None; this handoff is blocked before artifact creation and does not go to auditor.

—— 第二次尝试（main loop）——

## What I Did (run 2, main-loop executor, 2026-06-18)

Environment: main Claude Code session (per ADR-0003); user's local proxy
`http://127.0.0.1:7897` reachable directly from this shell. Pre-flight
proxy check passed (`curl -sI https://github.com` HTTP/2 200).

- Set status `blocked → claimed → done` on this handoff (frontmatter only;
  prior body sections preserved per "append only" rule).
- Cloned both upstream repos read-only into `/tmp/upstream-clones/`
  (not inside the project tree):
  - `NousResearch/hermes-agent` @ `426f321e84062e00fd5e6e9271aef48263cafffb` (main, 2026-06-18 13:09 +0530)
  - `xinnan-tech/xiaozhi-esp32-server` @ `a1973e07b71e018199018060497c58cd45d5d387` (main, 2026-06-18 16:57 +0800)
- Verified `_voice_input_callback` literal hits exist (Hermes: 3 sites in
  `plugins/platforms/discord/adapter.py`, 4 sites in `gateway/run.py`,
  tests aside). Confirmed it is **not** declared on the base class
  (`rg voice_input_callback gateway/platforms/base.py` → 0 hits) and not
  used by any other adapter (`rg -l voice_input_callback plugins/platforms/`
  → only `discord/`). Semantic search ("audio → STT → ingest") also
  pulled up the *generic* path `gateway/run.py:8061-8067` +
  `adapter.handle_message(MessageEvent(VOICE))`, which became evidence 4.
- Read the OpenAI provider end to end (178 lines; `base_url` site, SSE
  consumption path, function-call streaming, failure path) and the MCP
  endpoint handshake (`mcp_endpoint_handler.py` + integration doc),
  recording the 3-step handshake sequence (`initialize` id=1 →
  `notifications/initialized` → `tools/list` id=2) and the WS URL
  (`ws://<server>:8004/mcp_endpoint/mcp/?token=…`).
- Created project directory `docs/research-notes/` (new — distinct from
  existing single file `docs/research-notes.md`, which is untouched;
  md5sum unchanged before/after = `0fc468b4992c7b22bd0ae12e6f7eea89`).
- Created the three artifacts (sizes within budget; max ≈5.7 KB / 160 lines):
  - `docs/research-notes/hermes-discord-adapter.md` (status: draft)
  - `docs/research-notes/xinnan-tech-openai-and-mcp.md` (status: draft)
  - `docs/diagnoses/2026-06-16-voice-input-callback-discord-coupling.md` (status: current, **verdict: YES**, 4 evidence blocks)
- Updated `docs/handoffs/INDEX.md` (moved this entry from Active → Recent
  done).
- Did **not** modify any upstream code; did **not** modify
  `docs/research-notes.md`; did **not** touch
  `esp/xiaozhi-esp32/` (read-only scope respected).

## Open Questions for next role
- Verdict is `YES` (Discord-specific) with 4 code citations. Diagnosis
  recommends *not* triggering roadmap "降级方案 B" because the generic
  inbound voice path (`MessageEvent(VOICE)` → `handle_message()`) is
  available — net M3 cost re-estimated at ~4 days, not 18.
- planner: decide whether to write a new ADR that supersedes /
  closes ADR-0001 pitfall #4, and whether to retire the Week 3 risk-1
  hardening node accordingly.
- A `to: auditor, type: review` handoff is queued (id
  `2026-06-18-upstream-code-reading-audit-006`) so the diagnosis verdict
  + evidence can be independently checked before planner acts on it.
