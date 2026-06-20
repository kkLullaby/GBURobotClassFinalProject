---
id: 0001
title: Adopt agent-loop-evolution-spec three-role architecture for ottagent
status: active
created: 2026-06-16
author: user
---

## Context

GBU 期末作业项目，4 周窗口，solo 开发，目标交付：
ESP32 OttoRobot 作为 Hermes Agent 的物理化身（M1-M4 四个新写模块 +
一个上游 submodule 的最小侵入）。已有完整文档：

- [`README.md`](../../README.md)
- [`docs/architecture.md`](../architecture.md)
- [`docs/roadmap.md`](../roadmap.md)
- [`docs/demo-script.md`](../demo-script.md)
- [`docs/research-notes.md`](../research-notes.md)

通过初始 agent 6 阶段访谈（其中阶段 1-3 由初始 agent 直接从已有
doc 推断、跳过提问），确认这是个：

- 中等规模（4 周、solo、1-2 windows）
- 多技术栈（C++ ESP-IDF + Python 桥接服务 + Python plugin），按周线性推进
- 同时有"客观验证入口"（curl/wireshark/单测）和"主观验证"（演示效果靠人眼）
- 有一个明确的"只读上游"区（`esp/xiaozhi-esp32/` submodule）
- 已识别出一个最大风险（`_voice_input_callback` 可能 Discord-specific）

的项目，**满足采纳 spec 三角色架构的条件**。

### 项目特征（来自访谈 / 已有 doc）

- 预期持续：4 周
- 预期并行窗口：1-2 个（极少同时 3 个）
- 团队规模：solo（kk）
- 主要工作类型：代码正确性 + 设计合理性（架构选型已大量沉淀在
  `architecture.md` / `research-notes.md`）+ 演示效果
- 多技术栈：是；形态 = 同一产品多端（ESP32 C++ + 主机 Python 多个服务）
- 验证入口：部分客观（协议链路 curl 可测、单测可写）、部分主观
  （演示流畅度、答辩 8 个问答的应对）

### 角色选择

- **planner**：启用。理由：架构图、协议握手、模块边界已经是这个
  项目的核心资产，需要一个角色专注维护并把它翻译成 executor 可执
  行的 handoff。
- **executor**：启用。理由：M1/M2/M3/M4 四个模块的代码实现 + 测试，
  需要全工具权限的执行角色。
- **auditor**：启用。理由：demo-script 有 8 个评委问答场景需要被
  独立视角挑刺；且本项目存在"看起来跑通但实际是错的"的高风险
  （例如 SSE chunk 格式接近但不严格对齐 → 静默静音）。

### 隔离强度选择

| 角色 | 等级 | 理由 |
|------|------|------|
| planner | L3（工具白名单：可 R/W/E 在 docs/handoffs/、docs/adr/、docs/contracts/、docs/designs/ 下；不动源码；独立 memory） | 项目最值钱的产物是 architecture/roadmap/demo-script，planner 专管这块；独立 memory 防止被实现细节污染 |
| executor | L3（全工具白名单；独立 memory） | solo + 周间基本串行，无需 L5 worktree 的复制成本；ESP-IDF 编译产物体量巨大（GB 级），worktree 会很难受；独立 memory 防止"上次某个引脚 hack 过"误带入下次 |
| auditor | L4（只读工具 Read/Bash/Grep/Glob，无 Edit/Write；handoff 切片视图；独立 memory，限制只记方法不记判断） | 与 spec ADR-0006 一致；本项目演示场景需要 fresh perspective 来评估 |

**不预设 L5（worktree）的原因**：

- solo + 周线性，几乎不出现"两个 window 改同一文件"的并发场景
- ESP-IDF `build/` + `managed_components/` 体量巨大（GB 级），
  worktree 复制成本过高
- 万一 Week 2-3 真的出现 M1 和 M4 并行需求，再**临时**升 L5，
  不预设；触发条件写入本 ADR Consequences 段

### Memory 隔离

- 分角色独立 auto memory：是
  - `~/.claude/projects/.../memory/{shared,planner,executor,auditor}/`
- shared/ 守门：方式 a（不指给任何 subagent 当 autoMemoryDirectory，
  通过 CLAUDE.md @import 引入；agent 想往 shared/ 写需用户审核）
