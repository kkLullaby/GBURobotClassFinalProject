---
id: 2026-06-19-m4-implement-show-emoji-and-text-024
from: planner
to: executor
parent: 2026-06-19-m4-tools-inventory-spike-023
supersedes:
status: pending
created: 2026-06-19
artifacts:
  - esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc (改：加 2 个 AddTool)
  - (不新建文件，全部加进现有 RegisterMcpTools)
  - sdkconfig 不动 (无新依赖)
---

## Why now

[H023 inventory](archive/2026-06-19-m4-tools-inventory-spike-023.md) verdict:
M4 新增 **2 个 tool**（show_emoji + show_text），各 ~20-25 LOC，复用现成
`Display::SetEmotion` / `Display::ShowNotification` / `Display::SetChatMessage`，
**0 新依赖**。esp/xiaozhi-esp32/main/boards/otto-robot/ 是 [CLAUDE.md §Project
Scope](../../../CLAUDE.md) 的 M4 反豁免——**写** OK。

`gesture` DROP（self.otto.action 已覆盖 26 个动作）；
`show_qr` DROP（用 show_text "扫码: <url>" 轻方案替代）。

本 handoff 是 M4 真实现，配合后续 H024.bis (user 烧 + 端到端测) 共同走完。

跟 H015 同模式：**agent 写代码 + planner main-loop unblock build 限制 + user
烧 ESP32**。Agent 在 sandbox 内能 grep + 写 .cc + 用 `idf.py size`（如果 IDF
可达），不能 `idf.py flash`。

## Objective

按 [m4-tools-plan §2](../designs/active/m4-tools-plan.md) 在
`esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc::RegisterMcpTools()`
末尾追加 **2 个新 AddTool 调用**：

1. `self.otto.show_emoji(name: string = "happy")` → `Display::SetEmotion(name)`
2. `self.otto.show_text(text: string, kind: string = "notification")`
   → `Display::ShowNotification(text, 3000)` 或 `Display::SetChatMessage`

完成后 `idf.py size` 看 binary 增量 (< 5 KB 算合格)；不在 sandbox 内 flash。

## Constraints

- 只改 `esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc` **一个文件**
- **不**改 `otto_movements.h/cc`、`otto_emoji_display.h/cc`、`websocket_control_server.*`
- **不**改 sdkconfig / dependencies.lock / idf_component.yml
- **不**新建文件
- **不**碰其它板子目录 (`boards/esp-hi/` 之类 — 上游只读)
- **不**改 Hermes / shim / xinnan-tech 任何文件
- 按 [contract](../contracts/api/v1/esp32-mcp-tools.md) §2 锁的 schema 写
  (tool name / inputs / description 必须一字不差对齐 contract)
- C++ 风格按现有 `otto_controller.cc` (4-space indent, lambda 同行起)
- 错误纪律：tool 内部 lambda 抓不到 display? → log warning + return true
  (不抛异常 / 不崩固件)
- **Sandbox-friendly write-only**：agent 在 sandbox 写代码 + 跑
  `idf.py size` 或 `idf.py build`（如果 sandbox 有 IDF；没就 What I Did
  说明）；**不**尝试 flash
- 一切用 ESP-IDF `idf.py` 工具链 (per [shared/global-commands](../../.claude/memory/shared/global-commands.md))

## Acceptance Criteria

- [ ] `otto_controller.cc::RegisterMcpTools()` 末尾追加 2 个 AddTool 调用：
      1. `self.otto.show_emoji`:
         - description = m4-tools-plan §2 写的（含 21 个 emoji 名字）
         - PropertyList = `{ Property("name", kPropertyTypeString, "happy") }`
         - lambda body = `Board::GetInstance().GetDisplay()->SetEmotion(
              properties["name"].value<std::string>().c_str()); return true;`
      2. `self.otto.show_text`:
         - description = contract §2 写的（含 kind 选项 + QR 轻方案提示）
         - PropertyList = `{ Property("text", kPropertyTypeString),
              Property("kind", kPropertyTypeString, "notification") }`
         - lambda body：
           ```cpp
           std::string text = properties["text"].value<std::string>();
           std::string kind = properties["kind"].value<std::string>();
           auto* display = Board::GetInstance().GetDisplay();
           if (kind == "chat") {
               display->SetChatMessage("system", text.c_str());
           } else {
               display->ShowNotification(text.c_str(), 3000);
           }
           return true;
           ```
- [ ] **不**改 `RegisterMcpTools()` 其余 8 个 tool 的代码
- [ ] **不**新建文件 / 不改 .h
- [ ] 跑 `idf.py size --component main` 或 `idf.py size`：
      - binary 增量 < 5 KB (相对 H1a baseline 3.5 MiB)
      - 仍在 4 MiB partition 内（free 余量 > 400 KB）
      - 输出贴 What I Did（≤ 20 行）
- [ ] 跑 `idf.py build` 通过 (warning 全是上游已有；**不**引入新 warning)
- [ ] `git diff esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc`
      只看到末尾追加段，不影响其它已有 tool
- [ ] `git status --short` 预期：
      ```
       M esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc
      ```
- [ ] **不**改 docs/contracts/api/v1/esp32-mcp-tools.md（已是 v1）
- [ ] **不**实现 emoji name 校验 / text 长度截断（按 plan §5 fallback 留
      给后续 polish）
- [ ] **不**真烧 ESP32

## Context Pointers

- @docs/handoffs/archive/2026-06-19-m4-tools-inventory-spike-023.md (decision)
- @docs/research-notes/m4-otto-tools-inventory.md (inventory + cite)
- @docs/designs/active/m4-tools-plan.md (**主参考**——签名/LOC/lambda 模板)
- @docs/contracts/api/v1/esp32-mcp-tools.md (schema 锁，**严格对齐**)
- @docs/designs/active/m4-bin-size-budget.md (442 KB 余量基线)
- @esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc:533-830
  (现有 8 AddTool；新加 2 个挂这函数末尾)
