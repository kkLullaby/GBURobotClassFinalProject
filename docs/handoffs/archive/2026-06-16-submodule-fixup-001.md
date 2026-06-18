---
id: 2026-06-16-submodule-fixup-001
from: planner
to: executor
status: blocked
parent:
created: 2026-06-16
artifacts:
  - esp/xiaozhi-esp32/
  - esp/esp-idf/
  - .gitmodules
---

## Objective

把 `esp/xiaozhi-esp32/` 从当前的"嵌套独立 git repo"转为指向上游
`78/xiaozhi-esp32` 的正式 git submodule（pin 在当前 HEAD `b392c63`），
并把 `esp/esp-idf/` 的 git index 残留清掉，使主仓库 `git status` 不再
显示 `D esp/esp-idf`。

## Constraints

- **不删 `esp/xiaozhi-esp32/` 工作树**，HEAD 必须仍是 `b392c63`，且
  `main/boards/otto-robot/` 下所有文件原样保留（这是 M4 工作区）
- **不删 `esp/esp-idf/` 目录本身**（盘上的是 5.3.2，用户自己处理；
  本 handoff 只清主仓库 git index 残留）
- 操作前必须先 `git stash` 或确认主仓库工作区干净（除 `.claude/`、
  `CLAUDE.md`、`bootstrap.md`、`docs/`、`.gitignore`、`README.md` 这
  些已知未提交项以外）
- `.gitmodules` 文件第一次创建后必须有正确的 `path` + `url` + `branch`
  字段
- 操作过程中**任何步骤报错立刻停下**，把当前状态贴进 What I Did
  段并改 frontmatter `status: blocked`

## Acceptance Criteria

- [ ] 主仓库根有 `.gitmodules`，内容包含 `[submodule "esp/xiaozhi-esp32"]`
      指向 `https://github.com/78/xiaozhi-esp32.git`
- [ ] `git submodule status esp/xiaozhi-esp32` 返回非空，输出中 commit
      hash = `b392c63`（前 7 位 OK）
- [ ] `cd esp/xiaozhi-esp32 && ls main/boards/otto-robot/` 仍能列出
      `otto_robot.cc`、`otto_movements.cc`、`otto_emoji_display.cc` 等
      14 个文件（操作前后用 `find . | sort | sha1sum` 对比 hash 一致）
- [ ] 主仓库 `git status` 不再显示 `D  esp/esp-idf`
- [ ] `esp/esp-idf/` 目录在盘上仍然存在（用户的旧 5.3.2，本 handoff 不动）
- [ ] 主仓库 `git status` 至少能干净到只有「.gitmodules 新增 + 一行
      submodule 指针更新」的程度（其他未跟踪文件如 `.claude/` 等保持
      不变）
- [ ] 写一段 5 行以内 README 段落到 What I Did，告诉以后的人"克隆本仓时
      要加 `--recurse-submodules`，或 clone 后跑 `git submodule update
      --init --recursive`"

## Context Pointers

- @docs/adr/0002-week0-baseline-correction.md（本 handoff 的动机，§不符 1）
- @docs/adr/0001-adopt-agent-arch.md（§Project Scope 解释为什么 esp/
  豁免、为什么 M4 反豁免）
- @CLAUDE.md（§仓库结构 + §Project Scope，本 handoff 完成后两段描述会
  和实际对齐）
- @.gitignore（已 ignore `esp/esp-idf/`、`esp/xiaozhi-esp32/build/`、
  `managed_components/`、`dependencies.lock`、`sdkconfig` 等）
- @.claude/memory/shared/global-commands.md（§Git 工作流 给的 submodule
  指令本 handoff 完成后才真的能跑）
- @.claude/rules/handoff-protocol.md（§Assumption-severity rubric）
- 上游仓库：<https://github.com/78/xiaozhi-esp32>
- 当前 HEAD 验证：在 `esp/xiaozhi-esp32/` 里跑 `git log --oneline -1`
  应得到 `b392c63 Add M5Stack StickS3 board support. (#2060)`

## Out of Scope

- 不动 `esp/esp-idf/` 目录里的任何内容（用户的 5.3.2 装在哪、卸不卸、
  换不换 5.5.2，是用户自己的事）
- 不修 CLAUDE.md / shared/global-commands.md 里"submodule"字样的精
  确度（本 handoff done 后另起小 handoff 对齐文档）
- 不创建 `esp/xiaozhi-esp32/` 的任何新文件（包括 sdkconfig；那是 H1a
  的事）
- 不解决 H1a / H1b / H2 / H3 / H4 涉及的任何问题
- 不动主仓库的 `.gitignore`（已经 ignore 了所有该 ignore 的东西）
- **不提交**任何 commit；只把 working tree 改成"提交时只会是一个
  clean 的 submodule 转换 commit"的状态，让用户自己审过再 commit

## Suggested Steps（非强制顺序，按你的判断）

提供一个参考流程，executor 可以按自己的理解调整：

1. 先备份当前 HEAD：`cd esp/xiaozhi-esp32 && git log --oneline -1 > /tmp/xz-head.txt`
   （把当前 commit hash 记下来）
2. **算 baseline hash**：`cd esp/xiaozhi-esp32 && find . -type f -not -path './.git/*' -not -path './build/*' -not -path './managed_components/*' | sort | xargs sha1sum | sha1sum > /tmp/xz-tree-before.sha1`
3. 回到主仓库根，看看 git 怎么"持有"现在这个嵌套 repo：
   `git ls-tree HEAD esp/xiaozhi-esp32`（应该是 commit object，gitlink 模式 160000）
