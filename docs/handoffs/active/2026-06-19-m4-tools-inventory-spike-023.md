---
id: 2026-06-19-m4-tools-inventory-spike-023
from: planner
to: executor
parent: 2026-06-19-mcp-endpoint-server-bringup-016
supersedes:
status: pending
created: 2026-06-19
artifacts:
  - docs/research-notes/m4-otto-tools-inventory.md (new)
  - docs/designs/active/m4-tools-plan.md (new)
  - docs/contracts/api/v1/esp32-mcp-tools.md (new)
  - 不动 esp/xiaozhi-esp32/main/boards/otto-robot/ 任何代码 (本 spike 只读)
---

## Why now

ADR-0005 主线全验证：M2 路径打通（H018+H019+H020+H021），demo §1 答辩可演
（等 H022 完）。**Week 2 起点**：M4 = ESP32 端加 MCP tools 让 Hermes 调机器人
"做动作 / 展示 emoji / 显示文字"。

roadmap §2.1-2.3 计划加 4 个工具：

```
self.otto.show_emoji(name)
self.otto.gesture(name)
self.otto.show_text(text)
self.otto.show_qr(url)
```

但**上游 otto-robot 已有 8 个 tools**：

```
self.otto.action            (复合：方向/步数/速度/幅度/手臂摆动)
self.otto.servo_sequences   (AI 自定义动作序列)
self.otto.stop
self.otto.set_trim
self.otto.get_trims
self.otto.get_status
self.battery.get_level
self.otto.get_ip
```

→ "gesture" 已经基本在 `action`/`servo_sequences` 里覆盖；"show_emoji"
可能跟 `otto_emoji_display.{h,cc}` 已有接口重叠；"show_text" 和 "show_qr"
是新的（需要看 display 接口）。**必须先盘点再写，否则白干一遍**。

本 spike: 读 + 写 doc，**不动 C++ 代码**。Sandbox-friendly：上游
submodule 是只读的，本 handoff 是规划性质，不烧 ESP32 / 不接硬件。

## Objective

输出 3 份文档，让 Week 2 §2.1-2.3 的 4 个工具实现 (M4) 进入"开工即写"
状态：

1. **`docs/research-notes/m4-otto-tools-inventory.md`** — 上游已有 8 tool
   的逐项归类 + 我们计划新加 4 tool 的"vs 已有的差异/复用判断"
2. **`docs/designs/active/m4-tools-plan.md`** — 4 个新 tool 的最终决定
   （加 / 改名复用 / 撤掉），每个含：tool 全名 / 入参 schema / 返回值 /
   底层 API (display? otto_movements? 新建?) / LOC 估算 / 风险点
3. **`docs/contracts/api/v1/esp32-mcp-tools.md`** — 新增 4 tool (或裁后
   N tool) 的 MCP 协议契约，用于 Hermes 那侧调用模式锁定（不能漂移）

**不动代码**。M4 真实现是后续 H024 / H025 起来写。

## Constraints

- 不动 `esp/xiaozhi-esp32/main/boards/otto-robot/` 任何 C++ 代码
- 不动 `xiaozhi-mcp-adapter/` / `openai-shim/`
- 不动 `~/.hermes/` / docker
- 不动现有 ADR (本 spike 不引入新 ADR；M4 真改架构时另起)
- 不真烧 ESP32 / 不跑 idf.py
- 不实现 M4 plugin/skill (Hermes 那侧的工具)
- 上游代码**读** OK + 引用 OK；不许 patch 上游 (per CLAUDE.md §Project Scope)
- 文档语言中文 (跟全项目一致)
- 错误纪律：找不到对应 display API → blocked + 已搜过的 path 列出
- **Sandbox-friendly**：纯读 + 纯写 doc，agent 在 sandbox 内能完整跑

## Acceptance Criteria

