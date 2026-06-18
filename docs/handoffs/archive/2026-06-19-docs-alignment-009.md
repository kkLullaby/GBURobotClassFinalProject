---
id: 2026-06-19-docs-alignment-009
from: planner
to: executor
status: done
parent:
created: 2026-06-19
artifacts:
  - CLAUDE.md
  - .claude/memory/shared/global-commands.md
  - .claude/memory/shared/tech-stack.md
  - docs/roadmap.md
  - README.md
---

## Objective

把 Week 0 期间 ADR-0002 / 0003 / 0004 落地后**仍跟现实不符的几处文档
描述**一次性对齐，所有改动都是**文字校对级**，不引入新观点、不改架构。
具体 6 处（顺序无所谓）：

1. **CLAUDE.md §仓库结构 + §Project Scope**：现在 `esp/xiaozhi-esp32/`
   确实是 submodule 了（004 done），描述本来就对，**只要核一遍 wording
   没歧义**；同时 `esp/esp-idf/` 已从 index 拿掉，描述里如有"submodule"
   字样改为"用户在 ~/ 下独立安装的 IDF（不入库）"
2. **`.claude/memory/shared/global-commands.md` §Git 工作流**：把
   `git submodule update --init --recursive` 之类的命令**现在真的能跑
   了**，把命令前后多余的"待 Week 0 跑通后回填"之类的占位删掉
3. **`.claude/memory/shared/global-commands.md` §Hermes 段**：把 005
   A.bis 落地后用的实际配置法 (≤6 行) 回填：`hermes config set provider/
   model`、`~/.hermes/.env` 写法、`hermes -z` one-shot 命令
4. **`.claude/memory/shared/tech-stack.md` §关键参考实现**：上游 commit
   pin 加进去（hermes-agent `426f321e`、xiaozhi-esp32-server `a1973e07`），
   作为本项目 Week 0 的"事实参考点"
5. **docs/roadmap.md §Week 3 §风险 1 + §"全程关键检查点" Day 16 行**：
   按 ADR-0004 §3 标 obsolete。具体做法：在两段开头插入一行 `> ⚠️
   OBSOLETE since 2026-06-18 — see [ADR-0004](adr/0004-voice-input-
   callback-discord-only-confirmed.md). M3 直接走通用 MessageEvent(VOICE)
   path；Day 16 hard-stop 已关闭。`原文**不删**（roadmap 是历史 doc，
   留 trace）
6. **README.md**：扫一遍看有没有"`esp/xiaozhi-esp32/` git submodule/
   gitlink"这种已经对齐的描述（核对一遍即可），以及加一段 ≤4 行的
   "本仓 clone 提示"——"`git clone --recurse-submodules ...`，或 clone
   后跑 `git submodule update --init --recursive`"（这段是 004 What I
   Did 里 executor 写好的草稿，他没入库，本任务把它入库）

## Constraints

- **纯文字 edit**：不改架构、不引入新结论、不动 ADR 本体（ADR 是历史
  文档，已经定型）
- **不改源码**（M1/M2/M3/M4 都不存在，scope 内只动 docs 和 CLAUDE.md
  和 shared/）
- 每处改动同时**保留原意**：roadmap §Week 3 obsolete 标注只是加 banner
  + ADR link，原文一字不删
- 不动 003 / 006 / 007 等 archived handoff
- 不 commit；最后让 `git diff --stat` 落到 What I Did，由用户审过再
  commit
- 错误处理纪律见 H010 §Error-handling discipline（cosmetic 错自己改、
  substantive 错才 block）

## Acceptance Criteria

- [ ] 上面 6 处全部 done，每处 What I Did 写明 "before / after / why"
      （≤3 行 each）
- [ ] `git diff --stat` 输出贴进 What I Did；预期 modified 文件 ≤5
      个（CLAUDE.md / .claude/memory/shared/global-commands.md / .claude/
      memory/shared/tech-stack.md / docs/roadmap.md / README.md）
- [ ] roadmap §Week 3 §风险 1 + Day 16 行的原文 byte-for-byte 保留，
      只在前面加 OBSOLETE banner（grep 验：原文那几句话仍能搜到）
- [ ] 不动任何 ADR 文件（ADR 是历史；要改架构得起新 ADR，不是本任务）
- [ ] 不引入新的 API key / secret 字面值（README / shared/ 里描述用
      `<your-key>` 占位即可）
- [ ] 不 commit

## Context Pointers

