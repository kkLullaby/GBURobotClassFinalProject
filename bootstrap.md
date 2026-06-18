# Bootstrap Manual — xiaozhi-robot

> 三角色 agent 协作的启动手册。
> 架构决策见 [docs/adr/0001-adopt-agent-arch.md](docs/adr/0001-adopt-agent-arch.md)。
> 规范来源：[`agent-loop-evolution-spec`](https://github.com/kkLullaby/Multi-agent_collaboration_workflow_design_specifications)（本地：`/home/kk/code/project/Multi-agent_collaboration_workflow_design_specifications/`）。

---

## 第一次启动（开 planner 窗口）

planner 是入口角色 —— 它接你的需求、设计、写 handoff 给 executor，
也起草 ADR。

1. 新终端 `cd /home/kk/code/robot_class/final_pro_xiaozhi_robot`
2. `claude`（fast 模式可选：进会话后 `/fast`）
3. 给它一个**进入角色**的开场白：

```
You are this project's planner. Read these files in order, then wait for my first task:

1. .claude/agents/planner.md          — your role definition
2. CLAUDE.md                           — project contract
3. docs/adr/0001-adopt-agent-arch.md  — why we adopted this arch
4. docs/handoffs/INDEX.md             — current handoff state
5. docs/adr/INDEX.md                  — decision history

After reading, summarize in 3 bullets: (a) your role boundaries, (b) what's
in/out of scope per CLAUDE.md, (c) the top pitfalls you must remember from
ADR-0001.

Do NOT start any task until I send you the first one.
```

4. planner 回完总结后，把你的第一个真任务发给它。  
   通常 Week 0 的第一任务是："给 M0（xinnan-tech docker 起步）写一份
   handoff 给 executor"。

---

## 开 executor 窗口

executor 接 planner 的 handoff 实施，写测试，最后开一份 to: auditor
的 review handoff。

1. 新终端，**同一项目根目录**
2. `claude`
3. 开场白：

```
You are this project's executor. Read these files in order, then wait for my
handoff path:

1. .claude/agents/executor.md         — your role definition
2. CLAUDE.md                           — project contract
3. .claude/rules/handoff-protocol.md   — handoff protocol
4. docs/handoffs/INDEX.md              — current handoff state

After reading, summarize in 3 bullets: (a) your tool boundaries, (b) what's
in/out of scope (note: esp/xiaozhi-esp32/ is read-only EXCEPT
main/boards/otto-robot/ which is your M4 work area), (c) the assumption
severity protocol (LOW/MED/HIGH).

Then wait. I'll paste a handoff path next.
```

4. 等 planner 把 handoff 路径（`docs/handoffs/active/<id>.md`）甩给你后，
   你复制粘贴到 executor 窗口让它开工。

---

## 开 auditor 窗口

auditor 黑盒验收 executor 的产出。它**不能编辑**任何文件（工具白名单
只有 Read/Bash/Grep/Glob），只能往 handoff 追加 Verdict。

1. 新终端，**同一项目根目录**
2. `claude`
3. 开场白：

```
You are this project's auditor. Read these files in order, then wait for my
handoff path:

1. .claude/agents/auditor.md          — your role definition (3 modes)
2. CLAUDE.md                           — project contract
3. .claude/rules/handoff-protocol.md   — handoff protocol
4. docs/rubrics/general.md             — default evaluation rubric

After reading, summarize in 3 bullets: (a) what you do NOT read in a handoff
and why (fresh perspective discipline), (b) your three modes
(review/arbitrate/diagnose) and how you decide which one, (c) what's the ONE
thing you absolutely cannot do (mechanism-enforced).

Then wait. I'll paste a handoff path next.
```

4. 等 executor 完工后开的 to: auditor handoff 路径，复制粘贴到 auditor
   窗口。

---

## 三角色协作循环

```
用户需求
   ↓
planner 窗口
   ├─ 读相关代码/ADR/历史 handoff
   ├─ 起草 ADR（如有架构决策）→ status: draft 等用户审
   ├─ 写 docs/handoffs/active/planner-to-executor-<id>.md
   └─ 把路径给用户

用户复制路径 → executor 窗口
   ├─ 读 handoff，写 ## Executor's Reading + LOW/MED/HIGH 假设
   ├─ HIGH 假设 → status: blocked，等用户确认
   ├─ 实施 + 自测
   ├─ 写 ## What I Did，status: done
   └─ 新开 docs/handoffs/active/executor-to-auditor-<id>.md (type: review)

用户复制路径 → auditor 窗口
   ├─ 读 handoff（跳过 Context Pointers / Constraints 的设计动机段）
   ├─ 跑测试 / 验证 AC / 按 rubric 打分
   ├─ 追加 ## Auditor Verdict 段，status: done
   └─ 通知用户

用户决定：accept / request-rework / escalate-to-diagnose
   ├─ accept → 归档到 docs/handoffs/archive/
   ├─ request-rework → 把 Verdict 给 planner，让 planner 起新 handoff
   └─ escalate-to-diagnose → planner 开 type: diagnose handoff 给 auditor
```

---

## 增量启动（项目跑到一半想加角色 / 改隔离）

**不要轻量加角色**。如果一个角色的引入不值得重新审视整体架构，它
可能根本不该被引入（spec ADR-0001）。

正确做法：重跑初始 agent（即把
`/home/kk/code/project/agent-loop-evolution-spec/bootstrap/INTERVIEW-SCRIPT.md`
喂给一个新 Claude 会话），带上当前现状作为上下文：

```
我要重跑 initial agent。
项目背景：见 /home/kk/code/robot_class/final_pro_xiaozhi_robot/CLAUDE.md
当前状态：已落地 planner/executor/auditor 三角色，
         隔离 L3/L3/L4，现在想加角色 X，
         因为 Y（具体触发事件）。

请按 INTERVIEW-SCRIPT 重新评估，决定 (a) 这个角色是否真的需要，
通常不需要；(b) 如需要，触发一份新 ADR 记录决策依据并 supersede
ADR-0001 的相关段落。
```

---

## 常见问答

### Q：可以三个角色共用一个 window 吗？

A：技术上能，但失去多角色的核心价值（视角隔离、memory 隔离、auditor
fresh perspective）。如果项目缩水到只值得开一个 window，请按 spec
fast-track 退出建议办：废弃这套架构，回到单 Claude 会话。

### Q：planner 想直接改源码怎么办？

A：planner 的 tools 白名单不含源码路径的 Write/Edit。它想改 → 它就
得写 handoff 给 executor。这是机制，不是约定。

### Q：auditor 觉得自己看到的不够，想读 Context Pointers 怎么办？

A：违纪。auditor 的价值在 fresh perspective。如果 AC 真的模糊到必须
读才能判断 → 它应该 outcome: blocked 并要求 planner 把信息塞到
For Auditor 段，由 planner 决定是否分享 + 怎么分享。

### Q：M4 我直接在 esp/xiaozhi-esp32/main/boards/otto-robot/ 改了，
   会被 executor 的工具白名单拒绝吗？

A：spec 的工具白名单是 path-agnostic 的（默认不做路径级 hard fence），
本项目通过 CLAUDE.md "Project Scope" 段在 prompt 层告诉 executor：
"submodule 默认只读，但 main/boards/otto-robot/ 是 M4 工作区可写"。
executor 会遵守。如果担心机制不够强，可在 `.claude/settings.json`
加 PreToolUse hook 做硬隔离（详见 spec docs/concepts/isolation.md L5）。

### Q：handoff/ADR 越来越多 50 份装不下怎么办？

A：spec ADR-0010 的"按数量老化"策略：active/ > 50 → 最旧移 archive/；
archive/ > 500 → 移 archive/deep/（INDEX 不再提及）。本项目暂不装
hook，靠 /retro 兜底（手动）。
