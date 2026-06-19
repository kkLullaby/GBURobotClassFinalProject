---
status: draft
version: v1
created: 2026-06-19
author: planner
handoff_id: 2026-06-19-m4-tools-inventory-spike-023
---

# Contract — ESP32 MCP Tools (M4 新增)

> 锁 M4 新增 tool 的 MCP 调用契约。Hermes 那侧按此 schema 写调用代码，
> ESP32 端按此 schema 实现 AddTool。改 schema = bump version + 写
> [CHANGELOG](../CHANGELOG.md)。

## §1 命名约定（跟上游 78/xiaozhi-esp32 一致）

- Namespace 前缀：`self.otto.*`（otto-robot 板自带，上游已立惯例）
- 命名：lowercase + snake_case（`show_emoji`，不是 `showEmoji`）
- 上游全部 8 tool 见
  [m4-otto-tools-inventory.md §1](../../../research-notes/m4-otto-tools-inventory.md)；
  本 contract 只锁**新增**部分

## §2 M4 新增 tool

### `self.otto.show_emoji`

| 字段 | 值 |
|---|---|
| description | "在屏幕上显示一个表情。name 是表情名称，21 个合法值：neutral / happy / laughing / funny / sad / angry / crying / loving / embarrassed / surprised / shocked / thinking / winking / cool / relaxed / delicious / kissy / confident / sleepy / silly / confused" |
| inputs | `name: string` (default `"happy"`, enum 上述 21 值之一) |
| returns | `bool` (true) |
| side effect | 屏幕 GIF 表情切换；无运动 |

### `self.otto.show_text`

| 字段 | 值 |
|---|---|
| description | "在机器人屏幕上显示文字。text 是要显示的字符串（≤30 汉字）。kind=notification 是 3 秒临时弹窗（默认，不影响对话 UI），kind=chat 是持久写进对话栏。展示 URL/二维码场景：用 kind=notification + text='扫码访问: <url>'" |
| inputs | `text: string`, `kind: string` (default `"notification"`, enum `"notification" \| "chat"`) |
| returns | `bool` (true) |
| side effect | 屏幕 UI 文字显示；无运动 |

## §3 上游已有 8 tool（**不锁** —— 上游可能升级；仅引用）

详见 [inventory §1](../../../research-notes/m4-otto-tools-inventory.md)：
- `self.otto.action`, `self.otto.servo_sequences`, `self.otto.stop`,
  `self.otto.set_trim`, `self.otto.get_trims`, `self.otto.get_status`,
  `self.battery.get_level`, `self.otto.get_ip`

> Hermes-side 调用这些 tool 时按上游 schema, 本 contract 不锁；
> 若上游变 (schema migration), 在 [CHANGELOG](../CHANGELOG.md) 写一条
> note 即可，**不**升 v 号（本 contract 只管"自加"部分）。

## §4 Versioning rules

- v1 = M4 demo 答辩前的 baseline (本文件 status: current 那天)
- bump v2 触发条件：
  - **新加 tool** (e.g. show_qr 真做了) → 不 bump，append §2 新表
  - **改已有 tool 的 input schema** (e.g. show_emoji 加 `duration` 参数)
    → bump v2 + 写 CHANGELOG entry + 旧的搬 `archive/v1/`
  - **删 tool** (e.g. show_text 撤掉) → bump v2 同上
- 每次 bump 都要在
  [docs/contracts/api/CHANGELOG.md](../CHANGELOG.md) 留一行

## §5 Transport 层（不属于本 contract 但提一下）

这些 tool 走 `type:"mcp"` 子帧上 ESP32 ↔ xiaozhi-server WS，server 再
通过 mcp-endpoint :8004 反向把 tool list/call 转给 Hermes 那侧。详见：
- [esp32-to-server-handshake.md §4.1](esp32-to-server-handshake.md)（`type:"mcp"` 子帧封装）
- [esp32-to-server-handshake.md §4.3](esp32-to-server-handshake.md)（mcp_endpoint 反向通道）

本 contract 假定 transport 已通 (H016 done)。

## §6 Open Questions

- show_emoji 的 `name` 走 OpenAI tool schema 的 `enum` 字段强约束 LLM,
  还是 free-form string + description 提示？前者更准但减灵活
- show_text 是否要拒绝 `text` 含纯 emoji unicode (LVGL CJK 字体不一定全 cover)?
- 二代版本可能加 `self.otto.set_volume`, `self.otto.play_sound` (扬声器
  控制)；先 v1 锁这两个 tool 即可