- @esp/xiaozhi-esp32/main/display/display.h:34-37 (SetEmotion /
  ShowNotification / SetChatMessage 接口)
- @esp/xiaozhi-esp32/main/display/lvgl_display/emoji_collection.cc:55-75
  (21 emoji 注册名)
- @esp/xiaozhi-esp32/main/application.cc:546,555,562 (现有调用样例)
- @.claude/memory/shared/global-commands.md §ESP32 (idf.py 命令)
- @CLAUDE.md §Project Scope (otto-robot/ 是 M4 反豁免)

## Out of Scope

- 不实现 emoji 名字 enum 强校验 (上游 LVGL 容错)
- 不实现 text 长度截断
- 不实现 show_qr 真 QR 渲染
- 不写 Hermes-side prompt 教 "gesture → action" 映射 (H026 / Week 3)
- 不烧 ESP32 (H024.bis user-led)
- 不写 ADR
- 不动 docs (本 handoff 写完即可，contract 已 v1)
- 不改 mcp-endpoint / shim / xinnan-tech 任何东西

## Candidate Root Causes（编译挂时先查）

1. **`Board::GetInstance().GetDisplay()` 返回类型** — 看现有
   `application.cc:546` 怎么用；可能是 `Display*` 也可能 `Display&`
2. **PropertyList default value 类型** — Property ctor 第三参数：String 是
   `"default"`, Integer 是 `int`；string 用 `std::string("happy")` 还是
   `"happy"` 字面量
3. **kPropertyTypeString 没 default 时 value() throw** — show_text.text 没
   default，LLM 不传会崩；要么给 default `""` 要么 lambda 内 check
4. **lambda 捕获** — 现有 8 tool 用 `[this](...)` 或 `[](...)`；本两个
   tool 不依赖 OttoController 实例，用 `[]` 即可
5. **`Display::ShowNotification(const std::string&, int)` 重载** —
   display.h:35 是 `const std::string &notification, int duration_ms = 3000`；
   传 c_str() 转回 string 会做隐式构造
6. **header 漏 include** — otto_controller.cc 已 include Board + Display
   header (看现有 `self.otto.get_ip` 用了 WifiManager)；如缺，加 include

## Suggested Steps

```bash
cd ~/code/robot_class/final_pro_xiaozhi_robot

# 1. 看现有 RegisterMcpTools 尾部 + 现有 Display 调用样例
sed -n '820,860p' esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc
# 找 } 结束 function 的位置, 在它前插

# 2. 看 Board::GetInstance + Display 接口在哪 include
grep -n 'include' esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc | head -10

# 3. 看现有 application.cc 怎么用 SetEmotion 当样例
grep -B1 -A1 'SetEmotion' esp/xiaozhi-esp32/main/application.cc | head -10

# 4. 用 Edit tool 在 RegisterMcpTools() 末尾追加 2 个 AddTool 块
# (照 contract / plan 的 schema)

# 5. build
source ~/esp-idf-5.5.2/export.sh
cd esp/xiaozhi-esp32
idf.py build 2>&1 | tail -30
# 期望: Successfully created esp32s3 image; 0 new warning

# 6. size
idf.py size 2>&1 | head -30
# 期望: Total image size < 4 MiB partition, app delta < 5 KB

# 7. git diff + status
cd ../..
git diff esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc | head -60
git status --short
```

## Error-handling discipline

- **Cosmetic** (typo / 缩进) → 自己改，What I Did 提一句
- **Substantive** (idf.py build 编译失败 / size 超 partition) → status: blocked
  + 完整 stderr + 已试 2-3 修法
- **不要超 scope**：2 tool 加完就停，**不**顺手补 enum 校验 / 截断 / 翻译
- **Sandbox 没 ESP-IDF**：只写代码 + py_compile-style syntax check
  (`grep` 看自己写的对不对) → status: blocked + 说明，由 planner main-loop
  跑 build (planner 主机有 idf 5.5.2)
- **不要 flash** (要 USB)

## Recovery

| 症状 | 修 |
|---|---|
| `idf.py build` 报 `Board::GetInstance` 找不到 | grep `#include "board.h"` 是否已在 otto_controller.cc 顶部 |
| `kPropertyTypeString` 链接错 | 看现有 `self.otto.action` 怎么 include `mcp_server.h` |
| AddTool 第 3 参 PropertyList 编译类型不匹配 | 抄 esp_hi.cc:302-390 的样例 |
| size 超 4 MiB | 不可能（4 KB 增量 vs 440 KB 余量）；若超说明代码写错 |
| sandbox 无 idf.py | blocked + 完整 stderr; planner main-loop 跑 |

## For Auditor

不发 auditor。M4 done = H024 + H024.bis (user 烧 + 端到端测)；M4 完整 batch
后跟 M2/M3 一起 review。

## Open Questions for Planner

- 写完后是否要测**Hermes 那侧能否 NLU 触发**？理想是 M4 done = Hermes 能
  让机器人 "笑一个" + "屏幕显示 hello"。这是 H024.bis 端到端测的事
- demo 答辩剧本要新加一段："对机器人说: 看见我开心的话就对我笑一个 →
  机器人调 show_emoji(happy) → 屏幕变笑脸"。这部分写在 docs/demo-script.md
  Polish (W3 末)
- gesture 用 `self.otto.action` 替代后，Hermes system prompt 怎么教？写
  一份 Hermes-side prompt template handoff (H026+)
