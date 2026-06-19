---
status: current
version: v1
created: 2026-06-19
author: planner
upstream_pin:
  esp/xiaozhi-esp32: b392c630aa74bc9bb0ff5791bb89b1d8c96b3181   # 2026-06-16
  xinnan-tech/xiaozhi-esp32-server: a1973e07b71e018199018060497c58cd45d5d387  # 2026-06-18
source_files:
  - esp/xiaozhi-esp32/main/protocols/websocket_protocol.cc (L60-260)
  - esp/xiaozhi-esp32/main/application.cc (L520-610)
  - xinnan-tech: main/xiaozhi-server/core/connection.py (整个文件)
---

# Contract: ESP32 ↔ xinnan-tech server WebSocket handshake (v1)

> 这是**上游协议**的 fact 记录，**不是**本项目设计。本项目 M1-M4 必须遵守。
> 改这份 = 必须证明上游真改了，不是猜。

> ⚠️ 范围：仅 baseline `WebsocketProtocol`（**不**含 `MqttProtocol`，本项目
> 不走 MQTT 路径）。

---

## 1. 连接级元数据

### 1.1 Endpoint

ESP32 拨号到 server 的 URL：

```
ws://<server-host>:8000/xiaozhi/v1/?<query-string>
```

| 项 | 值 | 来源 |
|---|---|---|
| 默认 host | `xiaozhi.me` (上游 baseline) | `Kconfig.projbuild:3` `CONFIG_OTA_URL` 反推 |
| 端口 | **8000** (xinnan-tech minimal docker 已确认 LISTEN) | H011 What I Did |
| Path | `/xiaozhi/v1/` (注意末尾 slash) | xinnan-tech server `ws://172.19.0.2:8000/xiaozhi/v1/` 实测 |
| Scheme | `ws://`（本项目不走 wss；ESP32 出局明文，server 同主机） | H011 verify |

> ⚠️ **URL 来源不是直接配置**：ESP32 baseline 启动时去 `CONFIG_OTA_URL`
> 拉 OTA 响应，从其 `websocket.url` 字段拿 WS endpoint，写进 NVS
> `Settings("websocket", true)`。后续连接读 NVS。**首次烧录前没法不重烧切 URL**
> （详见 [diagnoses/2026-06-19-esp32-baseline-server-url-switch.md](../../../diagnoses/2026-06-19-esp32-baseline-server-url-switch.md)）。

### 1.2 HTTP Headers（ESP32 → server）

`websocket_protocol.cc:97-110`：

| Header | Value | 必需？ |
|---|---|---|
| `Authorization` | `Bearer <token>` 或 `<token>` 自带前缀 | 仅当 `wifi/token` NVS 非空；xinnan-tech minimal 默认不验 token |
| `Protocol-Version` | `1` / `2` / `3` (整数字符串)，本项目 baseline 是 `1` | **是** |
| `Device-Id` | ESP32 MAC 地址（小写，冒号分隔） | **是** |
| `Client-Id` | Board UUID (per-板子型号生成) | **是** |

xinnan-tech server 读这些 header 决定 session 路由和复用。

### 1.3 二进制帧：Opus audio

双向都用 binary WS frame 跑 audio。三种格式按 `Protocol-Version`：

- **v1**：raw Opus payload（无 header）
- **v2**：`BinaryProtocol2` (network-byte-order header + payload)
- **v3**：`BinaryProtocol3` (短 header)

ESP32 baseline 用 v1 时 server 也按 v1 处理；本 contract 锁 v1。

### 1.4 文本帧：JSON

所有控制消息都是 UTF-8 JSON，**根字段固定有 `"type": "<string>"`**。
未识别 `type` server 不报错，ESP32 端 `ESP_LOGW` 后丢弃
(`application.cc:608` `Unknown message type: %s`)。

---

## 2. Hello 握手（强制，连接后第一个消息）

### 2.1 ESP32 → server：`type:"hello"`

`websocket_protocol.cc:GetHelloMessage()` L203-227：

```json
{
  "type": "hello",
  "version": 1,
  "features": {
    "mcp": true,
    "aec": false   // 仅当 CONFIG_USE_SERVER_AEC，OttoRobot baseline 不开
  },
  "transport": "websocket",
  "audio_params": {
    "format": "opus",
    "sample_rate": 16000,
    "channels": 1,
    "frame_duration": 60      // OPUS_FRAME_DURATION_MS，常量
  }
}
```

字段说明：

| 字段 | 强制 | 用途 |
|---|---|---|
| `type` | **是** | 永远 `"hello"` |
| `version` | **是** | 必须等于 `Protocol-Version` header |
| `features.mcp` | **是**（baseline true） | ESP32 声明支持 MCP 子帧 |
| `features.aec` | 否 | 编译时决定；为 true 表示由 server 做声学回声消除 |
| `transport` | **是** | 永远 `"websocket"` |
| `audio_params` | **是** | 上行 audio 的格式声明 |

### 2.2 server → ESP32：`type:"hello"`（回应）

`websocket_protocol.cc:ParseServerHello()` L230-263 期望：

