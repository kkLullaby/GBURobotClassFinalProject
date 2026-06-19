---
status: current
created: 2026-06-19
author: planner
handoff_id: 2026-06-19-m4-tools-inventory-spike-023
---

# M4 — otto-robot MCP Tools Inventory

> Week 2 §2.1-2.3 工作量定责文档。盘点 78/xiaozhi-esp32 上游 otto-robot 板
> 已有 MCP tools 与 display 接口，决定 roadmap 计划的 4 个新 tool
> (show_emoji / gesture / show_text / show_qr) 哪些 ADD / DROP / BLOCK。

## §1 上游已有 8 个 MCP tool（otto_controller.cc:533-830）

来源：`grep -n 'AddTool(' esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc`

| Tool name | desc 摘要 | 输入 properties | 返回值 | 分类 |
|---|---|---|---|---|
| `self.otto.action` | 26 个预设动作（walk/turn/jump/swing/moonwalk/bend/shake_leg/updown/whirlwind_leg/sit/showcase/home/hands_up/hands_down/hand_wave/windmill/takeoff/fitness/greeting/shy/radio_calisthenics/magic_circle 等） | action:str (default sit), steps:int [1-100], speed:int [100-3000], direction:int [-1..1], amount:int [0-170], arm_swing:int [0-170] | bool | motion |
| `self.otto.servo_sequences` | AI 自定义即兴动作编程；舵机底层控制 (ll/rl/lf/rf/lh/rh 各 0-180°)；普通模式 + 振荡模式 (osc) | sequence:str (JSON) | bool | motion-advanced |
| `self.otto.stop` | 立即停止所有动作并复位 | — | bool | motion-system |
| `self.otto.set_trim` | 校准单个舵机位置（永久保存） | servo:str + value:int | bool | config |
| `self.otto.get_trims` | 获取当前舵机微调设置 | — | JSON | sensing-config |
| `self.otto.get_status` | 返回 "moving" 或 "idle" | — | str | sensing |
| `self.battery.get_level` | 电量+充电状态 | — | JSON | sensing |
| `self.otto.get_ip` | WiFi IP | — | str | sensing |

**观察**：现有 8 tool 全是 **机器人本体 (motion/sensing/config)**，**完全没有
display 相关的 tool**。display 接口存在但**没暴露给 MCP**。

## §2 计划新加 4 tool vs 已有的对比

### show_emoji ← display 现成 + 21 emoji 现成 → **ADD**

