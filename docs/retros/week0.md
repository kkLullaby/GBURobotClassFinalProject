---
status: current
created: 2026-06-19
author: planner
period: Week 0 (2026-06-16 → 2026-06-19, ~3-4 day calendar)
---

# Week 0 Retro — xiaozhi-robot

> 写于 H026。**目的**：沉淀 Week 0 的实践 + 抽方法论 + 收纳 bitter
> lesson，给 Week 1-4 用，也给上游 (Hermes / xinnan-tech) PR 时附素材。
> **不**写 ADR，不改 docs (除新建本文件 + 后续 H027 集中回灌)。

## §1 目标 vs 实际

### 原计划（[roadmap §Week 0](../roadmap.md)）

| # | 任务 | 估时 |
|---|---|---|
| 0.1 | 装 ESP-IDF 5.5.2 + 烧 otto-robot | 半天 |
| 0.2 | 起 xinnan-tech minimal Docker | 半天 |
| 0.3 | menuconfig 配 OTA URL + WS URL | 1 天 |
| 0.4 | 配临时 LLM (DeepSeek/Ollama) | 1 天 |
| 0.5 | 装 Hermes + TUI 跑一次 | 半天 |
| 0.6 | 读 Hermes discord plugin | 1 天 |
| 0.7 | 读 xinnan-tech openai.py + mcp-endpoint 文档 | 半天 |

**预算**：5-7 天弹性。

### 实际 (2026-06-16 → 2026-06-19, ~3-4 自然日)

| # | 任务 | 状态 | 落在哪 |
|---|---|---|---|
| 0.1 | ESP-IDF + 编译 | ✅ | H012 (3.5 MiB, 11% free) |
| 0.1+ | 烧 + 切本地 server + 一轮对话 | ✅ | H013 (RTT 4-6s, MAC `ac:a7:04:30:91:78`) |
| 0.2 | xinnan-tech Docker | ✅ | H011 (FunASR 893MB model.pt 先下) |
| 0.3 | OTA URL 配置 | ✅ | H013 Stage B |
| 0.4 | DeepSeek 接 | ✅ | H011 + H022 (server 直连 + 经 shim 间接两条) |
| 0.5 | Hermes 装 + TUI | ✅ | H005 (deepseek-v4-pro provider) |
| 0.6 | 读 discord plugin | ✅ | H003 + H006 (Discord-specific 已 audit) |
| 0.7 | 读 mcp-endpoint 文档 | ✅ | H010 (verdict: 走 OpenAI-compat 不走 MCP, 引出 ADR-0005) |

**Week 1 也提前推进**：H016 mcp-endpoint 起 + H018-H021 整套 openai-shim
(echo / Hermes fork / DeepSeek backend) + H020 真 Hermes session 收 + H022
真端到端 demo + H023 M4 inventory + H024 M4 实现 + H025 HMAC + H026 retro。

### 没做（明确推后）

- **systemd 自启** xinnan-tech / shim / hermes gateway → Week 3 demo polish
- **monitoring / alerting** → 不在 Week 0-4 scope
- **OBS 录屏自动化** → demo 答辩前几天 (Week 4)

### 时间预算回看

- 计划：5-7 天，实际：**约 1.5 天**手感操作 + 间断的小段时间累计 ~2 自然日
- **效率源**：多角色 agent 协作 — codex 在 sandbox 写代码 + planner
  main-loop 装 PyPI deps + user 物理端烧板子，三线并行
- **额外完成**：Week 1 + Week 2 起点 (M2 shim 100% / M4 50%) → roadmap 至少
  压缩 1 周
- **教训**：原 roadmap 高估 Week 0 (5-7 天)，实测**裸操作 ~1.5 天**够。
  Week 1-4 估时同样需要复核

---

## §2 Handoff 流水

22 个 archive + 3 个 active = **26 个 handoff** (H001-H026)。

### 按时间序的极简表