```json
{
  "type": "hello",
  "transport": "websocket",        // 必须 == "websocket"，否则 ESP_LOGE 拒绝
  "session_id": "<server-gen>",
  "audio_params": {
    "sample_rate": <int>,          // server 下行 audio 用的采样率
    "frame_duration": <int>        // server 下行 audio frame 时长 (ms)
  }
}
```

**收到这条 = audio channel opened**，触发 `on_audio_channel_opened_` callback。
ESP32 在收到前等待 `WEBSOCKET_PROTOCOL_SERVER_HELLO_EVENT`（含 timeout）。

---

## 3. server → ESP32 JSON 控制帧（全集）

按 `application.cc:520-610` 的 `OnIncomingJson` dispatch 表，server 可发：

| `type` | 子字段 | ESP32 行为 |
|---|---|---|
| `tts` | `state: "start"/"stop"/"sentence_start"`, `text?` | 切 device state 到 Speaking/Listening；`sentence_start` 时 `text` 投给 display |
| `stt` | `text: <string>` | display 显示用户说的话（debug 用，audio 已经在 binary 流里） |
| `llm` | `emotion: <string>` | display 切换表情 |
| `mcp` | `payload: {<JSON-RPC>}` | 转给 `McpServer::ParseMessage(payload)` — **本项目 M4 入口** |
| `system` | `command: "reboot"` | ESP32 调 `Reboot()` |
| `alert` | `status`, `message`, `emotion` | display + 声音报警 |
| `custom` | `payload: <obj>` | （仅 `CONFIG_RECEIVE_CUSTOM_MESSAGE` 时）display "system" 消息 |
| `goodbye` | — | （MQTT path 有；WS path 未发现入口） |

未列出的 `type` → ESP32 `ESP_LOGW("Unknown message type")` 后丢，**不报错**。

---

## 4. MCP 子帧（**本项目 M1 / M4 关键**）

### 4.1 帧结构

```json
{
  "type": "mcp",
  "payload": <JSON-RPC 2.0 object>
}
```

`payload` 完整遵守 MCP（Model Context Protocol）over JSON-RPC 2.0。
ESP32 端进 `McpServer::ParseMessage(payload)`。

### 4.2 ESP32 作为 MCP server，server 作为 MCP client

ESP32 上 `AddTool()` 注册的工具 → 通过 `tools/list` 暴露 → server 的
LLM thinking 阶段调 `tools/call` → ESP32 执行后返回 result。

**M4 直接在 `main/boards/otto-robot/otto_robot.cc` 里 `AddTool(...)` 即可**；
模板看 `esp/xiaozhi-esp32/main/boards/esp-hi/esp_hi.cc:302-390`。

### 4.2.bis Server 在 hello 之后**自动发** MCP `initialize`（实测发现）

H1b A-bis wscat 实测 (2026-06-19)：server 发完 `type:"hello"` 之后**立刻**
主动发一个 `type:"mcp"` 子帧，payload 是 JSON-RPC `initialize` 请求：

```json
{
  "type": "mcp",
  "payload": {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {
        "roots": {"listChanged": true},
        "sampling": {},
        "vision": {
          "url": "http://172.19.0.2:8003/mcp/vision/explain",
          "token": "<JWT 形如 eyJhbGciOiJIUzI1NiI...>"
        }
      },
      "clientInfo": {"name": "XiaozhiClient", "version": "1.0.0"}
    }
  }
}
```

含义：

- `protocolVersion: "2024-11-05"` — server 用的 MCP spec 版本
- `capabilities.vision` — server 暴露给 ESP32 的 vision 能力（HTTP endpoint
  `/mcp/vision/explain` + 自带 JWT），ESP32 可以让 LLM 调用图像理解。
  baseline OttoRobot 不一定用到，但 contract 必须记录这个 capability
  存在
- `clientInfo.name: "XiaozhiClient"` — server 自报家门（区别于 §4.3 接入点
  路径用的 `XiaozhiMCPEndpointClient`）

**ESP32 接收侧**：`application.cc:565` 进 `McpServer::ParseMessage(payload)`
处理 — 上游 `main/mcp_server.cc` 实现 `initialize` 响应（返回 ESP32 自身
capabilities），完成标准 MCP 握手；之后 server 会发 `tools/list` 收集
ESP32 的 `AddTool` 工具。

**M4 的隐含约束**：`AddTool` 名字 / schema 必须能通过 MCP `tools/list`
正确序列化（cJSON 兼容）。

### 4.3 与 xinnan-tech MCP 接入点的关系

xinnan-tech server **同时**支持另一种 MCP 路径：`ws://server:8004/mcp_endpoint/mcp/?token=...`，
此处 **server 是 MCP client**，外部程序（M1 adapter）是 MCP server。
这个**和 §4.1 的 `type:"mcp"` 子帧并存但物理路径不同**。