- [ ] 新建 `docs/research-notes/m4-otto-tools-inventory.md` ≤ 200 行，含：
      - §1 上游已有 8 tool 逐项表格 (name / desc / inputs / 返回值 / 用途
        分类 [motion / sensing / config / system])
      - §2 我们计划新加 4 tool 的逐项 "vs 已有"：
        - `show_emoji` ← 跟 `otto_emoji_display.h` API 对比，是 wrap 已有
          函数 (新工具) 还是有 tool 已暴露
        - `gesture` ← 跟 `self.otto.action`/`servo_sequences` 对比，是
          "shortcut wrap" 还是冗余
        - `show_text` ← 找 LCD/OLED 显示文字的接口在哪 (otto-robot 用什么
          display chip; grep `display.h` / `lcd.h`)
        - `show_qr` ← 同上，找 QR 渲染库 (是否已 link, esp_qrcode / 自写)
      - §3 verdict 表：每个新 tool 标 "ADD" / "REPLACE-X" / "DROP-redundant" /
        "BLOCK-need-new-driver"
      - §4 cite 文件路径 + 行号 (`file_path:line_number` 格式，clickable)
- [ ] 新建 `docs/designs/active/m4-tools-plan.md` ≤ 150 行，含：
      - frontmatter `status: draft` + `created: 2026-06-19`
      - §1 最终 tool 列表 (基于 inventory verdict)
      - §2 每个 tool 一段：
        - **签名**：`self.otto.<name>(<params>)` + 入参类型/范围
        - **行为**：调用底层什么、副作用
        - **返回值**：string / json
        - **C++ LOC 估算**：基于复杂度的范围 (10-50 line / 50-200 / etc)
        - **风险点**：编译产物增量 (M1 baseline 3.5MiB / 4MiB partition,
          剩 440KB; 见 docs/designs/active/m4-bin-size-budget.md) — 引这
          条目
        - **Hermes 那侧调用风格**：Hermes user 怎么说话会触发它 (示例 NLU)
      - §3 实施顺序 (谁先谁后)
      - §4 Open Questions for executor (M4 真开工时再决)
- [ ] 新建 `docs/contracts/api/v1/esp32-mcp-tools.md` ≤ 100 行，含：
      - frontmatter `status: draft` + `version: v1`
      - §1 namespace (`self.otto.*`) + 命名约定 (跟上游一致 lowercase
        snake)
      - §2 每个新 tool 一行：
        ```
        | tool name | description | inputs | returns |
        ```
      - §3 versioning (这些 tool 接口锁定后, 若 M4 实现要改, 该改这个
        contract + bump version + 写 CHANGELOG)
- [ ] **不**写 C++ / Python 代码
- [ ] **不**改 `docs/handoffs/INDEX.md` (planner 主体维护)
- [ ] **不**起 ADR (Week 2 真改架构时再起)
- [ ] `git status` 输出贴 What I Did，预期：
      ```
      ?? docs/research-notes/m4-otto-tools-inventory.md
      ?? docs/designs/active/m4-tools-plan.md
      ?? docs/contracts/api/v1/esp32-mcp-tools.md
      ```

## Context Pointers

- @docs/roadmap.md §Week 2 §2.1-2.3 (4 tool 原计划)
- @docs/designs/active/m4-bin-size-budget.md (442 KB 余量约束)
- @docs/contracts/api/v1/esp32-to-server-handshake.md (`type:"mcp"` 子帧
  协议；M4 tool 都走这条)
- @esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc:533-830
  (已有 8 个 AddTool 调用，**关键**——直接读这段)
- @esp/xiaozhi-esp32/main/boards/otto-robot/otto_emoji_display.h
  (emoji 接口在哪)
- @esp/xiaozhi-esp32/main/boards/otto-robot/otto_movements.h
  (gesture 候选源)
- @esp/xiaozhi-esp32/main/boards/esp-hi/esp_hi.cc:302-390 (上游另一个板子的
  AddTool 模板，参考写法)
- @CLAUDE.md §Project Scope (otto-robot/ 是 M4 反豁免，**写** OK 但本
  handoff 还不写)
- @.claude/memory/shared/global-commands.md (idf 命令以备)

## Out of Scope

- 不实现 M4 真 tool C++ 代码 (后续 H024 / H025)
- 不调 hermes 那侧 (M4 工具的 hermes-side schema)
- 不调 mcp-endpoint-server (H016 已通)
- 不写 ADR
- 不烧 ESP32 / 不动 idf.py
- 不评估真 LCD/OLED 性能 / 不写驱动
- 不实现 QR 渲染算法

