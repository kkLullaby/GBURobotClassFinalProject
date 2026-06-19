# 实施路线图（4 周）

> 配合 [architecture.md](architecture.md) 阅读。每周给出**可执行任务**、**验收标准**（demo-able）、**风险**、**降级方案**。

---

## 总览

| 周次 | 主线交付 | 完成判定（你能跑给别人看的事） |
|------|----------|------|
| **Week 0** | 环境就绪：xiaozhi 全链路裸跑 | 你对着机器人说话，它能用某个公有 LLM 回复 |
| **Week 1** | M2 openai-shim：Hermes 接入对话流 | 你说话 → Hermes TUI 看到消息 → 回复经机器人朗读 |
| **Week 2** | M4 + M1：Hermes 能调机器人工具 | TUI 输入 "show emoji happy"，机器人屏幕变笑脸 |
| **Week 3** | M3 + 场景一：完整 channel + cron | 早上自动播报 PR / 跨 channel 投递 |
| **Week 4** | 场景二 + Demo + 报告 | 4 分钟答辩 demo 走通 3 遍不翻车 + 报告完稿 |

---

## Week 0 ▸ 环境就绪（5-7 天弹性）

### 任务清单

| # | 任务 | 估时 | 验收 |
|---|------|------|------|
| 0.1 | 装 ESP-IDF 5.5.2，编译并烧录 otto-robot 板子型号 | 半天 | `idf.py monitor` 看到 "boot ok"，屏幕亮 |
| 0.2 | 起 xinnan-tech minimal Docker | 半天 | `docker logs` 显示 server 监听 8000/8003/8004 |
| 0.3 | menuconfig 配 ESP32 连本地 server（OTA URL + WS URL） | 1 天 | server 日志看到设备 hello 包，机器人能进对话状态 |
| 0.4 | 配一个临时 LLM 后端（如 DeepSeek 或 Ollama 跑个 7B） | 1 天 | 对机器人说"你好"，它说"你好，请问有什么可以帮你"|
| 0.5 | 装 Hermes Agent (`uv tool install hermes-agent`) + TUI 起一次 | 半天 | `hermes` 进 TUI，能对话（用任何 LLM provider）|
| 0.6 | 阅读 Hermes 的 `plugins/platforms/discord/` 全部代码 | 1 天 | 能口述 "VoiceReceiver 如何处理音频帧" |
| 0.7 | 阅读 xinnan-tech 的 `core/providers/llm/openai/openai.py` 和 `docs/mcp-endpoint-integration.md` | 半天 | 能解释 base_url 替换点和 MCP接入点握手流程 |

### 验收 demo

> 站在机器人面前说："小智，你叫什么名字"，机器人回答"我叫小智"。
> 同时在另一个终端 `hermes` 已启动，可以独立对话。
> （此时 xiaozhi 和 Hermes 互不相干）

### 风险 & 降级

- **🔥 风险 1**：ESP32 板子型号选错（看 [README.md](../README.md)）→ 屏幕黑、麦克风无声
  - **缓解**：menuconfig 第一件事是确认 `Board Type → Otto Robot`
- **🔥 风险 2**：xinnan-tech 的 ASR 选了在线服务但你没注册 → 不识别
  - **降级**：先用 FunASR 本地版（自带，无需 key）
- **风险 3**：ESP32 OTA URL 配错，导致连不上 server
  - **缓解**：用 `nc -l 8003` 先验证 ESP32 出包正常

### 这一周做完 = 你证明了上游链路是通的，没有底层惊喜

---

## Week 1 ▸ openai-shim：把 Hermes 接入对话主线

### 任务清单

| # | 任务 | 估时 | 验收 |
|---|------|------|------|
| 1.1 | 用 FastAPI 写 `openai-shim`：实现 `POST /v1/chat/completions` (non-stream 先跑通) | 1 天 | curl 直接打能拿到响应 |
| 1.2 | 调通 streaming SSE：Hermes 输出按 token chunk 推回 | 1-2 天 | curl 看到 `data: {"choices":[{"delta":...}]}\n\n` 流 |
| 1.3 | 把 shim 集成进 Hermes：用 Hermes 的 MCP server (`hermes mcp serve`) 或 `events_wait` 接 session | 1-2 天 | Hermes TUI 启动后，shim 能 push 进 session 并收回回复 |
| 1.4 | xinnan-tech 配 `base_url` 指向 shim | 半天 | 对机器人说话，**Hermes TUI 里能看见这句话进来**，机器人朗读 Hermes 的回复 |
| 1.5 | session 复用策略：用 ESP32 `device_id` 作为 chat_id 持久化 | 半天 | 多轮对话上下文不丢 |