- auditor 限"只记方法不记判断"：是（由 auditor.md system prompt 强制）
- 进 git：是（重定向到项目内 `.claude/memory/`，可 diff 可 rollback）
- 升级备胎：如发现 auditor 反复对同一段代码下相同判断，按 spec
  ADR-0006 升级路径处理（L4 → worktree 隔离 → 拆 fact-checker 子角色）

## Decision

采纳 spec v0.1 的三角色架构。按上述配置落地。

具体配置文件：

- @.claude/agents/planner.md
- @.claude/agents/executor.md
- @.claude/agents/auditor.md
- @.claude/rules/handoff-protocol.md
- @.claude/memory/shared/tech-stack.md
- @.claude/memory/shared/global-commands.md
- @CLAUDE.md
- @bootstrap.md

## Project Scope（架构覆盖边界）

### In agent-arch scope（完整架构覆盖）

- `docs/`（所有 4 份已有 doc + 未来 handoff/ADR/contract/design/diagnose/rubric）
- `bootstrap.md` / `README.md` / `CLAUDE.md` / `.claude/`
- 待创建：M1 `xiaozhi-mcp-adapter/`（Python，本仓库内）
- 待创建：M2 `openai-shim/`（Python，本仓库内）
- 待创建：M3 `hermes-xiaozhi-plugin/`（Python，本仓库内）
- **M4 例外纳入**：`esp/xiaozhi-esp32/main/boards/otto-robot/`（虽在
  submodule 内，但属于本项目自写的工具代码，executor 必须能写）

### Light scope（共享 ADR，无需 handoff 走流程）

- 一次性 demo 录屏脚本
- `scripts/` 临时小工具（如有）

### Out of scope（豁免区）

- `esp/xiaozhi-esp32/`（**整个 submodule 默认只读**，仅
  `main/boards/otto-robot/` 反豁免；详见 CLAUDE.md "Project Scope" 段）
- `esp/esp-idf/`（如未来链入仓库）
- `esp/xiaozhi-esp32/build/`、`managed_components/`、`dependencies.lock`
  （IDF 编译产物，体量巨大）

读上游代码用于理解协议、引用上游头文件是允许且推荐的；**写**才不行。

## Known pitfalls（本项目特别警惕的）

### 继承自 spec 的元 pitfall（不再展开，详见 spec 仓库 ADR）

来源：`/home/kk/code/project/Multi-agent_collaboration_workflow_design_specifications/`

- **agent 经验未必是资产，可能是偏见**（spec ADR-0002 #2 + ADR-0003 + ADR-0006）
  → auditor 不读 Context Pointers / 设计动机；只记方法不记判断
- **memory 跨角色污染破坏 auditor 公正性**（spec ADR-0003）
  → 强制分角色 memory 目录
- **新增机制要先问能否复用现有，防止脚手架膨胀**（spec ADR-0002 #5）
  → 不轻易开新角色 / 新文档类型；要加先看能否走 handoff type 或 rubric 字段
- **文档老化按 attention 容量（数量）而非时间**（spec ADR-0010）
  → active handoff > 50 移 archive；archive > 500 移 deep
- **agent prompt 跨项目零修改**（spec ADR-0002 #8）
  → 本项目的 `.claude/agents/*.md` 是 spec 模板原样拷贝，**严禁项目特化**；
    项目特化知识住 CLAUDE.md / rules/ / handoff 三层
- **架构纳入按需付费**（spec ADR-0002 #4）
  → 显式豁免区 `esp/xiaozhi-esp32/` 不被架构覆盖
- **角色边界靠互相否定定义**（spec ADR-0002 #9）
  → 三份 prompt 都有"不要做的事"段并显式引用对方角色

### 本项目特有 pitfall（来自 README/roadmap/research-notes）