- 上游 `Display::SetEmotion(const char* emotion)` 已虚函数化
  ([display.h:36](../../esp/xiaozhi-esp32/main/display/display.h#L36))
- otto-robot 用 `OttoEmojiDisplay : public SpiLcdDisplay` 继承
  ([otto_emoji_display.h:8](../../esp/xiaozhi-esp32/main/boards/otto-robot/otto_emoji_display.h#L8))
- emoji 集合已注册 21 个名字（neutral / happy / laughing / funny / sad / angry /
  crying / loving / embarrassed / surprised / shocked / thinking / winking /
  cool / relaxed / delicious / kissy / confident / sleepy / silly / confused）
  ([emoji_collection.cc:55-75](../../esp/xiaozhi-esp32/main/display/lvgl_display/emoji_collection.cc))
- otto-robot 用 GIF 版本 (DEFAULT_EMOJI_COLLECTION=otto-gif)
- application.cc:562 已在 server 推 emotion 时调用 `display->SetEmotion(emotion_str)`
  → 链路已 plumbed
- **新 tool 实质 = 把 SetEmotion 暴露给 MCP**，wrap **~20 LOC**
- 风险：emoji name 用 string 还是 enum？建议 string + 文档贴 21 个名（跟上
  游 `set emotion` 协议一致），调错就静默忽略

### gesture ← action 已全覆盖 → **DROP-redundant**

- `self.otto.action(action="wave", ...)` 即 `gesture("wave")` 的真子集
  - action 名清单：walk / turn / jump / swing / moonwalk / bend / shake_leg /
    updown / whirlwind_leg / sit / showcase / home / hands_up / hands_down /
    hand_wave / windmill / takeoff / fitness / greeting / shy /
    radio_calisthenics / magic_circle (26+ 个，**包含**所有"姿态"动作)
- otto_movements.h:65-86 暴露了 Walk/Turn/Jump/Bend/HandWave/Windmill/...
  整套底层 API
- 如果 user 想要 "gesture('wave')" 这种缩写，**不是 MCP 层加 tool**，是
  **Hermes 那侧 prompt engineering**：在 system prompt 教 Hermes "若想挥手
  调 self.otto.action(action='hand_wave')"
- **节省**：~30-50 LOC 重复定义 + 0 KB binary 增量

### show_text ← display 现成 + 没 tool → **ADD**

- 上游 `Display::SetChatMessage(const char* role, const char* content)` 现成
  ([display.h:37](../../esp/xiaozhi-esp32/main/display/display.h#L37))
- 还有 `ShowNotification(const char*, int duration_ms = 3000)` 临时弹窗版
  ([display.h:34-35](../../esp/xiaozhi-esp32/main/display/display.h#L34))
- application.cc:546/555 已在收到 user/assistant message 时调
  SetChatMessage 渲染 → 链路已 plumbed
- **新 tool 实质 = 把 ShowNotification (或 SetChatMessage) 暴露给 MCP**
  → ~25 LOC
- 风险：text 长度限制 (UI 上一行最多~20 个汉字)；多行换行手动控；过长
  截断
- 建议：tool 用 ShowNotification (临时, 3s 后消失)，避免覆盖正常对话 UI

### show_qr ← 无 qrcode 库 → **BLOCK-need-new-dep**

- `find esp/xiaozhi-esp32/managed_components -name '*qrcode*'` → **空**
- `find esp/xiaozhi-esp32/main -name idf_component.yml -exec grep qrcode` → 无
- 唯一上游可选 component 是 `espressif/esp_qrcode`（ESP-IDF official，
  300+ KB binary）；加入会 trigger `idf.py reconfigure` + managed_components
  全量重 download (~5-10 min)
- LVGL 那侧渲染 QR 也要写 ~100-200 LOC (canvas + module 像素映射)
- 增量风险：m4-bin-size-budget 估算 binary 余量 ~440 KB；esp_qrcode +
  渲染代码 ~350 KB → 余量降到 90 KB，**接近极限**，挤掉其它 tool 空间
- 也可选 **轻方案**：把 URL 作为 string `ShowNotification("扫码访问: <url>")`
  让用户手动输入。**0 binary 增量, 演示效果差但答辩可解释**
- **verdict**：M4 demo 答辩**不上**真 QR；用 **轻方案** 作为 `show_text` 的
  特例 (param 含 url 时拼 "扫码: " 前缀)；真 QR 留 v2 (post-demo)

## §3 Verdict 汇总

| 计划 tool | Verdict | 实现路径 | LOC | Binary 增量 |
|---|---|---|---|---|
| show_emoji | **ADD** | wrap Display::SetEmotion | ~20 | <2 KB |
| gesture | **DROP-redundant** | 用现成 self.otto.action + Hermes prompt | 0 | 0 |
| show_text | **ADD** | wrap Display::ShowNotification | ~25 | <2 KB |
| show_qr | **BLOCK-need-new-dep** → 轻方案 fold into show_text | wrap ShowNotification with "扫码: " prefix | (+5 LOC 进 show_text) | 0 |

**最终 M4 新增 2 个 tool** (`show_emoji` + `show_text`)，~50 LOC，~4 KB
binary 增量；剩 ~436 KB 余量给 Week 3+ 加更多 tool 或诊断功能。

## §4 引用清单（点击可跳）

- otto-robot 已有 tool：
  `esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc:533`
  `esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc:668`
  `esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc:708`
  `esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc:722`
  `esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc:782`
  `esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc:805`
  `esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc:810`
  `esp/xiaozhi-esp32/main/boards/otto-robot/otto_controller.cc:824`
- Display base：
  `esp/xiaozhi-esp32/main/display/display.h:33`（SetStatus）
  `esp/xiaozhi-esp32/main/display/display.h:34`（ShowNotification）
  `esp/xiaozhi-esp32/main/display/display.h:36`（SetEmotion）
  `esp/xiaozhi-esp32/main/display/display.h:37`（SetChatMessage）
- Emoji 注册：
  `esp/xiaozhi-esp32/main/display/lvgl_display/emoji_collection.cc:55-75`（21 个 32px 版本）
  `esp/xiaozhi-esp32/main/display/lvgl_display/emoji_collection.cc:103-123`（21 个 64px 版本）
- Otto display 子类：
  `esp/xiaozhi-esp32/main/boards/otto-robot/otto_emoji_display.h:8`
  `esp/xiaozhi-esp32/main/boards/otto-robot/otto_emoji_display.cc`
- 调用样例：
  `esp/xiaozhi-esp32/main/application.cc:546`（SetChatMessage("assistant", ...)）
  `esp/xiaozhi-esp32/main/application.cc:555`（SetChatMessage("user", ...)）
  `esp/xiaozhi-esp32/main/application.cc:562`（SetEmotion）
- Otto movements API：
  `esp/xiaozhi-esp32/main/boards/otto-robot/otto_movements.h:33-86`
- 板子 inverse-exemption 范围：
  `CLAUDE.md` §Project Scope §M4 例外纳入区
- Binary 余量基准：
  `docs/designs/active/m4-bin-size-budget.md`
- 参考实现：
  `esp/xiaozhi-esp32/main/boards/esp-hi/esp_hi.cc:302-390`（另一板子 AddTool 模式）

## Open Question for design phase（H024 实现前决）

- `show_emoji` 用 `string name` 还是 `enum index`？前者 21 个名一一对应方便
  prompt，后者更紧凑但难记
- `show_text` 用 ShowNotification (临时 3s) 还是 SetChatMessage (持久占栏)？
  前者不挡对话 UI，后者像"机器人主动说"
- gesture 真 drop 后，需要给 Hermes 加一段 prompt 解释 "想挥手时调
  action(action='hand_wave')"——这部分文档归 Hermes-side handoff (H025+)
- QR 真要做 → 走另一条 spike，调研 espressif/esp_qrcode 在 OttoRobot
  binary 余量下能否 fit