- @docs/adr/0002-week0-baseline-correction.md (这次对齐的动机源 #1, #2)
- @docs/adr/0003-executor-runs-in-main-loop.md (动机源 #2)
- @docs/adr/0004-voice-input-callback-discord-only-confirmed.md (动机
  源 #5; 看 §1 / §2 / §3，§4 跟本任务无关)
- @docs/handoffs/archive/2026-06-16-submodule-fixup-004.md (README
  草稿在 What I Did 段)
- @docs/handoffs/active/2026-06-16-hermes-bootstrap-005.md (实际跑通
  的 Hermes config 形态在 What I Did 段; A.bis 是用户手动跑的，
  005 完成后会把 config 形态写清楚)
- @CLAUDE.md @.claude/memory/shared/global-commands.md @.claude/memory/shared/tech-stack.md
- @docs/roadmap.md
- @README.md
- @.claude/rules/handoff-protocol.md
- @docs/adr/0003-executor-runs-in-main-loop.md (你跑主会话/codex)

## Out of Scope

- 不动 esp/xiaozhi-esp32/ 任何文件
- 不动 docs/adr/ / docs/handoffs/ / docs/contracts/ / docs/designs/
  下任何文件（你不是 planner）
- 不动 docs/research-notes.md / docs/architecture.md / docs/demo-
  script.md / docs/research-notes/ 目录任何内容
- 不引入新 markdown 文件
- 不改 ADR 本体
- 不改 INDEX.md（planner 维护）

## Assumption notes（planner 自标）

- [LOW] 005 A.bis 由用户在主会话完成；执行本任务时 005 应已 done。如
  仍 blocked，本任务 §3（Hermes config 回填）改为"基于 005 What I Did
  里 executor 探测到的 ~/.hermes/{config.yaml, .env} 形态做最小回填，
  并标注 'config persistence pending user A.bis'"
- [LOW] roadmap obsolete banner 形态选用 markdown blockquote，跟项目
  现有 ADR-0001 §pitfall 段风格一致

## Error-handling discipline

按 H010 §"Error-handling discipline" 全文执行（cosmetic 错自己改、
substantive 错才 block；改 status 前先问 "planner 看到第一句会不会是
'你只是打错命令'"）。

## Recovery

- 改坏：`git restore <file>` 单文件回滚；不要 reset --hard
- roadmap banner 插错位置：grep 找原文段头 + 重插

## For Auditor

不发 auditor。planner 自审，roadmap obsolete 标注最关键。

## Executor's Reading
### What I'll do
- 对 009 指定的 5 个文档做纯文字对齐：核 submodule/IDF wording，清理 shared 命令占位，回填 Hermes 实测命令，补 Week 0 upstream pin，在 roadmap 两处仅追加 obsolete banner，并在 README 增加 clone submodule 提示。

### Assumptions made
- [LOW] 009 明确列出的 5 个 artifacts 是本任务允许写入范围；不会修改 ADR、contracts、designs、archived handoff 或源码。
- [LOW] 用户说的“block 的部分附在新的报告里面”按本任务边界解释为：把最近 H012 blocked 摘要附在本 handoff 的 `What I Did` 报告里，不新建 markdown 报告文件。
- [LOW] Hermes 的最终事实以 archived 005 Final Resolution 和当前 shared/global-commands 中已回灌内容为准，不写任何真实 key。

## What I Did
- 1. `CLAUDE.md`：before = `esp/xiaozhi-esp32/` submodule 描述已对，`esp/esp-idf/` 仍像未来仓库路径；after = 补充 IDF 不入库、在 `~/esp-idf-5.5.2/` 独立安装；why = 对齐 ADR-0002/009 对 IDF 的现实边界。
- 2. `.claude/memory/shared/global-commands.md` Git 工作流：before = submodule 命令可用但注释偏泛；after = 明确“克隆后拉子模块”和“更新 xiaozhi-esp32 submodule 到上游 main”；why = 004 done 后 submodule 命令现在是真实工作流。
- 3. `.claude/memory/shared/global-commands.md` Hermes 段：before = 已有 DeepSeek 命令；after = 明确 key 经 `hermes auth add deepseek` 写入 `~/.hermes/state.db`，`.env` 当前未使用，保留 `hermes -z` one-shot；why = 对齐 005 Final Resolution，不写真实 key。
- 4. `.claude/memory/shared/tech-stack.md`：before = 只有参考实现名字；after = 增加 Week 0 参考 pin：Hermes `426f321e84062e00fd5e6e9271aef48263cafffb`、xinnan-tech `a1973e07b71e018199018060497c58cd45d5d387`；why = 固化 Week 0 事实参考点。
- 5. `docs/roadmap.md`：before = Week 3 风险 1 和 Day 16 hard-stop 仍像当前计划；after = 在两处前面追加 ADR-0004 obsolete banner，原风险文字和 Day 16 表格行未删除；why = roadmap 是历史 doc，保留 trace 但标明已作废。
- 6. `README.md`：before = 已有 clone submodule 命令；after = 标题改为“克隆本仓库（含 submodule）”，保留 `git clone --recurse-submodules ...` 和忘记时的 `git submodule update --init --recursive`；why = 把 004 README 草稿落入用户向文档。
- 用户要求的 blocked 附件：H012 当前 blocked 摘要已纳入本报告；阻塞点是 `idf.py set-target esp32s3` 在 CMake dependency solving 阶段无法访问 `https://components-file.espressif.com/components/78/esp-ml307.json`，未继续 `menuconfig/build`，未 flash/monitor。
- 验证：
  - `rg -n "OBSOLETE since 2026-06-18|_voice_input_callback Discord-specific 已确认|降级方案 B" docs/roadmap.md`：两处 banner、原降级方案 B、Day 16 行均可搜到。
  - `git diff --name-only -- docs/adr`：空输出，未改 ADR。
  - secret 形状扫描：`rg -n "sk-[A-Za-z0-9]|ms-[A-Za-z0-9]|AIza|xox[baprs]-|ghp_|github_pat_|DEEPSEEK_API_KEY=.*[^<>]|OPENAI_API_KEY=.*[^<>]|ANTHROPIC_API_KEY=.*[^<>]" ... || true` 空输出。
- `git diff --stat` 输出（当前仓库里 `.claude/`、`CLAUDE.md`、`docs/` 多数为 untracked，所以该命令只统计 tracked README 的既有 diff）：
  ```text
  README.md | 272 ++++++++++++++++++++++++++++----------------------------------
  1 file changed, 122 insertions(+), 150 deletions(-)
  ```
- 目标文件状态补充：
  ```text
   M README.md
  ?? .claude/memory/shared/global-commands.md
  ?? .claude/memory/shared/tech-stack.md
  ?? CLAUDE.md
  ?? docs/roadmap.md
  ?? docs/handoffs/active/2026-06-19-docs-alignment-009.md
  ```
- 未 commit；未修改源码；未新建报告文件；未动 `docs/contracts/`、`docs/designs/` 或 ADR 本体。
