# 选型调研笔记

> 本文档记录关键技术选型背后的对比与决策依据，**可直接作为课程报告的"相关工作"章节素材**。  
> 调研时间：2026-06-16

---

## 1. xiaozhi-esp32 后端 server 选型

### 1.1 背景

上游 [78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) ESP32 端用 WebSocket 或 MQTT+UDP 跟一个"服务端"通信。**78 本人没有提供完整的开源对话 server**，仅提供：

- 协议文档（`docs/websocket.md`, `docs/mqtt-udp.md`, `docs/mcp-protocol.md`）
- 一个 MQTT/UDP 边缘网关（`78/xiaozhi-mqtt-gateway`，承担 transport 转发）
- 一个已归档不再维护的 legacy server（`78/xiaozhi`，README 明确标注"请使用社区方案"）

因此社区出现了 4 个被上游官方推荐的开源 server 实现。

### 1.2 协议关键事实

ESP32 端的消息类型：
```
hello | listen | stt | llm | tts | mcp | system | alert | custom
```

**MCP 走 WebSocket 隧道**：
```json
{"session_id": "...", "type": "mcp", "payload": {/* JSON-RPC 2.0 */}}
```
ESP32 端是 **MCP server**（暴露设备工具），云端是 **MCP client**。

参考：
- `esp/xiaozhi-esp32/docs/websocket.md`
- `esp/xiaozhi-esp32/docs/mcp-protocol.md` 第 5 行：「MCP is used between the backend API (MCP client) and the ESP32 device (MCP server)」

### 1.3 候选对比

| | xinnan-tech | joey-zhou (Java) | AnimeAIChat (Go) | hackers365 (Go) | 78/mqtt-gateway | 78/xiaozhi (legacy) |
|---|---|---|---|---|---|---|
| **Stars** | **9.8k** | 1.3k | 448 | 346 | 117 | 767 |
| **最新版本** | v0.9.4 (2026-06) | v5.1.0 (2026-04) | v0.1.3 (2026-06) | v0.6.3 (2026-05) | none | 已废弃 |
| **维护状态** | 活跃 | 活跃 | 活跃 | 活跃 | 低 | **停止维护** |
| **语言** | Python + Java + Vue | Java (Spring) | Go | Go (Eino) | Node.js | JS+Py |
| **WebSocket** | ✅ | ✅ | ✅ | ✅ | (作为 client) | — |
| **MQTT+UDP** | ✅ | ✅ | ❌ 社区版 | ✅ | ✅ 核心功能 | — |
| **MCP 设备侧** | ✅ | ✅ | ✅ | ✅ | 透传 | — |
| **MCP接入点（外部 → server）** | ✅ **有文档** | ❌ 未文档化 | ❌ | "MCP Market" | n/a | — |
| **OTA** | ✅ | ✅ | ✅ | ✅ | n/a | — |
| **Vision** | ✅ 多 VLM | ❌ | ✅ | ✅ | n/a | — |
| **LLM 可换** | OpenAI(+base_url)/Ollama/Gemini/Doubao/DeepSeek/GLM/Spark/Dify/Coze/HomeAssistant | OpenAI/GLM/Ollama/Dify/Coze | OpenAI/Ollama (Coze) | OpenAI-compat/Ollama/Eino | n/a | — |
| **Docker** | ✅ | ✅ (含 db) | ✅ | ✅ (含 AIO) | ❌ PM2 | — |
| **外部依赖** | 可选 MySQL+Redis | **必须** MySQL+Redis | SQLite | 可选 | 无 | — |
| **扩展点** | Python plugin SPI + MCP接入点 + base_url | Function Call + MCP 工具协议 | 无文档化 plugin | 可插拔模块 + MCP Market | per-MAC 路由 | — |
| **文档** | 中文为主，部分 EN/VI/DE/PT | 仅中文 | 仅中文 | 中文为主 | 中文 | 中文 |
| **License** | MIT | MIT | 自定义"基于 Apache 2.0" | MIT | MIT | MIT |
| **最大坑** | 全栈最重（Python+Java+Vue），但 minimal 模式可砍 | 必装 MySQL+Redis，无 vision | 社区版无 MQTT/UDP | 社区最小，无 plugin API | 仅 gateway，需 downstream | 已废弃 |

