---
status: draft
created: 2026-06-19
author: planner
handoff_id: 2026-06-19-m4-tools-inventory-spike-023
supersedes:
---

# M4 — Otto Tools Implementation Plan

> 基于 [inventory](../../research-notes/m4-otto-tools-inventory.md)
> verdict，给 Week 2 §2.1-2.3 的实施 (M4) 落 LOC + risk + Hermes 调用风格。
> 本设计 status: draft；M4 真开工 (H024) 时可 promote to current。

## §1 最终 tool 列表

| Tool | 状态 |
|---|---|
| `self.otto.show_emoji` | NEW (ADD) |
| `self.otto.show_text` | NEW (ADD, 含 QR 轻方案) |
| ~~`self.otto.gesture`~~ | DROPPED — 用现成 `self.otto.action` + Hermes prompt |
| ~~`self.otto.show_qr`~~ | DROPPED for M4 demo — 真 QR 走另起 spike |

## §2 每个 tool 的设计

### `self.otto.show_emoji(name: str)` — NEW

- **签名**：`self.otto.show_emoji(name="happy")`
- **入参**：
  - `name` — string，21 个合法值：neutral / happy / laughing / funny / sad /
    angry / crying / loving / embarrassed / surprised / shocked / thinking /
    winking / cool / relaxed / delicious / kissy / confident / sleepy /
    silly / confused
  - 默认值：`"happy"`
- **行为**：调 `Board::GetInstance().GetDisplay()->SetEmotion(name.c_str())`
  - 显示对应的 GIF 表情在 LCD 上
  - 未定义 name → emoji_collection 找不到时 LVGL 显示 "?" 或 fallback（不崩）