### 验收 demo（这周完成后该能演这个）

> 1. 你对机器人说："**我叫 kk**"，机器人答："好的 kk，记住了"  
> 2. 切到电脑前 `hermes` TUI，看到这两轮对话历史  
> 3. 在 TUI 里直接打："**我叫什么**"，TUI 回答 "kk"  
> 4. 回到机器人说："**我叫什么**"，机器人回答 "kk" —— **证明 session 一致**

> （这一步把"机器人"和"终端"变成同一个 Hermes 对话的两个 channel）

### 风险 & 降级

- **🔥 风险 1**：Hermes 的 session 注入机制需要走 internal API 而非 public 接口
  - **应对**：先 spike Hermes 的 `mcp_serve.py` 的 `messages_send` 工具，看看能不能从外部触发新消息
  - **降级**：如果实在不能，shim 直接调 Hermes 用的 LLM provider（绕开 agent loop），失去 tool calling 能力但能朗读
- **风险 2**：SSE chunk 格式不严格 → xinnan-tech 解析失败、机器人静音
  - **应对**：参考 [OpenAI streaming 文档](https://platform.openai.com/docs/api-reference/chat/streaming) 严格对齐字段
- **风险 3**：延迟太大（>3s 用户体验差）
  - **应对**：测每一段延迟，瓶颈通常在 ASR 或 LLM provider 选择

### 这一周做完 = Hermes 真正变成机器人的"大脑"

---

## Week 2 ▸ M4 + M1：让 Hermes 能调机器人工具

### 任务清单

| # | 任务 | 估时 | 验收 |
|---|------|------|------|
| 2.1 | ESP32 端在 `otto_robot.cc::InitializeTools()` 加 `xiaozhi.show_emoji(name)` 工具 | 半天 | xinnan-tech 后台看到 tool 注册成功 |
| 2.2 | 同方式加 `xiaozhi.gesture(name)`（调 OttoMovements 现成动作） | 半天 | 同上 |
| 2.3 | 同方式加 `xiaozhi.show_text(text)` / `xiaozhi.show_qr(url)` | 1 天 | 用 xinnan-tech 自带的 MCP 测试页面手动调，机器人有反应 |
| 2.4 | 写 `xiaozhi-mcp-adapter`：抄 `78/mcp-calculator/mcp_pipe.py`，连 xiaozhi MCP接入点 | 2-3 天 | adapter 能 list tools 列出上述工具 |
| 2.5 | 把 adapter 注册到 Hermes（`cli-config.yaml` 的 `mcp_servers:`） | 半天 | `hermes` 启动日志显示 4 个 tool 加载成功 |
| 2.6 | 端到端联调 | 1-2 天 | TUI 输入 "让机器人挥手"，agent 调 `xiaozhi.gesture("wave")`，机器人挥手 |

### 验收 demo

> 在 Hermes TUI 输入：「**显示一个笑脸，然后跳支舞，最后说我跳完了**」  
> Agent 依次调用：`show_emoji("happy")` → `gesture("dance")` → `speak("我跳完了")`  
> 机器人按顺序完成。

### 风险 & 降级

- **🔥 风险 1**：xiaozhi MCP接入点的鉴权 token 流程不明确
  - **应对**：直接读 xinnan-tech 的 `docs/mcp-endpoint-integration.md` + 跟测试页面对照
- **风险 2**：ESP32 的 `AddTool` 注册后 server 拿不到（注册时机晚于云端 tools/list 调用）
  - **应对**：在 ESP32 上 `Restart()` 一次，强制重新 hello

### 这一周做完 = 答辩里 60% 的炫酷动作能演

---

## Week 3 ▸ M3 + 场景一：完整 channel + cron 自动化

> 📝 **2026-06-19 修订** per [ADR-0005](adr/0005-openai-compat-transcript-egress.md) + [Week 0 retro §6](retros/week0.md)：
> - 3.1 / 3.4 (Discord callback / 上行音频独立路径) 已**作废**——transcript egress 走 M2 webhook,
>   H020 实测真 Hermes 已自动 spawn session 收到 user transcript
> - 3.2 / 3.3 拆成 H028 (Stage A plugin 骨架) + H028.bis (装+hermes run) + H029 (M1 proxy 真 send)
> - M3 工作量原估 5-6 天 → **实际 1-2 天**（H028 spike ~半天 + H028.bis 半天 + H029 1 天）

### 任务清单

| # | 任务 | 估时 | 验收 |
|---|------|------|------|
| ~~3.1~~ | ~~spike Discord plugin / 理解 voice callback~~ | — | OBSOLETE per [ADR-0004](adr/0004-voice-input-callback-discord-only-confirmed.md) |
| 3.2 (H028) | 写 `hermes-xiaozhi-plugin/` 包骨架 + XiaozhiAdapter + register(ctx) + 3 mock 测 | 半天 | pytest 3/3 PASS, sandbox-friendly |
| 3.2b (H028.bis) | ln -s 到 `~/.hermes/plugins/xiaozhi/`, `hermes gateway run` 看 "Platform 'xiaozhi' registered" + 切 shim env 指 plugin webhook | 半天 | hermes 日志见 plugin 注册成功 + ESP32 voice 真 spawn session 显示 "[xiaozhi] 用户: ..." |
| 3.3 (H029) | M1 加 `show_text_proxy(device_id, text, kind)` stdio tool + adapter.send 调它 | 1 天 | TUI 输 `send xiaozhi:ac:a7:04:30:91:78 "嗨"` → 机器人屏幕弹"嗨" |
| ~~3.4~~ | ~~上行音频独立路径~~ | — | OBSOLETE (transcript 已经走 M2 webhook，H020 done) |
| 3.5 | cron job：早安播报 (每天 9 点 deliver=xiaozhi) | 1 天 | 9 点机器人屏幕弹 "早，今天有 N 个 PR 等 review" |
| 3.6 | Telegram channel + cross-channel routing | 1 天 | Telegram 发消息 → 机器人屏幕显示 "[Telegram] Alice: ..." |

### 验收 demo（场景一全流程）

> 1. 早上 9 点（手动 trigger cron），机器人转头："早，今天有 2 个 PR 等 review"  
> 2. 你说："念第一个"，机器人念  
> 3. 朋友发 Telegram，机器人转头："Alice 找你"  
> 4. 你说："回她：晚上吃面"，机器人确认 + Telegram 真的发出去

### 风险 & 降级

> ⚠️ OBSOLETE since 2026-06-18 — see [ADR-0004](adr/0004-voice-input-callback-discord-only-confirmed.md). M3 直接走通用 MessageEvent(VOICE) path；Day 16 hard-stop 已关闭。

- **🔥🔥 风险 1 (本项目最大)**：`_voice_input_callback` 是 Discord-specific，需要改 Hermes 核心代码
  - **应对**：3.1 这天就要确认；如果是 Discord-specific，**走以下降级方案**：
  - **降级方案 A**：fork Hermes，提一个 PR 把 callback 通用化（如果 NousResearch 响应快，最干净）
  - **降级方案 B**：不让 xiaozhi 做"音频上行 channel"，而是让用户语音输入仍走 xinnan-tech → openai-shim 路径，xiaozhi channel 只作为**输出** channel（接收 `send_message_tool` 推送）。这样**场景一/二仍能演**，只是场景一里"我对机器人说"和"机器人主动说"用的不是 Hermes 的 channel 抽象，故事弱一点
- **风险 2**：跨 channel routing 在 Hermes 里实现成本超预期
  - **应对**：用 `send_message_tool` 而非自己造 routing，能少写一半代码

### 这一周做完 = 场景一可以完整演

---

## Week 4 ▸ 场景二 + Demo 打磨 + 报告

### 任务清单

| # | 任务 | 估时 | 验收 |
|---|------|------|------|
| 4.1 | ESP32 加 `xiaozhi.listen_ambient(seconds)` 工具（+ 红色 LED 指示） | 1 天 | 调用时机器人录 10 秒环境音上传 |
| 4.2 | ESP32 加 `xiaozhi.show_qr(url)` 工具（用 ESP-IDF QR 库） | 1 天 | 屏幕显示二维码可扫 |
| 4.3 | 全程跑场景二脚本（手机 Telegram → Hermes → 机器人发声） | 1 天 | 4 段演示从头到尾走通 |
| 4.4 | Fallback 方案：网络断了 / ASR 慢 怎么办？录视频备份 | 1 天 | 准备好 5 段录屏作为答辩 fallback |
| 4.5 | 写课程报告：项目背景、架构、协议、关键模块、Demo、隐私讨论、未来工作 | 2-3 天 | 报告 PDF 完稿 |
| 4.6 | 答辩演练（≥3 次完整跑） | 1 天 | 自己计时，控制在 4 分 ±15 秒 |

### 验收 demo（最终）

> 见 [demo-script.md](demo-script.md) 完整脚本

### 风险 & 降级

- **🔥 风险 1**：答辩现场 wifi 不行
  - **应对**：手机开热点 + ESP32 改配为热点 SSID + 提前演练切换
- **🔥 风险 2**：Telegram 国内访问问题
  - **应对**：用国内可用的 channel（飞书 / 钉钉 plugin），或者用 Hermes 的 webhook channel 自建消息源
- **风险 3**：现场延迟比家里高（演示翻车）
  - **应对**：把演示用的 LLM 切到延迟最小的（DeepSeek API 国内延迟低）

### 这一周做完 = 项目准备好答辩

---

## 全程关键检查点

> ⚠️ OBSOLETE since 2026-06-18 — see [ADR-0004](adr/0004-voice-input-callback-discord-only-confirmed.md). M3 直接走通用 MessageEvent(VOICE) path；Day 16 hard-stop 已关闭。

| 检查点 | 时间 | 卡点 → 必须做的事 |
|--------|------|------|
| Week 0 末 | 第 7 天 | 链路不通 → 拍醒，全力查 ESP32 ↔ server 连接，不进 Week 1 |
| Week 1 末 | 第 14 天 | shim 不通 → 砍掉 streaming，先用 non-streaming 跑通，再回头优化 |
| Week 2 末 | 第 21 天 | MCP adapter 不通 → 砍掉 ESP32 端新工具，让 Hermes 只通过 `speak` 一个工具控制机器人 |
| **Week 3 第 2 天** | 第 16 天 | **_voice_input_callback Discord-specific 已确认** → 立刻执行降级方案 B，不要硬撑 |
| Week 4 中 | 第 25 天 | 演示翻车 → 立刻锁定脚本，剩下时间只打磨已经跑通的部分，不加新功能 |

---

## 时间预算（带缓冲）

```
Week 0:  5-7 天     (核心 5 天，缓冲 2 天)
Week 1:  5-6 天     (核心 4 天，缓冲 2 天)
Week 2:  5-7 天     (核心 5 天，缓冲 2 天)
Week 3:  6-9 天     (核心 6 天，缓冲 3 天 ← 风险最大周次)
Week 4:  5-7 天     (核心 5 天，缓冲 2 天)
─────────────────
合计:   26-36 天    (3.5-5 周)
```

> ⚠️ 注意：估时按"每天专注 4-5 小时"算。如果是兼顾别的课，按 1.5 倍延长。

---

## 一旦超时怎么砍

按这个**优先级砍**（从下往上保留）：

1. ❌ 第一砍：Telegram 跨 channel routing（场景一第 3 段）
2. ❌ 第二砍：`listen_ambient` + 屏幕字幕显示（场景二第 4-5 段）
3. ❌ 第三砍：cron 早安播报（场景一第 1 段）
4. ❌ 第四砍：Hermes xiaozhi channel 的上行音频（M3 大半，只保留 send 输出）
5. ✅ 守住：M0 + M1 + M2 + M4 + 至少 2 个 MCP 工具能用 + 一段能演的对话

> **底线 demo**：你说话 → Hermes 决定调机器人的某个工具（如 `show_emoji + speak`）→ 机器人响应。这一条 4 周内 100% 能做出来。