4. 从主仓库 index 里临时 unstage 这个 gitlink：`git rm --cached esp/xiaozhi-esp32`
   （**关键：`--cached` 不删工作树**；如果忘了 `--cached` 会把 GB 级
   的源码全删，要 stop 立刻 status: blocked 找 planner）
5. 同样处理 `esp-idf`：`git rm --cached esp/esp-idf`（这本来就在 index
   里被标 D，rm --cached 把它从 index 彻底拿掉）
6. 用 `git submodule add` 重新建立 submodule：
   ```bash
   git submodule add -b main https://github.com/78/xiaozhi-esp32.git esp/xiaozhi-esp32
   ```
   如果报"目录已存在 / 已是 git repo"，按 git 的错误提示用 `--force`
   或先临时 `mv esp/xiaozhi-esp32 esp/xiaozhi-esp32.tmp`，submodule
   add 完拿 .git 子目录回来，再 mv 回来（执行前贴提示找 planner）
7. submodule add 后会在主仓库写入 `.gitmodules` 和一个新的 gitlink；
   检查这个 gitlink 是否 = `b392c63`，如果不是（比如自动 fetch 到了
   更新的 main HEAD），切回去：`cd esp/xiaozhi-esp32 && git checkout b392c63`，
   再 `cd ..` 在主仓库 `git add esp/xiaozhi-esp32`
8. **算 verify hash**：再跑一遍步骤 2 的 sha1sum，存 `/tmp/xz-tree-after.sha1`，
   `diff /tmp/xz-tree-before.sha1 /tmp/xz-tree-after.sha1` 必须为空
9. `git status` 看应该只有 `.gitmodules` (新增) + `esp/xiaozhi-esp32`
   (modified, new submodule) + `esp/esp-idf` (deleted from index)
   这三件事；如果还有别的源码文件变动 → status: blocked 报告
10. **不 commit**，把所有命令 + 输出贴到 What I Did

## Candidate Root Causes

不是 bug-class，无 root cause 段。

## Recovery（如果半路炸了）

- 任何时候 `git status` 显示 `esp/xiaozhi-esp32` 下源码文件被改/删：
  `cd esp/xiaozhi-esp32 && git checkout -- .` 把工作树还原；如果工
  作树本体被删了：`git clone -b main https://github.com/78/xiaozhi-esp32.git esp/xiaozhi-esp32 && cd esp/xiaozhi-esp32 && git checkout b392c63`
- 主仓库 `.git/` 不动；最差情况整个 esp/xiaozhi-esp32 重 clone 也行，
  代价就是再下一遍源码（不大）

## For Auditor

（本 handoff 不发 auditor；做完直接交回 planner 审）

## Executor's Reading
### What I'll do
- Preserve the existing `esp/xiaozhi-esp32/` working tree at `b392c63`, add the missing submodule metadata for upstream `78/xiaozhi-esp32`, remove the stale `esp/esp-idf` gitlink from the main index, and verify status/hash outputs without committing.

### Assumptions made
- [LOW] The existing uncommitted `.claude/`, `CLAUDE.md`, `bootstrap.md`, `docs/`, `.gitignore`, and `README.md` changes are the known allowed dirty state named in the handoff; I will leave them untouched.
- [LOW] `esp/xiaozhi-esp32` already has the desired working-tree HEAD `b392c63`, so the submodule pointer can be staged to that commit without changing files under the upstream tree.
- [MED] Network access is restricted in this executor environment, so if `git submodule add` would require a clone/fetch, I will use the existing local repo plus `.gitmodules`/index operations instead of fetching from GitHub.
- [MED] `main/boards/otto-robot/` currently lists 15 top-level files, not the handoff's stated 14; I will preserve the exact pre-operation tree hash and list the observed files in `What I Did`.

## What I Did
- Claimed the handoff, read its context pointers, and verified the current repo state before editing `.gitmodules`.
- Stopped before changing submodule metadata because the `esp/esp-idf` acceptance criteria conflict with Git's index/HEAD semantics in the current repository.
- Evidence:
  - `git ls-tree HEAD esp/esp-idf` returns `160000 commit 9d7f2d69f50d1288526d4f1027108e314e8c879f esp/esp-idf`, so `esp/esp-idf` is still present in HEAD.
  - `git ls-files --stage esp/esp-idf` returns no rows, so the `esp/esp-idf` gitlink is already absent from the index.
  - `git diff --cached --name-status -- esp/esp-idf` returns `D esp/esp-idf`, which is the staged deletion caused by that HEAD/index difference.
- Therefore, under the handoff's "do not commit" constraint, I cannot make `git status` stop showing `D esp/esp-idf` while also keeping `esp/esp-idf` removed from the index. The planner needs to choose whether to allow a commit, accept the staged `D` until the user's commit, or restore the `esp/esp-idf` gitlink for now.

## Open Questions for Auditor
- None; this handoff is blocked before implementation and does not go to auditor.

## Planner Resolution (2026-06-16)

Executor 的诊断**完全正确**：
- 我写的 AC #6（"`git status` 不再显示 `D esp/esp-idf`"）违反 git
  语义。`esp/esp-idf` 是 HEAD 里的 gitlink，只要不 commit，`D` 必然
  在 status 里。这正是本 handoff 想要的中间态。
- AC #3 的"14 个文件"是 planner 数错（实际 15），应该完全用 sha1sum
  对比，不写数字。
- 网络/沙箱限制：本 handoff 的某些步骤（`git submodule add` 需要
  fetch upstream）在受限 executor 里跑不了。

本 handoff 终结为 blocked。后续工作迁移到
[2026-06-16-submodule-fixup-004](2026-06-16-submodule-fixup-004.md)
（supersedes: 001），AC 已更正，并拆分用户 ↔ executor 的执行边界。