### 1.4 选定 xinnan-tech 的理由

1. **唯一一个有两个 extension seam 都符合需求**：
   - `LLM provider base_url` 可替换 → 解决"对话流转给 Hermes"
   - `MCP接入点` → 解决"Hermes 工具反向注入"
2. **唯一一个同时支持 WebSocket + MQTT + Vision + 最广 ASR/TTS 选择**
3. **上游 78 在自己 README 里第一个推荐的项目**
4. **9.8k stars，社区最活跃**
5. **minimal Docker 模式**可绕开 MySQL/Redis/Java

### 1.5 核心源码引用

- 验证 base_url 可替换：[xinnan-tech/main/xiaozhi-server/core/providers/llm/openai/openai.py](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/main/xiaozhi-server/core/providers/llm/openai/openai.py)
  ```python
  # config.LLM.<name>.url 被直接传给 openai.OpenAI(base_url=...)
  ```
- 验证 MCP 接入点：[docs/mcp-endpoint-integration.md](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/mcp-endpoint-integration.md)
  - 形如 `ws://host:8004/mcp_endpoint/mcp/?token=<jwt>`
- 模仿对象：[78/mcp-calculator/mcp_pipe.py](https://github.com/78/mcp-calculator) —— 官方提供的 sample MCP tool process，是写 xiaozhi-mcp-adapter 的直接模板

---

## 2. Agent runtime 选型

### 2.1 候选

| | Claude Code | openclaw | Hermes Agent |
|---|---|---|---|
| 类型 | 编程 agent CLI | 多 channel 个人助手 | 多 channel 个人助手 + 研究框架 |
| 仓库 | anthropics（闭源） | openclaw/openclaw | NousResearch/hermes-agent |
| 语言 | 闭源 binary | TypeScript/Node | Python 82% + TS 13% |
| License | 商业 | MIT | MIT |
| Channel 数 | 1（终端）| 20+ | 13+ |
| 真终端 TUI | ✅✅ | 配套 | ✅✅ |
| MCP 客户端 | ✅ | ❓ 未明确 | ✅✅ (stdio/HTTP) |
| LLM 后端 | 仅 Claude | 任意 | OpenRouter/OpenAI/Anthropic/Ollama/Nous/Kimi/GLM/MiniMax/HF |
| Sub-agent | ✅ | ✅ | ✅ |
| Skills/memory | 中 | ClawHub | ✅✅ self-improving + FTS5 |
| Cron | 项目级有 | ✅ | ✅ 完整 |
| 部署灵活 | 本地 | 多种 | local/Docker/SSH/Singularity/Modal/Daytona |
| 研究背景 | Anthropic 产品 | 个人项目 | **NousResearch 出品** |

### 2.2 选定 Hermes Agent 的理由

**功能匹配度**：
- 原生 MCP client（cli-config.yaml 配置即可挂载多个 MCP server）
- channel 抽象成熟，**Discord plugin 提供了完整的 voice channel 参考实现**（这点至关重要，详见 §3）
- LLM 后端无关，演示时可现场切换证明"Hermes 是大脑、xiaozhi 是身体，二者解耦"

**研究 / 答辩价值**：
- NousResearch 是知名开源 AI 实验室（Hermes 系列模型作者，开源 LLM 圈头部团队），引用其项目给项目报告加分
- "self-improving skills + Honcho dialectic user modeling" 是写论文友好的关键词
- 项目可作为 PR 提交回 NousResearch 社区，**这层"开源贡献"叙事是 Claude Code 给不了的**

**与 xiaozhi-server 接口完美对齐**：
- xinnan-tech 的 `base_url` ↔ Hermes 可暴露的 OpenAI-compat 接口
- xinnan-tech 的 `MCP接入点` ↔ Hermes `mcp_servers:` 配置
- 两边都讲标准协议，**胶水代码量最小**

### 2.3 Claude Code 被排除原因

- 闭源 binary，无法"嵌入"为某个 daemon
- 单 channel（终端），跟"多 channel 个人助手"的项目叙事相悖
- 绑定 Claude 模型，演示"后端可替换"做不出来
- 唯一接入方式是 subprocess `claude -p`，session 持续性靠 `--resume`，不够干净

### 2.4 openclaw 被排除原因

- README 信息有限，MCP 支持不确定
- TypeScript/Node 栈与 xiaozhi-server Python 栈不同语种，胶水成本上升
- channel 数量虽多但**没有 voice channel 先例**（Hermes 的 Discord voice 是现成模板）

---

## 3. Hermes Agent channel 扩展机制详查

### 3.1 关键发现

- **两条路径**：built-in (`gateway/platforms/`) vs plugin (`plugins/platforms/`)。后者是**官方推荐的第三方扩展路径**（Discord 已从 built-in 迁出，证明这条路是稳的）
- **必须实现的 ABC** (`gateway/platforms/base.py::BasePlatformAdapter`)：
  - `connect()`, `disconnect()`, `send()` 三个 abstract
  - `send_typing()`, `get_chat_info()`, `__init__(config)` 非 abstract 但必填
- **MessageEvent 结构标准化**：所有 channel 上行消息走 `self.handle_message(MessageEvent(...))`，消息字段 `chat_id / user_id / message_type (TEXT/PHOTO/VOICE/...) / text / attachments / thread_id`

### 3.2 Discord 是 voice channel 的参考实现

`plugins/platforms/discord/adapter.py` 里的 `VoiceReceiver`：

- 钩住 voice WebSocket，SSRC → user 映射
- 解密 `aead_xchacha20_poly1305_rtpsize`（可选 DAVE E2EE）
- 解码 Opus → PCM per SSRC
- 按 1.5s 静音 flush
- PCM → 16kHz mono WAV via ffmpeg（Whisper-ready）
- 通过 `_voice_input_callback` 上报到 `gateway/run.py`

**这是我们写 xiaozhi voice channel 的直接模板。**

输出侧 `plugins/platforms/discord/voice_mixer.py` 提供 numpy-based PCM 混音器，含"thinking" 背景音 + TTS 层叠 + ducking。注释明示：「The mixer NEVER touches the inbound receive path」—— 这种**输入/输出严格分离**的设计正好契合 xiaozhi 的双向数据流模型。

### 3.3 ⚠️ 关键风险

**`_voice_input_callback` 可能是 Discord-specific 的钩子，不是 generic 接口。**

如果是后者，要写 voice channel 必须 fork 改 `gateway/run.py`，从"plugin 路径"掉到"built-in 16 步路径"。

**Week 0/3 必须先做的事**：spike Hermes 源码，确认这个 callback 是不是通用的。决定 M3 工作量是 **3-4 天**（乐观）/ **8-12 天**（现实）/ **18-25 天**（悲观）。

### 3.4 MCP 集成方式

- 配置在 `cli-config.yaml`：
  ```yaml
  mcp_servers:
    xiaozhi:
      command: python
      args: ["-m", "xiaozhi_mcp_adapter"]
      env: {...}
  ```
- 支持 **stdio** 和 **HTTP**，无 SSE/WebSocket
- 每个 server 可单独配 sampling 限流

→ M1 (`xiaozhi-mcp-adapter`) 必须是 stdio 形态，否则 Hermes 不识别。

### 3.5 跨 channel 协作机制

**Hermes 不支持跨 channel session sharing**（`session_key = agent:main:<platform>:<chat_type>:<chat_id>`）。

跨 channel 投递走两条路：
1. **`send_message_tool`**：agent 在 session A 主动给 channel B 推消息
2. **`cron` 的 `deliver` 字段**：定时任务指定投递目标

我们的 demo 场景二（"我手机 Telegram → 机器人发声"）走的就是 `send_message_tool` 路径。**这不是缺陷，反而是干净的设计**：消息投递和会话状态分离，每个 channel 维护自己的上下文。

---

## 4. 协议层认知矩阵（避免常见混淆）

| 概念 | 谁是 server | 谁是 client | 传输 |
|------|-----------|------------|------|
| **xiaozhi 主协议** | xiaozhi-esp32-server | ESP32 firmware | WebSocket / MQTT |
| **xiaozhi MCP（设备工具）** | ESP32 firmware 内置 | xiaozhi-server 云端 | 嵌在主协议 WS 里 |
| **xiaozhi MCP接入点** | xiaozhi-server | 我们的 xiaozhi-mcp-adapter | WebSocket，独立 endpoint :8004 |
| **Hermes MCP 消费** | xiaozhi-mcp-adapter | Hermes Agent | stdio |
| **Hermes openai-shim** | openai-shim (我们写) | xinnan-tech LLM provider | HTTP /v1/chat/completions |
| **Hermes channel inbound** | n/a (callback pattern) | n/a | adapter.handle_message() |
| **Hermes channel outbound** | n/a | n/a | adapter.send() |

**最容易混淆**：xiaozhi 上的 MCP 是 **device-as-server**，Hermes 上的 MCP 是 **adapter-as-server**。两边角色相反，这是 M1 adapter 存在的根本原因。

---

## 5. 参考文献（报告"参考文献"章节可直接用）

### 项目仓库
- [78/xiaozhi-esp32 上游固件仓库](https://github.com/78/xiaozhi-esp32)
- [xinnan-tech/xiaozhi-esp32-server 开源 server](https://github.com/xinnan-tech/xiaozhi-esp32-server)
- [NousResearch/hermes-agent 多 channel agent runtime](https://github.com/NousResearch/hermes-agent)
- [78/mcp-calculator 官方 sample MCP tool](https://github.com/78/mcp-calculator)

### 协议规范
- [Model Context Protocol Spec (modelcontextprotocol.io)](https://modelcontextprotocol.io)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [Anthropic MCP 介绍](https://docs.anthropic.com/en/docs/agents-and-tools/mcp)

### 本地文档
- `esp/xiaozhi-esp32/docs/websocket.md` —— xiaozhi 主协议
- `esp/xiaozhi-esp32/docs/mcp-protocol.md` —— 设备端 MCP server 规范
- `esp/xiaozhi-esp32/docs/mqtt-udp.md` —— MQTT+UDP 备选传输
- `esp/xiaozhi-esp32/main/boards/esp-hi/esp_hi.cc` —— 板级 MCP 工具实现样例

### 工具链
- [ESP-IDF v5.5.2](https://github.com/espressif/esp-idf/tree/v5.5.2)
- [FastAPI](https://fastapi.tiangolo.com/) (M2 openai-shim)
- [FastMCP](https://github.com/jlowin/fastmcp) (M1 xiaozhi-mcp-adapter)
- [OpenAI Streaming Protocol](https://platform.openai.com/docs/api-reference/chat/streaming)

---

## 6. 待持续跟踪的开放问题

| # | 问题 | 影响 | 何时回答 |
|---|------|------|----------|
| 1 | `_voice_input_callback` 是否 Discord-specific | M3 工作量 +50% | Week 0 末 spike |
| 2 | xiaozhi MCP接入点 token 是 JWT 还是 plain | M1 鉴权代码 | Week 2 调通时 |
| 3 | xinnan-tech 的 LLM provider 在 streaming 模式下的 chunk 格式与官方 OpenAI 是否完全一致 | M2 实现 | Week 1 调通时 |
| 4 | Hermes session 注入是否有 public API（非 internal） | M2 集成方式 | Week 1 spike |
| 5 | ESP32 端 `listen_ambient` 的录音如何传到 Hermes（直接 HTTP upload 还是走 MCP tool result） | M4 接口设计 | Week 4 实现时 |
| 6 | 演示当天网络是否需要内网备用方案 | 答辩成败 | 答辩前 1 周确认 |