| ID | from→to | 类型 | 结果 |
|----|---------|------|------|
| H001 | planner→executor | codex spike | blocked → 由 H004 supersede |
| H002 | planner→executor | codex spike | blocked → 由 H005 supersede |
| H003 | planner→executor | codex spike | done (Discord plugin 读完) |
| H004 | planner→executor | codex spike | done (submodule 正式 pin) |
| H005 | planner→executor | codex spike + user finish | done (Hermes TUI 跑通) |
| H006 | executor→auditor | review | done (accept H003) |
| H007 | planner→executor | codex spike | blocked → 由 H010 supersede |
| H008 | planner→executor | codex spike | A done / B → H011 |
| H009 | planner→executor | docs alignment | done |
| H010 | planner→executor | codex spike | done (transcript 走 OpenAI-compat) |
| H011 | planner→**user** | user-led + planner main-loop 代跑 | done (Docker minimal 起) |
| H012 | planner→executor | planner main-loop unblock | done (build 3.5 MiB) |
| H013 | planner→**user** | user-led (物理端) | done (烧成 + 4-6s RTT) |
| H014 | planner→executor | docs 回灌 (memo) | done |
| H015 | planner→executor | codex spike + planner unblock | done (M1 echo 1.17s PASS) |
| H016 | planner→**user** | 多 stage 混合 | done (隐式通过 via H022) |
| H018 | planner→executor | codex spike + planner unblock | done (shim 2/2 PASS) |
| H019 | planner→executor | **codex sandbox 自闭环** | done (5/5 PASS, 无 unblock) |
| H020 | planner→**user** | planner main-loop 代跑 + 物理 | done (5/5 真 Hermes 收) |
| H021 | planner→executor | **codex sandbox 自闭环** | done (9/9 PASS) |
| H022 | planner→**user** | planner main-loop + 物理 | done (5/6 Stage, 3s RTT) |
| H023 | planner→executor → planner代写 | codex blocked + planner 接管 | done (inventory + verdict) |
| H024 | planner→executor → planner unblock | codex 3 轮 blocked + planner unblock | done (build PASS, +20KB) |
| H025 | planner→executor | **codex sandbox 自闭环** | done (11/11 PASS) |
| H026 | planner→planner | planner self-task | done (本文件) |

### 类型分布

```
codex sandbox 自闭环 (✨ ideal)   ▓▓▓             3 (H019/H021/H025)
codex spike + planner unblock     ▓▓▓▓▓▓          6 (H005/H012/H015/H018/H023/H024)
planner main-loop 代跑            ▓▓▓▓            4 (H011/H020/H022 + planner part H023)
user-led 物理端                   ▓▓              2 (H013 + H016 D + H022 voice)
codex spike blocked → superseded  ▓▓▓             3 (H001→H004 / H002→H005 / H007→H010)
docs-only                         ▓▓              2 (H009 / H014)
read-only audit                   ▓               1 (H003 / H006)
```

26 handoff 中：**ideal 自闭环 3 个 (11%)**，含 planner unblock 6 (23%)，
**user 物理参与 4 个 (15%)**——剩 50% 是 docs / 设计 / superseded。

### 平均周期

- 单 handoff 从 issue → done：**几小时到 1 天** (含 codex 多轮 reopen)
- **3-4 自然日**内完成 26 个 → 平均 ~6 handoff/日，**远超** roadmap 1
  handoff/日的隐含估算

---

## §3 ADR 决策史

5 个 ADR，全 active，0 superseded。

### ADR-0001 — 采纳 agent-loop-evolution-spec 三角色架构 (2026-06-16)

- **触发**：项目初期，单 agent 心智负担过大；外部 spec 已成熟
- **决策**：planner / executor / auditor 分工 + handoff 文件流转 + memory 分层
- **后续影响**：定下整个项目的协作模式；arch 决策必经 ADR，全程 0 静默改

### ADR-0002 — Week 0 基线修正 (2026-06-16 created, 2026-06-19 activated)

- **触发**：发现 submodule 状态不对 + 烧录路径不清；H001/H002 都 blocked
- **决策**：先把"基线"统一描述清楚 (submodule pin + tty 设备 + step 拆段)
- **后续影响**：H004 + H012 + H013 顺利推进的前提

### ADR-0003 — Executor 跑在独立主会话，不通过 Task subagent (2026-06-16 / 2026-06-19)

- **触发**：H001-H002 在 Task subagent 内 sandbox 限制太多
- **决策**：executor = 独立 Claude Code session (类 codex)；Type II 子项：
  planner main-loop 代跑 unblock
- **后续影响**：**贯穿全 Week 0** — 6 次 codex spike + planner unblock；3 次
  纯 codex 自闭环 (H019/H021/H025) — 这是协作模式的实际演化路径

### ADR-0004 — Discord-specific 回调降级 (2026-06-18 / 2026-06-19)

- **触发**：H003 读 Hermes Discord plugin 发现 `_voice_input_callback` 是
  Discord 私货，原 ADR-0001 pitfall #4 高估了通用性
- **决策**：降级该 pitfall + 关闭 Week 3 Day 16 hard-stop (本来要花 1 天
  对齐音频回调，现在不必)
- **后续影响**：Week 3 工时 -1 天

### ADR-0005 — M3 transcript 走 OpenAI-compat (2026-06-19)

