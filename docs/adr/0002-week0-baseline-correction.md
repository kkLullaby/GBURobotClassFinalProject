---
id: 0002
title: Week 0 基线修正：submodule 状态、首次烧录路径、本机烧录链路验证拆段
status: active
created: 2026-06-16
activated: 2026-06-19
author: planner
supersedes:
---

## Context

Week 0 启动时，planner 对实测环境做了一次基线探测，发现 3 处
**CLAUDE.md / roadmap / shared/tech-stack.md 与实际不符**，必须在写
任何 Week 0 handoff 之前显式记录修正，否则后续 handoff（H0/H1/H2）
都会引用一个错的"事实"。

### 不符项清单

#### 不符 1：`esp/xiaozhi-esp32/` 不是 git submodule

- **CLAUDE.md** §仓库结构 + §Project Scope 都按 "submodule" 描述
- **shared/tech-stack.md** 写 "`esp/xiaozhi-esp32/` = 78/xiaozhi-esp32
  main 分支"，暗示是 submodule
- **shared/global-commands.md** §Git 工作流 给的指令是
  `git submodule update --init --recursive` + `git submodule update`
  跟上游
- **实测**（2026-06-16）：
  - 主仓库根目录没有 `.gitmodules`
  - `git submodule status` 返回 `fatal: 在 .gitmodules 中没有发现路径
    'esp/xiaozhi-esp32' 的子模组映射`
  - `esp/xiaozhi-esp32/` 是一个**嵌套 git 工作树**（自带 `.git`），
    `origin = kkLullaby/ottagent.git`，
    `upstream = 78/xiaozhi-esp32.git`，当前 HEAD = `b392c63`（上游 main）
  - `esp/esp-idf/` 在 git index 里被标记 `D`（已从主仓库 index 删除），
    但目录还在磁盘上（是 ESP-IDF 5.3.2，**不是** roadmap 要求的 5.5.2）
- **影响**：若不修，"跟上游 main" 这件事每次都要手 `cd && git pull`，
  PR 给 Hermes 社区时仓库结构会被质疑；且 CLAUDE.md / shared/ 的多处
  描述持续撒谎

#### 不符 2：首次跑通路径用的是 **web 端烧录工具**，不是本地 IDF

- **roadmap.md Week 0** §0.1 假设："装 ESP-IDF 5.5.2，编译并烧录
  otto-robot 板子型号"
- **实测**：用户用 [16302 web 烧录工具](https://www.16302.com/firmwarehub/O3XoF1s)，
  **借别人的电脑**烧上了上游 baseline 固件，已在 web 端控制台跑通
  全程对话
- **影响**：
  - 用户本机的 IDF 工具链、USB 驱动、串口权限**全未验证**
  - M4（写 `main/boards/otto-robot/` 的新 MCP 工具）必须本机能 build +
    flash，所以"本机烧录链路验通"是 M4 的硬前置，**不能跳**
  - roadmap Week 0 §0.1 的"烧录"实际跑过了，但用的不是 roadmap 想要的
    路径，不能算 §0.1 done

#### 不符 3：roadmap 把"本机烧录链路验证"当一步，应拆两段

- USB 线、电源、设备的物理 ready 在用户这里**还没凑齐**
- 若按 roadmap §0.1 一气呵成"build + flash + monitor"，会被 USB 物理
  ready 卡死，IDF 工具链是否通这件事也跟着无法独立验证
- **修正**：拆成 H1a（纯 build，验工具链）+ H1b（flash + monitor，验
  烧录链路），中间可异步等 USB 线到位

## Decision

落 3 件事，**Week 0 第一波 handoff 之前**完成或同步发出：

1. **写 H0 handoff**（planner → executor）把 `esp/xiaozhi-esp32/` 从
   嵌套 git repo 转为正式 submodule，pin 在当前 HEAD `b392c63`；同步
   把 `esp/esp-idf/` 的 index `D` 残留清掉（该目录是 5.3.2 的旧版，
   按 .gitignore 已不入库，从 index 里清掉一致即可，**不删盘上目录**
   —— 用户的 5.5.2 装哪由用户自己决定，跟主仓库无关）
2. **Week 0 任务拆段**：H1a（纯 build）⨉ H1b（flash + monitor）分开发，
   H1b 等 USB 线到位
3. **承认上游 baseline 已经跑通这件事**：在 P0 contract 草稿
   (`docs/contracts/esp32-to-server-handshake.md`) 里把 16302 web 路径
   作为"已知可行的 baseline 路径"记录留存（不是推荐路径，是 fallback）

**CLAUDE.md / shared/global-commands.md 不在本 ADR 直接改**，等
H0 done 后另起一个小 handoff 把"submodule"字样在文档里彻底对齐。

## Consequences

### Positive

- 后续所有 Week 0 handoff 引用的"事实"是真实的，executor 不会在
  H0 第一步就发现 `.gitmodules` 不存在然后阻塞
- H1 拆段让"工具链验证"与"USB 物理 ready"两件事的成败可独立诊断
- 上游 baseline 路径有正式记录，万一本机烧录链路始终走不通，知道
  最终 fallback 是再借电脑烧一次

### Negative

- Week 0 比 roadmap 多出 1 个 handoff（H0）和 1 个 ADR（本文档），
  整体增加 ~0.5 天文档开销
- ADR-0002 一旦 approved，H0/H1a/H1b 才能定稿发出；中间有一个用户
  审核的 gate

### Trade-off

- 不修 submodule 也能交付（Light scope 路径），但 4 周后给 Hermes
  社区 PR 时仓库结构会要返工。早改 vs 晚改，早改的总成本更低
- 拆 H1 增加 handoff 数量但降低单 handoff 风险，对 solo + 周线性
  开发利大于弊

## References

- 项目契约：@CLAUDE.md
- 三角色架构 ADR：[0001](0001-adopt-agent-arch.md)
- Tech facts: @.claude/memory/shared/tech-stack.md, @.claude/memory/shared/global-commands.md
- Roadmap Week 0: @docs/roadmap.md（§Week 0）
- 当前 HEAD：`esp/xiaozhi-esp32/` @ `b392c63` (`Add M5Stack StickS3 board support. (#2060)`)
- Upstream: <https://github.com/78/xiaozhi-esp32>
- Web 烧录入口（baseline fallback）：<https://www.16302.com/firmwarehub/O3XoF1s>
