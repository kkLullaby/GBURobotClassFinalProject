# Project: ottagent (GBU 期末作业)

> 本项目采纳多角色 agent 协作架构。完整规范见
> [agent-loop-evolution-spec](https://github.com/kkLullaby/Multi-agent_collaboration_workflow_design_specifications)（本地路径 `/home/kk/code/project/Multi-agent_collaboration_workflow_design_specifications/`）。

## 项目简介

把 ESP32-S3 OttoRobot 形态的小智机器人改造为 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的"第一具物理化身"——一个能说话、能转头、能感知环境的桌面 channel/工具集。**创新点不在硬件，在拓扑**：零私有协议、后端无关、可作为 PR 贡献给 Hermes 社区。

详见 [`README.md`](README.md)、[`docs/architecture.md`](docs/architecture.md)、[`docs/roadmap.md`](docs/roadmap.md)。

## 技术栈

- **ESP32 固件**：C++ / ESP-IDF v5.5.2（上游 `78/xiaozhi-esp32` main 分支）
- **协议适配层**：xinnan-tech `xiaozhi-esp32-server`（Docker minimal 模式）
- **桥接服务**：Python 3.8+（M1 `xiaozhi-mcp-adapter`、M2 `openai-shim` FastAPI）
- **Agent 主体**：Hermes Agent（Python，`uv tool install hermes-agent`）
- **Hermes plugin**：M3 `plugins/platforms/xiaozhi/`（Python）

## 常用命令

```bash
# ESP32 编译/烧录/串口（在 esp/xiaozhi-esp32/ 子目录下）
source ~/esp-idf-5.5.2/export.sh
idf.py set-target esp32s3
idf.py menuconfig          # Xiaozhi Assistant → Board Type → Otto Robot
idf.py build flash monitor # 退出 monitor: Ctrl+]

# xinnan-tech server (Docker minimal)
# 见 docs/architecture.md §6.1

# Hermes
hermes                     # 进 TUI
```

更全面的命令见 [`.claude/memory/shared/global-commands.md`](.claude/memory/shared/global-commands.md)。

## 仓库结构

```
final_pro_xiaozhi_robot/
├── README.md
├── CLAUDE.md                      ← 你正在读
├── bootstrap.md                   ← 三角色窗口启动手册
├── .claude/
│   ├── agents/                    ← planner / executor / auditor 的 system prompt
│   ├── rules/handoff-protocol.md
│   ├── memory/{shared,planner,executor,auditor}/
│   └── settings.json
├── docs/
│   ├── architecture.md            ← 已有（项目高保真架构）
│   ├── roadmap.md                 ← 已有（4 周路线图）
│   ├── demo-script.md             ← 已有（答辩 demo 脚本）
│   ├── research-notes.md          ← 已有（选型调研）
│   ├── handoffs/{active,archive}/ ← 跨角色任务流转
│   ├── adr/                       ← 决策史（ADR-0001 已写）
│   ├── contracts/                 ← 跨栈接口契约（M1↔M2、M2↔Hermes、ESP32↔server）
│   ├── designs/                   ← 长设计文档
│   ├── rubrics/                   ← auditor 评估标准
│   └── diagnoses/                 ← 诊断报告
└── esp/
    └── xiaozhi-esp32/             ← 上游 submodule（见下方"Project Scope"）
```

ESP-IDF 不放在仓库内；本机工具链按 `~/esp-idf-5.5.2/` 独立安装。

## 角色与协作

本项目使用三角色 agent 协作。角色定义在 [`.claude/agents/`](.claude/agents/)。

- **planner**：设计 + 写 handoff + 起草 ADR；**不动源码**（M1/M2/M3/M4 设计 + docs/ 编辑均归此）
- **executor**：按 handoff 实施 + 写测试（4 个模块的 Python/C++ 代码均归此）
- **auditor**：按 rubric 黑盒验证；**不读 planner 的设计动机**

完整协作模型见 [`docs/adr/0001-adopt-agent-arch.md`](docs/adr/0001-adopt-agent-arch.md)。

## Handoff 协议

所有跨角色流转走 `docs/handoffs/active/<from>-to-<to>-<id>.md`，规则见 [`.claude/rules/handoff-protocol.md`](.claude/rules/handoff-protocol.md)。完成后归档到 `archive/`。

INDEX 在 `docs/handoffs/INDEX.md` —— **先读 INDEX，再按需读具体 handoff**。

## 架构演进

所有架构决策落在 `docs/adr/`。改架构 = 写一个新 ADR 来 supersede 旧的，**永不静默编辑**。

复发性的"bitter lesson"必须连同最初触发场景一起记录。

## Project Scope（架构覆盖边界）

### In agent-arch scope（完整架构覆盖）

- `docs/`、`bootstrap.md`、`README.md`、`CLAUDE.md`、`.claude/`
- 未来新写的 M1 `xiaozhi-mcp-adapter/`（Python，本仓库内）
- 未来新写的 M2 `openai-shim/`（Python，本仓库内）
- 未来新写的 M3 `hermes-xiaozhi-plugin/`（Python，本仓库内）
- **M4 例外纳入区**：`esp/xiaozhi-esp32/main/boards/otto-robot/`（虽在 submodule 内，但属于本项目自写的工具代码）

### Light scope（共享 ADR，无需 handoff 走流程）

- 一次性 demo 录屏脚本、`scripts/` 临时工具（如有）

### Out of scope（豁免区，三角色都不许动）

- `esp/xiaozhi-esp32/`（**默认整个 submodule 只读**，仅 `main/boards/otto-robot/` 反豁免）
- `esp/esp-idf/`（不入库；用户在 `~/esp-idf-5.5.2/` 独立安装 IDF）
- `esp/xiaozhi-esp32/build/`、`managed_components/`、`dependencies.lock`（IDF 编译产物，体量巨大）

读上游代码用于理解协议、引用上游头文件，是允许且推荐的；**写**才不行。

## 项目事实（shared/ 经 @import 注入）

@.claude/memory/shared/tech-stack.md
@.claude/memory/shared/global-commands.md

## 当前活动

- @docs/handoffs/INDEX.md
- @docs/adr/INDEX.md

## 三角色共同纪律

1. 读任何 doc 先查 vitality state（frontmatter `status` 字段）；archived/superseded 必须沿 supersession 链找到 current
2. 读目录前先读 INDEX.md，不要遍历
3. 跨角色协作走 handoff 文件，不靠主会话口头转述
4. Auto Memory 只记事实/方法，不记判断/观点
5. 每个假设打 LOW/MED/HIGH 标签；HIGH 必须 STOP 等用户确认
6. **本项目特有**：涉及 `esp/xiaozhi-esp32/` 时先看 §"Project Scope"，分清"读"和"写"的边界