- **触发**：H010 spike 发现 xinnan-tech 不发 MCP-client transcript callback，
  实际只走 OpenAI `messages`
- **决策**：M2 shim **升级为 transcript 入口** + Hermes 改用 webhook 收
- **后续影响**：M3 工作量 5-6 → 1-2 天；H018-H022 + H025 都为这条线服务

---

## §4 Bitter Lessons 集中收纳

| # | 触发场景 | 教训 | 已回灌位置 | 待回灌 |
|---|---|---|---|---|
| 1 | H001/H002 codex 内 Task subagent 限制 | codex spike 写代码 OK，**装 PyPI / 跑 IDF / 跑 docker 不 OK** → planner main-loop 接力 unblock | ADR-0003 II 类 | — |
| 2 | H012 装完 IDF 没 init 自身 submodules → set-target 崩 | IDF tarball 不全；必装后立刻 `submodule update --init --recursive` (~15min) | shared/global-commands §一次性 | — |
| 3 | H012 OTTO_ROBOT 板 menuconfig 不够，要 append 3 CONFIG | menuconfig prompt 不含 sdkconfig_append 字段；得读 `boards/*/config.json` | shared/global-commands; ADR-0001 pitfall #1 | — |
| 4 | H013 串口找不到——ESP32-S3 是 `/dev/ttyACM0` 不是 `/dev/ttyUSB0` | OttoRobot 用内置 USB-OTG (CDC-ACM)，不是外挂 CH340 | shared/global-commands §串口 | README FAQ 待加 |
| 5 | H013 flash 后卡 `waiting for download` | flash 完 boot 没切，得按板上 RST 键 | shared/global-commands §3 | — |
| 6 | H015 user `python3` 是 PlatformIO penv 没装项目 deps | 用 alias `pyx=miniconda3/bin/python` | shared/global-commands §Python | — |
| 7 | H010 spike：xinnan-tech 不发 MCP transcript callback | 不要假定上游"按文档说的"实现；spike 验证 → 引出 ADR-0005 | ADR-0005 §Context | — |
| 8 | H011 FunASR 缺 model.pt (893 MB) → restart:always 崩溃循环 | 容器 restart-loop 会 mask 真因；先 logs grep EOFError | shared/global-commands §xinnan; ADR-0001 pitfall #N | — |
| 9 | H020 Hermes webhook **强制 HMAC** 且 header 是 **GitHub 风格** `X-Hub-Signature-256` | Hermes 复用 GitHub 协议，不是自定义 X-Hermes-*；强制不可空 | H025 修 + shim README | docs/contracts/api/v1/hermes-webhook-handshake.md 待补 |
| 10 | H020 Hermes agent 子进程继承父级 env (含 ALL_PROXY) | demo polish 时改 `~/.hermes/.env` 而不是 shell env | — | shared/global-commands §Hermes 待加 |
| 11 | H020 `ALL_PROXY=socks5` 杀 websockets/asyncio TCP | spike 前先 `unset HTTP_PROXY HTTPS_PROXY ALL_PROXY` | shim README + xiaozhi-mcp-adapter README | 集中回灌 .claude/memory/shared/ |
| 12 | H022 wifi 段一变 ESP32 卡死 (CONFIG_OTA_URL 硬编码) | OTA URL 烧进 partition；切热点必须确保 server IP 同段 | — | docs/demo-script.md 答辩前列入预检 |
| 13 | H022 DeepSeek 严格校验 `role=tool` 必须含 `tool_call_id` | shim pydantic schema 只接 role+content 默静默丢字段 → 必须 `extra=allow` + `model_dump(exclude_none=True)` 完整透传 | shim app.py + deepseek_backend.py 已修 | docs/contracts/api/v1/openai-message-passthrough.md 待补 |
| 14 | H023 codex 解 "读 INDEX 再读目录" 过严 → blocked | docs/designs/INDEX.md 不存在直接按 handoff path 写即可；CLAUDE.md 规则需子条款 | — | CLAUDE.md §三角色共同纪律 待加子条款 |
| 15 | H024 `Board::GetInstance().GetDisplay()` 返指针，但 board.h 只 forward-declare → 必须显式 `#include "display.h"` | submodule 内自己写的代码也要主动管 include 链；不要假定 transitive include | otto_controller.cc 已加 | M4 contract §1 注释 |
| 16 | H024 codex 三次 reopen 失败（路径错 / blocked-on-cosmetic）→ planner unblock | Error-handling discipline 要在 handoff 内明确"补查路径错就再试一次" | H024 handoff Recovery §更新 | executor.md prompt 待调 |

**16 条**。"待回灌" 6 条 → 集中走 H027 (本 retro 后批一次)。