- **返回值**：`true` (永远成功，OttoEmoji 内部容错)
- **底层 API**：`Display::SetEmotion` ([display.h:36](../../esp/xiaozhi-esp32/main/display/display.h#L36))
- **C++ LOC**：~20 (1 个 AddTool + lambda + properties)
- **Binary 增量**：<2 KB（仅多 1 个 lambda，emoji 资源已 link）
- **风险点**：
  - emoji name 跟 server 推过来的 emotion name 必须**完全一致**（已知 21 个 set）
  - 21 个名字写进 description string → ~600 字符 description，注意
    [m4-bin-size-budget](m4-bin-size-budget.md) 余量（440 KB 富裕）
- **Hermes 调用示例**：
  - User: "对我笑一个" → LLM 调 `self.otto.show_emoji(name="laughing")`
  - User: "你看起来好像在思考" → LLM 调 `self.otto.show_emoji(name="thinking")`
  - User: "做出爱心眼" → LLM 调 `self.otto.show_emoji(name="loving")`

### `self.otto.show_text(text: str, kind: str = "notification")` — NEW

- **签名**：`self.otto.show_text(text="...", kind="notification")`
- **入参**：
  - `text` — string，UI 上推荐 ≤ 30 个汉字（80 byte），LVGL 自动换行
  - `kind` — string, `"notification"` (default, 3s 临时弹窗) 或
    `"chat"` (持久写进对话 UI)；当 text 形如 `https?://...` 时建议 NLU 选
    notification
- **行为**：
  - kind=notification → `display->ShowNotification(text, 3000)`
  - kind=chat → `display->SetChatMessage("system", text.c_str())`
- **返回值**：`true`
- **底层 API**：`Display::ShowNotification` ([display.h:34](../../esp/xiaozhi-esp32/main/display/display.h#L34))
  和 `Display::SetChatMessage` ([display.h:37](../../esp/xiaozhi-esp32/main/display/display.h#L37))
- **C++ LOC**：~25
- **Binary 增量**：<2 KB
- **QR 轻方案**：在 description 里教 LLM "若要展示二维码/链接, 用 kind=
  notification + text='扫码访问: <url>'"; **不实现** QR 渲染
- **风险点**：
  - text 含 emoji unicode 会怎样？LVGL CJK 字体配置决定；可能显 "[]"
    → demo 前测一遍
  - SetChatMessage 持久占栏可能挡正常对话流；建议默认 notification
- **Hermes 调用示例**：
  - User: "屏幕上显示今天的日期" → LLM 调 `show_text(text="2026-06-19 周五")`
  - User: "把这个链接显示出来 https://example.com" → LLM 调
    `show_text(text="扫码访问: https://example.com", kind="notification")`
  - User: "记下我刚说的话" → LLM 调 `show_text(text="<前一句>", kind="chat")`

### ~~`self.otto.gesture`~~ — DROPPED

- 完全被 `self.otto.action` 覆盖
- 后续工作：写一段 Hermes system prompt 教 LLM 用 `action()`：
  ```
  When user asks for a gesture (wave / dance / sit / nod / ...),
  invoke self.otto.action with action="hand_wave" / "magic_circle" /
  "sit" / "shy" / etc. Available actions: walk, turn, jump, swing,
  moonwalk, bend, shake_leg, updown, whirlwind_leg, sit, showcase,
  home, hands_up, hands_down, hand_wave, windmill, takeoff, fitness,
  greeting, shy, radio_calisthenics, magic_circle.
  ```
- 这部分 Hermes-side prompt 走单独的 handoff（H025+ Hermes
  channel/prompt 设计）

### ~~`self.otto.show_qr`~~ — DROPPED FOR M4 DEMO

- 真 QR 渲染走另起 spike：调研 `espressif/esp_qrcode` 在 OttoRobot 4 MiB
  partition + 440 KB 余量下能否 fit；LVGL canvas + module 像素映射
- demo 答辩用 `show_text` 的 QR 轻方案 ("扫码访问: <url>") 替代

## §3 实施顺序（H024）

1. **show_emoji** 先（最简单，~30 min 写 + flash + 测）
2. **show_text** (notification mode 优先, chat mode 加 default switch
   后续) (~45 min)
3. 写 Hermes system prompt 教 `gesture → action` mapping（5 min）
4. 端到端 demo: 跟机器人说 "对我笑一下 + 屏幕显示 hello" → 测两个新 tool

总估算：**~1.5 小时编码 + flash + 端到端测**（roadmap 给 1.5 day, 我们
裁到半天，省下时间给 H022 polish + Week 3 准备）。

## §4 Open Questions for executor (H024)

- show_text 默认 kind 选 notification 还是 chat？（推 notification）
- emoji 21 个名字写不写进 tool description？（推荐写，长但帮 LLM 选对）
- AddTool 注册位置：跟现有 `RegisterMcpTools()` 同函数加，还是新建
  `RegisterDisplayTools()`？（推 同函数 + comment 分段）
- 测试方法：单元测 OK 但 ESP32 没单元测框架；靠 idf.py monitor + 手测
- 编译 flash 烧需 ~15 min 周期；建议先 2 tool 一起加再烧（不要 1 个 1 烧）

## §5 风险 & fallback

| 风险 | fallback |
|---|---|
| show_emoji name 跟 emoji_collection 注册名漂移（上游升级动了名字） | 看 emoji_collection.cc 当前 21 名为权威；description 字面写出，测试一一 cover |
| show_text 长字符串 LVGL 渲染卡 | 限制 ≤ 80 byte，超出截断 (代码层) |
| binary 超 4 MiB partition | 删 emoji 64px 版本？或砍掉部分动作？（极不希望） |
| Hermes 不主动调 (LLM 没 NLU 触发) | tool description 写更详细 + Hermes system prompt 加示例 |

## References

- [m4-otto-tools-inventory.md](../../research-notes/m4-otto-tools-inventory.md)
- [m4-bin-size-budget.md](m4-bin-size-budget.md)
- [esp32-mcp-tools.md](../../contracts/api/v1/esp32-mcp-tools.md)
- [otto_controller.cc:533-830](../../../esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc)
- [display.h:33-37](../../../esp/xiaozhi-esp32/main/display/display.h)
- [emoji_collection.cc:55-75](../../../esp/xiaozhi-esp32/main/display/lvgl_display/emoji_collection.cc)