1. **ESP32 板子型号默认是 `Bread Compact WiFi`，必须改 `ottoRobot`**
   - 选错 → 屏幕黑、麦克风/喇叭无声、按键无响应
   - 改完必须 `rm -rf build sdkconfig && idf.py set-target esp32s3 && idf.py menuconfig` 重来
   - 注意 Kconfig prompt 实际是 `"ottoRobot"`（小写 o + 驼峰），不是 README/CLAUDE 上写的 "Otto Robot"
   - **menuconfig 不够（H012 教训, 2026-06-19）**：选完 `ottoRobot` 后还**必须**手工 append 3 个
     CONFIG (`HTTPD_WS_SUPPORT=y` + `CAMERA_OV2640=y` + `CAMERA_OV3660=y`)，否则 build
     在 2206/2212 处崩 (`websocket_control_server.cc` httpd_ws_* 未声明)。来源：
     `main/boards/otto-robot/config.json` 的 `sdkconfig_append` 字段——上游 README 漏说
   - 出处：README §3 + roadmap Week 0 风险 1 + [H012](../handoffs/archive/2026-06-19-idf-build-verify-h1a-012.md) §Unblock + Build SUCCESS

2. **ESP-IDF 版本必须 ≥ 5.5.2（上游硬性要求）**
   - 用 5.3.x 会 version solving failed
   - 之前在 5.3.2 上做了大量降级 hack，**升 5.5.2 后那些 hack 全是白做**
     （历史在 `esp/xiaozhi-esp32/backup-pre-cleanup-20260616` 分支）
   - **教训**：不要为了用更熟的工具版本去 hack 上游硬性要求
   - **新装 IDF 必须 init 其自身 submodules（H012 教训, 2026-06-19）**：
     `cd ~/esp-idf-5.5.2 && git submodule update --init --recursive`（不要带
     `--depth=1`——在 `lib_esp32c3_family` 处 fetch 会中断、留 `refs/heads/.invalid`
     ref，需手工 nuke `.git/modules/...` 重 init）

3. **组件没拉全 → 找不到 `esp_video_init.h` 之类的头文件**
   - 修复：`rm -rf build managed_components dependencies.lock && idf.py reconfigure`
   - 出处：README Q&A

4. **`_voice_input_callback` 可能是 Discord-specific**（roadmap 第 16 天的 🔥🔥 风险）
   - 这是本项目**最大未知**，决定 M3 工作量从 8 天还是 18 天
   - 必须在 Week 3 第 2 天硬性确认；若是 Discord-specific 立刻走降级方案 B
   - **教训**：把"高方差未知"的解锁日提前钉死，不要被"也许能行"拖到 deadline

5. **SSE chunk 格式不严格对齐 → xinnan-tech 解析失败、机器人静默静音**
   - 表面看 endpoint 通了、HTTP 200，但 TTS 没声音
   - 必须按 OpenAI streaming 文档严格对齐字段
   - **教训**：HTTP 层通不等于业务层通；定 contract 必须包含一个
     "playback success" 的端到端断言

6. **ESP32 `AddTool` 注册晚于云端 `tools/list` 调用 → server 拿不到新工具**
   - 修：ESP32 上 `Restart()` 强制重新 hello
   - 出处：roadmap Week 2 风险 2

7. **xiaozhi MCP接入点 token 流程文档不全**（roadmap Week 2 风险 1）
   - 必须直接读 `xinnan-tech docs/mcp-endpoint-integration.md` + 对照测试页面
   - **教训**：M1 启动前先 spike 这个文档；不要假定它讲清楚了再动手

8. **xiaozhi-server "minimal" 模式 vs 完整模式差异巨大**
   - 完整模式拖一堆 MySQL/Redis/Java 进来；minimal 模式才轻
   - 出处：research-notes 选型决策
   - **教训**：所有 Docker compose 文件 PR 时先确认是 minimal 变种

9. **Hermes session key 是 per-channel 的**
   - `agent:main:<platform>:<chat_type>:<chat_id>`，Telegram 和 xiaozhi 是
     **两个独立 session**，上下文不共享
   - 跨 channel 协作必须走 `send_message_tool` 或 cron `deliver` 字段
   - 这点必须在 demo 答辩里讲清楚，否则容易被评委误以为是 bug
   - 出处：architecture §3

10. **ESP-IDF 编译产物 `build/` GB 级**
    - 直接后果：worktree 升 L5 复制成本高得离谱
    - **教训**：本项目不预设 L5；如真要升必须用 git worktree 的 sparse mode
      或在 worktree 里直接 `rm -rf esp/xiaozhi-esp32/build`

