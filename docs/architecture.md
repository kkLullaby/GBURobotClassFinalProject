# 架构设计

> 项目目标：把 ESP32 小智机器人变成 **Hermes Agent** 的一具"具身化身"（embodiment），让一个开源的、跑在用户电脑上的、多 channel 个人 AI 助手能够通过这具机器人**说话、做表情、感知环境**，同时也能**听用户的语音指令**。

---

## 1. 一句话定位

> **xiaozhi 是 Hermes Agent 在物理世界里的第一具身体。**

机器人不再是一个"独立的语音助手"，而是用户已有的个人 AI 助手平台（Hermes Agent）的一个 **plugin platform** —— 与 Telegram、Discord、Slack 并列，但唯一具备物理表达力。

---

## 2. 高保真架构图

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │                                                                      │
 │                          你的笔记本（Linux/macOS）                    │
 │                                                                      │
 │   ┌────────────────────────────────────────────────────────────┐     │
 │   │                                                            │     │
 │   │                    Hermes Agent (Python)                   │     │
 │   │                                                            │     │
 │   │   ┌──────────────────────────────────────────────────┐    │     │
 │   │   │            gateway / platform_registry           │    │     │
 │   │   │                                                  │    │     │
 │   │   │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │    │     │
 │   │   │  │  TUI     │ │ Telegram │ │ ⭐ xiaozhi (你写) │ │    │     │
 │   │   │  │ adapter  │ │ adapter  │ │  adapter          │ │    │     │
 │   │   │  │ (built-in│ │(built-in)│ │ (plugin path)     │ │    │     │
 │   │   │  └────┬─────┘ └────┬─────┘ └────────┬──────────┘ │    │     │
 │   │   │       │            │                │            │    │     │
 │   │   │       └────────────┴────────────────┘            │    │     │
 │   │   │                    │                              │    │     │
 │   │   │              MessageEvent                         │    │     │
 │   │   │                    ▼                              │    │     │
 │   │   │  ┌──────────────────────────────────────────┐    │    │     │
 │   │   │  │   agent runner / LLM loop                │    │    │     │
 │   │   │  │   (OpenAI / Anthropic / OpenRouter /     │    │    │     │
 │   │   │  │    Nous Portal / Ollama 等可替换)         │    │    │     │
 │   │   │  └────────────────┬─────────────────────────┘    │    │     │
 │   │   │                   │                              │    │     │
 │   │   │              tool calls                          │    │     │
 │   │   │                   ▼                              │    │     │
 │   │   │  ┌──────────────────────────────────────────┐    │    │     │
 │   │   │  │   MCP client (stdio / HTTP)              │    │    │     │
 │   │   │  └────────────────┬─────────────────────────┘    │    │     │
 │   │   └───────────────────┼──────────────────────────────┘    │     │
 │   │                       │                                   │     │
 │   │   ⭐ M3              │                                    │     │
 │   │   xiaozhi-channel     │ ⭐ M1                              │     │
 │   │   plugin              │ xiaozhi-mcp-adapter               │     │
 │   │   ┌──────────┐        │ ┌──────────────────┐              │     │
 │   │   │ Whisper  │        └▶│ Python MCP server│              │     │
 │   │   │ ASR/TTS  │          │ (FastMCP / stdio)│              │     │
 │   │   └────┬─────┘          └─────────┬────────┘              │     │
 │   │        │                          │                       │     │
 │   │        │                          │ WebSocket             │     │
 │   │        │                          │ (xiaozhi MCP接入点)   │     │
 │   │        │                          ▼                       │     │
 │   │        │              ┌─────────────────────────┐         │     │
 │   │        │              │                         │         │     │
 │   │        │              │ xinnan-tech/xiaozhi-    │         │     │
 │   │        │              │  esp32-server (Docker)  │         │     │
 │   │        │              │                         │         │     │
 │   │        │              │ ┌─────────────────────┐ │         │     │
 │   │        │              │ │ LLM provider:       │ │         │     │
 │   │        │              │ │   type: openai      │ │         │     │
 │   │        │              │ │   base_url: ──┐     │ │         │     │
 │   │        │              │ └───────────────┼─────┘ │         │     │
 │   │        │              │                 │       │         │     │
 │   │        │              │ ┌───────────────▼─────┐ │         │     │
 │   │        │              │ │ ASR  ──→  对话循环  │ │         │     │
 │   │        │              │ │             │       │ │         │     │
 │   │        │              │ │             ▼  TTS  │ │         │     │
 │   │        │              │ └───────────────┬─────┘ │         │     │
 │   │        │              └─────────────────┼───────┘         │     │
 │   │        │                                │                 │     │
 │   │        │                  ┌─────────────▼────────────┐   │     │
 │   │        │                  │ ⭐ M2  openai-shim       │   │     │
 │   │        │                  │   FastAPI 服务            │   │     │
 │   │        │                  │   /v1/chat/completions    │   │     │
 │   │        │                  │   → 转发给 Hermes session │   │     │
 │   │        └─────────────────▶│   (与左侧音频 channel    │   │     │
 │   │       Hermes 处理结果       │    汇聚到同一 inbox)     │   │     │
 │   │       回流到 shim          └───────────────────────────┘   │     │
 │   └────────────────────────────────────────────────────────────┘     │
 │                                       ▲                              │
 └───────────────────────────────────────┼──────────────────────────────┘
                                         │  WebSocket
                                         │  (xiaozhi 原生协议)
                                         │  Opus audio + JSON control
                                         │
              ┌──────────────────────────┴────────────────────────────┐
              │                                                       │
              │                 ESP32-S3 / OttoRobot                  │
              │                                                       │
              │   ┌──────────┐  ┌───────────┐  ┌────────────────┐    │
              │   │ Mic      │  │ Speaker   │  │ LCD 屏 + 舵机   │    │
              │   │ (上行)   │  │ (TTS 下行)│  │ + LED          │    │
              │   └──────────┘  └───────────┘  └────────────────┘    │
              │                                                       │
              │   ┌──────────────────────────────────────────────┐    │
              │   │   xiaozhi-esp32 firmware (上游 main)          │    │
              │   │   - Wi-Fi + WebSocket client                 │    │
              │   │   - Wake word + VAD                          │    │
              │   │   - 内置 MCP server (设备端工具)              │    │
              │   │     ⭐ 你扩展的工具：                          │    │
              │   │       speak / show_emoji / show_text /       │    │
              │   │       show_qr / gesture / listen_ambient     │    │
              │   └──────────────────────────────────────────────┘    │
              └───────────────────────────────────────────────────────┘
```

---

## 3. 关键概念区分

### MCP 在这个项目里有两个方向

这是最容易混淆的点。

| 方向 | 谁是 server | 谁是 client | 走哪条线 |
|------|-----------|------------|--------|
| **A. 设备工具暴露** | ESP32 上的 firmware | xiaozhi-esp32-server 云端 | 嵌在 xiaozhi 私有 WebSocket 里，外层 `{"type":"mcp", "payload": <JSON-RPC>}` |
| **B. Hermes 工具消费** | xiaozhi-mcp-adapter (我们写的) | Hermes Agent 的 MCP client | 标准 MCP（stdio 或 HTTP） |

**M1 (xiaozhi-mcp-adapter) 的核心职责就是把方向 A 翻译成方向 B**，让 Hermes 能像调任何标准 MCP server 一样调机器人的工具。

### Hermes session 是 per-channel 的

Hermes 的 session key 形如：`agent:main:<platform>:<chat_type>:<chat_id>`。Telegram 来的消息和 xiaozhi 来的消息属于**两个独立 session**，上下文不共享。

跨 channel 协作走两条路：
- **`send_message_tool`**：agent 在 session A 里主动给 channel B 推消息（不是回复）
- **cron 的 `deliver` 字段**：定时任务指定投递到哪个 channel

这意味着 demo 场景二的"我手机 Telegram 让机器人替我答辩"实现路径是：
```
你 → Telegram channel session
  → agent 调 send_message_tool(platform="xiaozhi", text="...")
    → xiaozhi adapter.send() → ESP32 speak()
```
不是"同一个对话从 Telegram 流向 xiaozhi"，而是"agent 主动跨 channel 投递消息"。这点在答辩里要讲清楚。

---

## 4. 组件清单（4 个要写的 + 1 个现成的）

| ID | 组件 | 形态 | 抄哪份 | 估时 | 关键风险 |
|----|------|------|--------|------|----------|
| **M0** | xinnan-tech/xiaozhi-esp32-server | 现成 Docker | n/a | 1 天调通 | 文档中文为主，minimal 模式跑通后省心 |
| **M1** | xiaozhi-mcp-adapter | Python service | [78/mcp-calculator/mcp_pipe.py](https://github.com/78/mcp-calculator) | 5-7 天 | xiaozhi MCP接入点的握手细节需要读源码 |
| **M2** | openai-shim | FastAPI 1-2 文件 | OpenAI SDK 文档 | 2-3 天 | streaming 的 SSE chunk 格式要严格对齐 |
| **M3** | Hermes xiaozhi channel plugin | Python plugin | [Hermes plugins/platforms/discord/](https://github.com/NousResearch/hermes-agent) | 8-12 天 (现实估) | `_voice_input_callback` 可能 Discord-specific（最大风险） |
| **M4** | ESP32 端新 MCP tools | C++ 改 `otto_robot.cc` | [esp-hi/esp_hi.cc](https://github.com/78/xiaozhi-esp32/blob/main/main/boards/esp-hi/esp_hi.cc) | 3-5 天 | 仅 add tool，零侵入 |

---

## 5. 数据流：典型对话的端到端时序

### 5.1 用户对机器人说话（场景一典型流）

```
T+0ms     用户说："把第一个 PR 念给我听"
T+50ms    ESP32 mic 检测到唤醒词 + VAD 触发
T+100ms   ESP32 → WS → xiaozhi-esp32-server: 开始上行 Opus audio frames
T+1500ms  用户说完，VAD 静音判定
T+1600ms  server 做 ASR → 得到文本 "把第一个 PR 念给我听"
T+1700ms  server 发起 LLM 调用 → POST openai-shim:/v1/chat/completions
T+1750ms  openai-shim 把请求转 Hermes：
            - 创建/复用 xiaozhi session
            - 注入为 MessageEvent
            - Hermes agent 接管推理
T+2000ms  Hermes agent 决定调用 MCP tool: gh.pr_list(state=open)
T+2200ms  agent 收到 PR 列表，决定再调 gh.pr_diff(number=58)
T+2500ms  agent 思考后生成回复："好，PR #58……"
T+2600ms  Hermes 把回复以 OpenAI streaming 格式返回 openai-shim
T+2650ms  openai-shim 把 SSE chunks 转给 xiaozhi-esp32-server
T+2700ms  server TTS 流式合成 → WebSocket 下行 Opus 给 ESP32
T+2800ms  机器人开始朗读
```

### 5.2 用户在终端打字，让机器人发声（场景二典型流）

```
用户 → Hermes TUI: "robot, 给评委做个自我介绍"
   │
   ├─→ TUI adapter → MessageEvent (platform=tui)
   │
   └─→ Hermes agent
         │
         ├─→ decide: 用户想要 xiaozhi 发声，不是 TUI 回复
         │
         ├─→ tool call: send_message_tool(
         │     platform="xiaozhi",
         │     chat_id=<XIAOZHI_HOME_CHANNEL>,
         │     text="大家好，我是 Otto……"
         │   )
         │
         └─→ xiaozhi adapter.send(chat_id, text)
               │
               └─→ Hermes 通过 xiaozhi-mcp-adapter
                   调用机器人 MCP tool: speak(text)
                     │
                     └─→ xiaozhi-esp32-server 收到 MCP 调用
                          │
                          └─→ WS → ESP32: 触发 TTS playback
```

---

## 6. 选型决策与理由

### 6.1 为什么是 xinnan-tech/xiaozhi-esp32-server？

✅ **9.8k stars, v0.9.4 (2026-06-03)** —— 生态最活跃，原作者 78 在 README 里官方推荐
✅ **同时支持 WebSocket + MQTT** —— 不被传输协议绑定
✅ **OpenAI-compatible `base_url`** —— 写一个 shim 就能换大脑
✅ **MCP接入点机制** —— 外部 MCP server 反向注入，是 Hermes 工具调用的天然入口
✅ **minimal Docker 模式** —— 不需要 MySQL/Redis/Java 那一堆基础设施

❌ 文档中文为主（对我们不是问题）

### 6.2 为什么不用其他 server？

- `78/xiaozhi`：**已停止维护**，README 明确写"请使用社区方案"
- `joey-zhou/...-java`：MySQL+Redis+Spring Boot，基础设施太重，无 vision
- `AnimeAIChat/...-go`：**社区版不带 MQTT/UDP**（需要付费版），license 不标准
- `hackers365/...-golang`：社区最小，无文档化 plugin API

### 6.3 为什么是 Hermes Agent 而不是 Claude Code / openclaw？

- **MCP 原生支持** —— `mcp_servers` 配置项可直接挂载，cli-config.yaml 即写即用
- **多 channel 体系成熟** —— 20+ 平台，Discord voice channel 是现成的具身参考实现
- **后端无关** —— 支持 OpenRouter/OpenAI/Anthropic/Ollama/Nous Portal 等，可在演示时切换证明解耦
- **MIT License** —— 课程项目无授权风险
- **研究背景** —— NousResearch 是知名开源 AI 实验室，引用其项目给报告加分

替代选项被排除的原因：
- **Claude Code**：闭源，subprocess 调用只能 `claude -p`，不支持把它"嵌入"为某个 daemon
- **openclaw**：Node.js/TypeScript 栈，MCP 支持不明确，channel 数量比 Hermes 少
- **OpenHands**：偏软件工程 agent，对个人助手 + 多 channel 不是核心场景

### 6.4 为什么不直接让 ESP32 调 Hermes，绕开 xiaozhi-server？

**因为 ESP32 firmware 是上游 78/xiaozhi-esp32 的，里面写死了它要连一个 xiaozhi 协议的服务端**（包括 hello/listen/stt/llm/tts 的状态机、Opus 音频帧、唤醒词上报等）。重写这套协议等于 fork 整个固件，违背"不动硬件层"的原则（用户已声明）。

让 xiaozhi-server 作为协议适配层（处理音频、状态机、TTS），让 Hermes 只关心"文本对话 + 工具调用"，是最干净的关注点分离。

---

## 7. 模块边界与接口

### 7.1 xiaozhi-mcp-adapter (M1)

**职责**：把设备端 MCP 工具暴露给 Hermes。

```
                    ┌────────────────────────────┐
   stdio MCP        │                            │       xiaozhi MCP
   (Hermes 这边) ──▶│   xiaozhi-mcp-adapter      │──── 接入点 WS ────▶
   tools/list       │                            │      ws://xiaozhi-server
   tools/call       │  - 维持长连 WS              │      :8004/mcp_endpoint
                    │  - JSON-RPC 双向转发        │      /mcp/?token=xxx
   ◀──── 结果 ──────│  - 工具名加 "xiaozhi." 前缀 │
                    │    避免与其他 MCP server 冲突│
                    └────────────────────────────┘
```

**关键 API（你要实现的）**：
```python
# 入站：处理 Hermes 的 MCP 请求
async def handle_mcp_request(msg: dict) -> dict: ...

# 出站：转发给 xiaozhi server 的 WS endpoint
async def forward_to_xiaozhi(msg: dict) -> dict: ...

# 启动：作为 stdio MCP server 注册到 Hermes
if __name__ == "__main__":
    asyncio.run(stdio_server.run(handle_mcp_request))
```

**配置在 Hermes 的 cli-config.yaml**：
```yaml
mcp_servers:
  xiaozhi:
    command: python
    args: ["-m", "xiaozhi_mcp_adapter"]
    env:
      XIAOZHI_ENDPOINT_URL: "ws://localhost:8004/mcp_endpoint/mcp/"
      XIAOZHI_ENDPOINT_TOKEN: "${XIAOZHI_TOKEN}"
```

### 7.2 openai-shim (M2)

**职责**：让 xiaozhi-server 以为它在调一个 OpenAI 兼容服务，实际请求转给 Hermes session。

```python
# 极简版伪代码
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import httpx

app = FastAPI()

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    # 1. 从 req 里取出最新一句用户输入
    user_text = req.messages[-1].content
    
    # 2. 把它当作消息推给 Hermes 的 xiaozhi channel
    #    用 Hermes 暴露的 events_wait 或 messages_send 接口
    response_stream = hermes.send_to_session(
        platform="xiaozhi",
        chat_id=req.user,  # 用 ESP32 设备 ID 作为 chat_id
        text=user_text,
    )
    
    # 3. 把 Hermes 的回复流转成 OpenAI SSE 格式
    async def relay():
        async for chunk in response_stream:
            yield f"data: {json.dumps(openai_chunk(chunk))}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(relay(), media_type="text/event-stream")
```

**在 xinnan-tech 配置**（`data/.config.yaml`）：
```yaml
LLM:
  ChatGLMLLM:
    type: openai
    model_name: "hermes-bridge"
    url: "http://localhost:8765/v1"   # ← openai-shim
    api_key: "any-string-works"
```

### 7.3 Hermes xiaozhi channel (M3)

**职责**：让 Hermes 把"机器人的语音输入"当成一个标准 channel 消息。

参考 `plugins/platforms/discord/adapter.py` 的结构。

**plugin.yaml 骨架**：
```yaml
name: xiaozhi
platform: xiaozhi
adapter_class: XiaozhiAdapter
register_fn: register
requires_env: [XIAOZHI_HOME_CHANNEL]
home_channel_env: XIAOZHI_HOME_CHANNEL
cron_deliver_env_var: XIAOZHI_HOME_CHANNEL
```

**adapter.py 必须实现**（来自 `gateway/platforms/base.py` 的 ABC）：
```python
class XiaozhiAdapter(BasePlatformAdapter):
    async def connect(self) -> bool: ...
    async def disconnect(self) -> None: ...
    async def send(self, chat_id, content, ...) -> SendResult:
        # 通过 MCP 调机器人的 speak() 工具
        ...
    async def send_typing(self, chat_id): 
        # 让机器人显示"思考中"表情
        ...
    async def get_chat_info(self, chat_id) -> dict: ...
```

**上行音频处理**：模仿 Discord 的 `VoiceReceiver`，把 ESP32 上行的 Opus → PCM → WAV，调 Whisper ASR → 文本 → `self.handle_message(MessageEvent(...))`。

**关键问题待 spike 验证**：`gateway/run.py` 里的 `_voice_input_callback` 是不是 generic 的，还是 Discord-specific 的？决定这一块工作量从 8 天还是 18 天。

### 7.4 ESP32 端新 MCP tools (M4)

**职责**：扩展机器人侧的工具集，让 Hermes 能调用。

在 `main/boards/otto-robot/otto_robot.cc` 的 `InitializeTools()` 里 `AddTool(...)`。参考 `main/boards/esp-hi/esp_hi.cc` (302-390 行)。

| 工具名 | 签名 | 实现要点 |
|--------|------|---------|
| `xiaozhi.speak` | `(text: string)` | 直接调 server-side TTS 链路，等同于用户语音输入触发的 TTS 回流 |
| `xiaozhi.show_emoji` | `(name: string)` | 切 LCD 表情，复用 OttoEmojiDisplay 现有动画 |
| `xiaozhi.show_text` | `(text: string, duration_ms: int)` | LCD 大字幕 |
| `xiaozhi.show_qr` | `(url: string)` | 生成 QR 码并铺满屏 |
| `xiaozhi.gesture` | `(name: enum)` | 调 OttoMovements 预设动作：`wave / nod / shake / dance` |
| `xiaozhi.listen_ambient` | `(seconds: int)` | 录环境音上传，⚠️ **必须显示红色 listening 指示灯** |
| `xiaozhi.set_led` | `(color: rgb, mode: enum)` | 状态指示 |

---

## 8. 安全 / 隐私边界（必写）

- **`listen_ambient` 工具**：调用时机器人**必须**亮红色 LED + 短促 beep，工具响应里也必须 echo 一个 `"recording_consent": true` 字段进 metadata
- **Hermes 系统 prompt** 里必须包含规则："禁止在没有用户授权的前提下连续调用 `listen_ambient`"
- **API key 管理**：所有 LLM provider key 走环境变量，不进代码、不进 sdkconfig
- **MCP 工具权限分级**：参考 xiaozhi 现成的 `AddTool` vs `AddUserOnlyTool`（后者只允许用户直接触发，AI 调不到）
- 演示场景二涉及"代念发言"时，应在屏幕上同步显示字幕，让现场所有人都能看到机器人在说什么 —— 避免"AI 假装是人"的伦理边界

---

## 9. 演进路径

- **v0.1**：Hermes 仅作为 LLM 后端，单向（用户说话 → 机器人回复）
- **v0.2**：加入设备 MCP 工具，Hermes 可以让机器人做表情/动作
- **v0.3**：加入 xiaozhi channel plugin，跨 channel 投递（场景二）
- **v0.4**：cron + ambient awareness（早安播报、状态推送）
- **v1.0**：完整 demo + 文档 + 可作为 Hermes 社区 PR 提交