## Candidate Root Causes（spike 找不到信息时先查）

1. **otto_emoji_display.h 接口太简** — 可能只有 `Show(EmojiId)` 之类；
   若 emoji set 是硬编码 enum，**`show_emoji(name)` 要先做 name → enum 映射**
2. **没有 LCD/OLED text 直接 API** — otto-robot 可能只有 emoji，没原始
   text 渲染；`show_text` 可能要新建 driver (重，跳到 v2)
3. **没 QR library link** — esp_qrcode 是上游可选 component；要 dependencies.lock
   里加，**会触发重新 download managed_components**
4. **action/servo_sequences 已 cover gesture 80%** — `gesture("wave")`
   可能就是 `self.otto.action(action="wave", direction=0, steps=2)` 的简写；
   verdict 应该是 "DROP-redundant" 或 "ADD-as-shortcut"
5. **inventory 找漏 tool** — `otto_controller.cc` 可能不是全部 AddTool 调
   用点；要 `grep -rn 'AddTool' esp/xiaozhi-esp32/main/boards/otto-robot/`

## Suggested Steps

```bash
# 0. 切到仓库根
cd ~/code/robot_class/final_pro_xiaozhi_robot

# 1. 把上游 8 tool 完整拉出来
grep -n -B1 -A8 'AddTool(' esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc

# 2. 看 emoji display 接口
ls esp/xiaozhi-esp32/main/boards/otto-robot/otto_emoji_display.h
grep -n 'class\|void\|Show\|Display\|Emoji' esp/xiaozhi-esp32/main/boards/otto-robot/otto_emoji_display.h | head -30

# 3. 看 movements 接口
grep -n 'class\|void\|Action\|wave\|dance' esp/xiaozhi-esp32/main/boards/otto-robot/otto_movements.h | head -30

# 4. 找 LCD/display 在哪
grep -rn 'lvgl\|lv_label\|display\|lcd' esp/xiaozhi-esp32/main/boards/otto-robot/*.h 2>&1 | head -20

# 5. 找 QR 是否已 link
grep -rn 'qrcode\|esp_qrcode' esp/xiaozhi-esp32/main/idf_component.yml \
    esp/xiaozhi-esp32/managed_components/ 2>&1 | head -10

# 6. 写 3 个 docs (按 AC 顺序)
mkdir -p docs/research-notes docs/designs/active docs/contracts/api/v1
# (用 Write/Edit 工具写)

# 7. git status
git status --short
```

## Error-handling discipline

- **Cosmetic** (typo / doc 排版) → 自己改、What I Did 提一句
- **Substantive** (找不到 display API / 不知 QR 怎么集成) → status: blocked
  + 列出已 grep 的所有 path + 已读的所有 file
- **不要超 scope**：spike 是规划，**不要**顺手写 C++ 或试编译

## Recovery

| 症状 | 修 |
|---|---|
| grep 不到 emoji_display 接口 | 试 .cc 而不是 .h；或 `find esp/xiaozhi-esp32/main -name '*emoji*'` |
| display 接口在上游别处 | 看 `esp/xiaozhi-esp32/main/display/` 目录 |
| 不确定 esp_qrcode 是否已 link | `find esp/xiaozhi-esp32/managed_components -name 'esp_qrcode*'` |
| 该写 contract 但不确定 schema | 抄上游已有 AddTool 的 PropertyList 写法当模板 |

## For Auditor

不发 auditor。spike 是规划性质；M4 真实现 (H024+) batch 后一起 review。

## Open Questions for Planner

- M4 真开工 (H024) 应该 user 还是 agent？
  - **User 烧** ESP32 是必须的 (idf.py flash 要 USB)
  - **Agent 写 C++ 代码** OK，但跑不了 build (sandbox 没 ESP-IDF)
  - 套路：agent 写代码 + planner main-loop unblock + user 烧 (类似 H012/H015)
- 4 tool 一次性加完 vs 分批：roadmap 1.5 day 估算；spike 后给真 LOC
- emoji set 用上游 enum 还是开放参数？前者安全后者灵活
- M4 完成后 demo 可以演的"动作链"长什么样 (Week 2 验收)