---

## §5 Agent-arch 实战回顾

### 三角色实际占比

- **planner (我)**：所有 26 handoff issue + 6 次 unblock + 5 ADR + 本 retro
- **executor (codex)**：14 个 handoff 实际写代码，3 个完全自闭环
- **auditor**：**1 次** (H006 review H003)

### "codex spike + planner unblock" 模式的演化

H012 ▸ H015 ▸ H018 → **codex 写代码 OK 但 sandbox 装不了 deps** → planner
main-loop 装 + 跑 test → 完成。3 次后该模式正式 ADR-0003 II 写进规范。

H019 ▸ H021 ▸ H025 → **codex 自闭环** (没有 unblock)。原因：M2 体系
PyPI deps 在 H018 全部装齐，后续 backend 增加无新依赖 → codex 在 sandbox 内
能完整跑 pytest。**这是模式的最优形态**。

H023 ▸ H024 → **codex blocked-on-cosmetic** (INDEX 不存在 / 路径输错 / build
forward-declare)，planner 直接接管。教训：codex error-discipline 在
ambiguous case (cosmetic vs substantive 边界) 偏保守，**宁可 blocked 不超
scope** — 这是正确的，只是导致 planner 工时被多吃。优化方向：handoff
Recovery 段写得更明确。

### 必须 user-led 的工作

- **H011** Docker bringup：FunASR model.pt 下载耗时 + 网络 + 用户家里
  机器
- **H013** ESP32 物理烧录：USB-OTG + RST 按键 + 串口监视
- **H016 D** + **H022 ESP32 voice**：物理端的 demo 是 user 必须站在
  机器人前
- **H020 D physical**：Hermes 真 session spawn 期间用户要看 TUI

这 4 处即使 fleet 化也不能消除，**人在物理端**是产品定义的一部分。

### Auditor 用了几次

**1 次**。粒度太大？还是合理？

- 论据 A (太懒)：22 archive 中 0 个走过 auditor diagnose；M2 4 个 codex spike
  没走 auditor (留 demo 前 batch)
- 论据 B (合理)：Week 0 是 spike-heavy，spike 的 verification 内嵌 (pytest
  + curl smoke + idf.py build) → auditor 单独再 review 是 noise
- **结论**：Week 1+ 进入 M2/M3/M4 集成测时，应该至少 1 次 batch auditor

---

## §6 Week 1 启动建议

### 该补的 docs alignment (待回灌)

走 1 个集中 handoff **H027 "Week 0 retro 回灌"**：

1. CLAUDE.md §三角色纪律 加 "INDEX 不存在时如何处理" 子条款 (#14)
2. shared/global-commands.md 加 §Proxy unset 段 (#11)
3. shared/global-commands.md 加 §Hermes env 段 (Hermes agent 继承 env, #10)
4. README FAQ 加 ttyACM0 注释 (#4)
5. docs/contracts/api/v1/hermes-webhook-handshake.md 新建 (HMAC + GitHub
   header) (#9)
6. docs/contracts/api/v1/openai-message-passthrough.md 新建 (#13)
7. docs/demo-script.md 加"切热点预检"段 (#12)
8. .claude/agents/executor.md prompt 微调 "cosmetic error 自修原则" (#16)

### Agent 工作流调整

- **codex Recovery 段写更明确**：H023/H024 教训
- **codex 自闭环的 handoff 标记上**：让 user 一眼能知道"这个直接交 agent
  跑、不用陪"
- **planner unblock 的工时也算 handoff cost**：未来估时不能假设 codex
  会 100% 自闭环

### Demo polish 时间预算

按 roadmap Week 4 = 5 天。基于 Week 0 实际效率，估**真正 polish 2-3 天**
够 (录屏 + 备用 fallback path + 答辩 PPT)。剩 2-3 天作 buffer。

### Week 1 主线

H024.bis (user 烧 + 端到端测 M4 show_emoji/show_text)
→ H025 已 done (HMAC + Stage F 自动 unblock, 待物理验证)
→ H026 已 done (本文件)
→ H027 (docs 集中回灌, 6-8 条)
→ Week 1 M3 (Hermes xiaozhi channel plugin) 起手

---

## 附：Week 0 一句话总结

> 3-4 自然日内完成 Week 0 + 提前推进 Week 1-2 关键路径；建立"codex
> sandbox + planner main-loop + user 物理端"三线并行协作模式；定下 5 个
> ADR + 16 条 bitter lesson + 11 个 PASS test + 1 个 3s RTT 端到端 demo。
> 项目进入 "**M3 起航 + M4 加表情**" 阶段。
