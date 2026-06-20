---
id: 0003
title: Executor 跑在独立 Claude Code 主会话，不通过 Task subagent
status: active
created: 2026-06-16
activated: 2026-06-19
author: planner
supersedes:
---

## Context

Week 0 第一波 3 个 handoff（[001](../handoffs/active/2026-06-16-submodule-fixup-001.md)、
[002](../handoffs/active/2026-06-16-hermes-bootstrap-002.md)、
后续重发的 [003](../handoffs/active/2026-06-16-upstream-code-reading-003.md)、
[004](../handoffs/active/2026-06-16-submodule-fixup-004.md)、
[005](../handoffs/active/2026-06-16-hermes-bootstrap-005.md)）
全部 blocked，且**根因相同**：

Claude Code 通过 Task tool 起的 subagent 沙箱比 ADR-0001 §"隔离强度"
描述的 "L3 全工具白名单" 要严：

- `/home/kk/` 整树只读 → 写不了 `~/.bashrc`、`~/.hermes/`、`~/.local/`、
  `~/.cache/`、`~/.config/`
- 主仓 `.git/index.lock` 写不了 → 跑不了 `git rm`、`git add`、
  `git submodule add`、`git commit`
- 用户 shell 配的 HTTP 代理（`127.0.0.1:7897`）在 sandbox 内不可达
  → 跑不了 `git clone github.com/...`、`pip install`、`docker pull`

这意味着 **subagent 形态的 executor 在本项目 80%+ 的工作上都会
block**：M1/M2/M3 装 Python 依赖、H1a IDF 下载、H2 docker pull、任何
涉及 git 提交的步骤都会撞墙。

ADR-0001 选 L3（"全工具白名单"）的本意是 executor 能跑大部分 dev 命令；
sandbox 实际比这严，是 spec 模型与本机 Claude Code 实现的差距，**不是
ADR-0001 选错梯度，是当时不知道实现侧的边界**。

### Bitter lesson

> 多角色架构里 executor 的"工具能力"不仅由 spec 的隔离梯度决定，**也由
> 宿主 (Claude Code) 给 subagent 的真实沙箱决定**。不验证就假设 L3
> 通用，会把所有依赖外网/家目录/git index 的工作都打到 blocked。

## Decision

本项目 executor **不通过 Task subagent 跑**，改为：

> **打开第二个 Claude Code 主会话（独立终端窗口、独立工作目录可同一），
> 在里面把 handoff prompt 当成主任务直接喂给 main loop。**

主会话没有上述沙箱限制——它跑在用户 shell 里，能写 home、能动 git
index、能用用户的代理。

planner、auditor、executor 仍按 ADR-0001 三角色 + 独立 memory 协作，
**只是 executor 不走 subagent 工具，而是用户在另一个窗口里"扮演"
executor 启动 Claude**。

### Operational changes

- bootstrap.md 已在 ADR-0001 时按 "三角色窗口" 描述协作，**实际就是
  本 ADR 的形态**，不需要改
- `.claude/agents/executor.md` 的内容（system prompt 模板）保留，作为
  "新开主会话时第一条系统消息"的参考；当 user 启动新会话时手动粘进去
  即可
- 主项目仓库 `.claude/settings.json` 不需要把 Task tool 给的 subagent
  类型对接到 executor 角色——本项目就不通过 Task 触发 executor

### Coverage scope

本决定**只覆盖本项目（ottagent / GBU 期末作业）**。是否回流 spec
仓库视后续多个 spec 用户项目是否复现而定（按 spec ADR-0002 #"复发性
bitter lesson 必须连同最初触发场景一起记录"原则，本 ADR 的 Context
段已记录最初触发场景）。

## Consequences

### Positive

- executor 工作真正能跑通，不再每发一个 handoff 就 1/3 概率 blocked
- 三角色边界靠"窗口隔离 + memory 目录隔离"维护，不靠 subagent 沙箱
  维护——后者本来就不该是 trust boundary
- bootstrap.md 的描述与现实对齐
- 后续 Week 1-4 不必为 "subagent 沙箱能做什么" 反复试错

### Negative

- 角色间隔离强度名义上比 ADR-0001 L3 描述的弱：window-based 隔离不强
  制 tool whitelist；理论上 executor 窗口里 Claude 可能误改 docs/
  （planner 的地盘）。**缓解**：靠 executor.md system prompt 显式禁止 +
  handoff 的 Out of Scope 段双重把关，且 git diff 用户自审
- 三个窗口同时跑时手动 context switch 成本上升（用户要记得"这条粘到哪
  个窗口"）

### Trade-off

- 如果未来 Claude Code 给 subagent 提供"信任级别"配置（能放开 home /
  git index / 代理），本 ADR 应该被 supersede 回到 ADR-0001 的 subagent
  形态——subagent 自动化程度更高
- 期间如果发现 window-based 隔离出现"executor 误改 planner 文件"的
  事故 ≥2 次，应升级到 worktree 隔离（ADR-0001 §"升级触发条件" 已有
  L5 worktree 兜底，与本 ADR 兼容）

## References

- 触发证据 1：[001 submodule-fixup blocked](../handoffs/active/2026-06-16-submodule-fixup-001.md) — git index read-only
- 触发证据 2：[002 hermes-bootstrap blocked](../handoffs/active/2026-06-16-hermes-bootstrap-002.md) — `uv tool install` cache read-only
- 触发证据 3：[004 submodule-fixup blocked](../handoffs/active/2026-06-16-submodule-fixup-004.md) — `.git/index.lock` read-only（即使 supersede 后仍 block）
- 触发证据 4：[005 hermes-bootstrap blocked](../handoffs/active/2026-06-16-hermes-bootstrap-005.md) — `~/.hermes/` 写不了 + 代理不可达
- 触发证据 5：[003 upstream-code-reading blocked](../handoffs/active/2026-06-16-upstream-code-reading-003.md) — `git clone github.com` 走不通本地代理
- 相关：[ADR-0001 §"隔离强度选择"](0001-adopt-agent-arch.md)
- 相关：[ADR-0002](0002-week0-baseline-correction.md)
- bootstrap：@bootstrap.md