11. **ESP32 OTA URL 配错 → 连不上 server**
    - 缓解：用 `nc -l 8003` 先验证 ESP32 出包正常
    - 出处：roadmap Week 0 风险 3

12. **`listen_ambient` 工具是隐私敏感的**
    - 必须亮红色 LED + 短 beep + metadata 里 echo `recording_consent: true`
    - 系统 prompt 必须禁连续调用
    - 演示场景二涉及"代念发言"时屏幕必须同步显示字幕
    - 出处：architecture §8

13. **写 handoff/命令清单时不要凭"上一个项目的默认"写串口设备名**（H1b 教训, 2026-06-19）
    - H1b handoff Stage C 默认写 `/dev/ttyUSB0`，实际 OttoRobot 是
      `/dev/ttyACM0`（ESP32-S3 内置 USB-OTG，非 CH340/CP210x 外挂芯片）
    - 用户严格按 handoff 跑就触发 `Could not open /dev/ttyUSB0: No such file
      or directory`，浪费一轮 round-trip
    - **教训**：handoff 里凡是"具体硬件路径 / 端口号 / 命令行参数"必须
      **要么从 [shared/global-commands](../../.claude/memory/shared/global-commands.md)
      里 quote、要么标记"待 user 实测确认"**——planner 不能凭印象写
    - 触发对 ADR-0001 §纪律 1（"每个假设打 LOW/MED/HIGH 标签"）的隐含违反：
      "用 ttyUSB0" 本质是 LOW 但写成了"事实"，应该写 LOW 假设让 executor 校核
    - 出处：H1b §Open Questions ④

### 演化时机

新踩坑请在事件发生时追加到本节末尾，**不要静默修改既有条目**；
若旧条目结论被推翻，写新条目 supersede 旧的（标 "supersedes pitfall #N"）。
凡跨项目复发 ≥2 次的 pitfall，下次 `/promote-adr` 时考虑回流 spec。

## Consequences

### Positive

- 跨窗口协作走结构化协议，不靠口头/记忆传递
- 决策史可审计（ADR），演进留痕（CHANGELOG / supersession 链）
- auditor 的 fresh perspective 由机制（工具白名单 + handoff 切片）保障，不靠自律
- 本项目最大未知（Discord callback）有明确触发的"升级方案 B"路径，
  且写在 ADR 里下次不会忘
- M4 反豁免区的边界写清楚后，executor 改 `otto-robot/` 不会越界改上游

### Negative

- 4 周项目花 0.5-1 天搭脚手架，相对总时长比例不小
  - 缓解：搭好后剩余 26-35 天的产出可被结构化记录，为答辩材料和后续 PR 给社区都加分
- INDEX / ADR 维护成本（按 spec 默认是 /retro 兜底，本项目暂不装 hook）
- shared/ 守门靠人工（solo 项目里就是 kk 自己审，相对可控）

### Trade-off / 升级触发条件

- 若 Week 2-3 出现"M1 Python 服务 + M4 ESP32 固件"两个 window 频繁
  并行改同名配置/文档 → 临时把 executor 升到 L5（worktree）；
  升级时必须在 worktree 里立即 `rm -rf esp/xiaozhi-esp32/build managed_components`
  以避免复制 GB 级编译产物
- 若 auditor 在 3 次评估内反复对同段代码下相同判断 → 按 spec ADR-0006
  走升级路径，记入新 ADR

## References

- Spec: `/home/kk/code/project/agent-loop-evolution-spec/` v0.1
- 同一份规范的镜像/演进版：`/home/kk/code/project/Multi-agent_collaboration_workflow_design_specifications/`
- 访谈剧本：`<spec>/bootstrap/INTERVIEW-SCRIPT.md`
- 元原则：`<spec>/docs/adr/0002-meta-principles.md`
- 隔离梯度：`<spec>/docs/adr/0009-isolation-gradient.md`
- auditor fresh perspective：`<spec>/docs/adr/0006-auditor-fresh-perspective.md`
- 本项目背景：[../architecture.md](../architecture.md)、[../roadmap.md](../roadmap.md)、[../demo-script.md](../demo-script.md)、[../research-notes.md](../research-notes.md)