| 维度 | §4.1 `type:"mcp"` 子帧 | xinnan-tech MCP 接入点 |
|---|---|---|
| WS endpoint | `ws://server:8000/xiaozhi/v1/` (audio + control) | `ws://server:8004/mcp_endpoint/mcp/` (纯 MCP) |
| 谁是 server | **ESP32** | M1 adapter |
| 谁是 client | xinnan-tech server | xinnan-tech server |
| 注册的工具来自 | ESP32 `AddTool()` (M4) | M1 实现 (后续) |
| 本项目用途 | M4 暴露 ESP32 硬件能力（move/look/sense） | M1 暴露 Hermes / 通用能力给 server |

两条 MCP 路径**互不冲突**，server 在 LLM `tools/call` 时按工具名路由。

---

## 5. Out of scope（v1 不覆盖）

- HTTP OTA 协议（`ota.cc` 拉 `CONFIG_OTA_URL` 返回的 JSON）— 单独契约
- MQTT path（`mqtt_protocol.cc`）— 本项目不用
- 设备配网 BluFi 协议 — 上游 `docs/blufi_zh.md`
- Audio binary frame 的 v2/v3 头格式 — 单独契约（如果将来本项目升 v3）
- xinnan-tech server 内部 ASR/TTS/LLM provider 配置 — 那是 server 配置，不是 contract

## 6. 变更纪律

任何对 §1-4 的更改 必须：

1. 先确认上游 commit pin（更新 frontmatter `upstream_pin`）
2. 起 `[contract]` 前缀的 handoff，列出谁要 sync（M1 / M2 / M3 / M4 哪些受影响）
3. 在 `docs/contracts/api/CHANGELOG.md` 加一行（含日期 + 影响范围）
4. 老版本归 v1/ frozen，新版本写 v2/，`current/` 指针更新

## 7. Open questions for M1/M2/M3/M4

- **M1**：MCP 接入点（§4.3）的 token 怎么获取？xinnan-tech server 配置里
  生成还是 server 启动时随机？需 M1 开工前实测
- **M2**：openai-shim 的 SSE 必须严格对齐字段（详见 [m1-mcp-transcript-egress](../../../research-notes/m1-mcp-transcript-egress.md)
  + [xinnan-tech-openai-and-mcp](../../../research-notes/xinnan-tech-openai-and-mcp.md) §3）；
  本 contract 不重复，但 M2 要把那张表作为 sub-contract 引用
- **M3**：transcript 出口走 §3 `type:"stt"` (display) 还是走 OpenAI-compat
  `messages` (chat) — 见 [ADR-0005](../../../adr/0005-openai-compat-transcript-egress.md)
  最终决定走后者
- **M4**：`AddTool` 命名要先验 xinnan-tech `sanitize_tool_name`
  ([xinnan-tech-openai-and-mcp §2](../../../research-notes/xinnan-tech-openai-and-mcp.md))

## 8. 实测验证手段

```bash
# 本机 docker 起后 (H011 done)
# 用 wscat 模拟 ESP32 接入，验 server 收到 hello 后返回 hello
wscat -c 'ws://localhost:8000/xiaozhi/v1/' \
  -H 'Protocol-Version: 1' -H 'Device-Id: aa:bb:cc:dd:ee:ff' -H 'Client-Id: test-uuid'

# 进交互后输入：
> {"type":"hello","version":1,"features":{"mcp":true,"aec":false},"transport":"websocket","audio_params":{"format":"opus","sample_rate":16000,"channels":1,"frame_duration":60}}

# 期望立刻回：
< {"type":"hello","transport":"websocket","session_id":"<...>","audio_params":{...}}
```

这是 H1b done 后的第一道 sanity check。

### 8.bis H1b 实测数据 (2026-06-19)

baseline 端到端验证记录（OttoRobot 板，xinnan-tech minimal docker + DeepSeek LLM）：

| 项 | 值 |
|---|---|
| ESP32 device MAC | `ac:a7:04:30:91:78` |
| 主机 LAN IP | `10.206.218.66/24` (wlp0s20f3 接手机热点 `kklull`) |
| 串口 | **`/dev/ttyACM0`**（ESP32-S3 USB-OTG，**不是** `/dev/ttyUSB0`） |
| 实际烧的 OTA URL | `http://10.206.218.66:8003/xiaozhi/ota/` |
| WS endpoint | `ws://10.206.218.66:8000/xiaozhi/v1/` |
| Session ID 样例 | `bbc16c92-c8eb-43e8-ae67-f80b0ba23be4` |
| WS hello 握手 RTT | < 1s (monitor 时戳人工观察) |
| 一轮对话 RTT (用户说完 → TTS 开播) | **~4-6s**（FunASR + DeepSeek + EdgeTTS）|
| ESP32 boot heap free | (待补；M4 开工前 `grep heap_init` monitor 输出回填) |
| 增量 build 耗时 (改 OTA_URL 后) | 3m17s |

**人工验证**：对机器人说"你好小智"，FunASR 识别为"你好，小子"（小智发音
ASR 默认模型识别不稳；不影响项目），DeepSeek 回复"哈喽～你哪位啊？"，
EdgeTTS 合成喇叭播出。**双向通路全跑通**。

H1b handoff 完整版：[archive/2026-06-19-flash-baseline-to-local-server-h1b-013.md](../../../handoffs/archive/2026-06-19-flash-baseline-to-local-server-h1b-013.md)。
