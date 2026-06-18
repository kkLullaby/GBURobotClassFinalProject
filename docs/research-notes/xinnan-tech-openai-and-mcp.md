---
status: draft
created: 2026-06-18
upstream_repo: xinnan-tech/xiaozhi-esp32-server
upstream_commit: a1973e07b71e018199018060497c58cd45d5d387   # main, 2026-06-18 16:57 +0800
read_at: 2026-06-18
files_read:
  - main/xiaozhi-server/core/providers/llm/openai/openai.py (178 lines)
  - main/xiaozhi-server/core/providers/tools/mcp_endpoint/mcp_endpoint_client.py
  - main/xiaozhi-server/core/providers/tools/mcp_endpoint/mcp_endpoint_handler.py
  - main/xiaozhi-server/core/providers/tools/mcp_endpoint/mcp_endpoint_executor.py
  - docs/mcp-endpoint-integration.md, docs/mcp-endpoint-enable.md
---

# xinnan-tech: OpenAI provider + MCP 接入点精读

## 1. OpenAI provider — `base_url` 替换点

文件：`main/xiaozhi-server/core/providers/llm/openai/openai.py`

| 关注点 | 位置 | 摘要 |
|---|---|---|
| `base_url` 读取 | L23-27：`if "base_url" in config: self.base_url = config.get("base_url") else: self.base_url = config.get("url")` | **两个键名都接受**，M2 openai-shim 在 server `data/.config.yaml` 里写 `base_url: http://m2-shim:8089/v1` 即可 |
| 客户端构造 | L72：`self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=custom_timeout)` | 直接用官方 `openai` SDK，**不是手写 HTTP**——意味着 M2 必须严格遵守 SDK 期望的 SSE chunk 结构，否则 SDK 在 client 侧就 raise |
| 流式请求 | L91-101 (`response`)：`stream=True` 固定开启 | 不支持非流模式，M2 shim 必须输出 SSE |
| 思考模式 deny-list | L13-19, L80-89 (`_apply_thinking_disabled`) | 域名命中 (aliyuncs/bigmodel/moonshot/volces) 时把 `extra_body` 注入 `enable_thinking:false` —— M2 shim 的 host 不在表里，**不会被注入**；不用担心 |
| `<think>` 标签过滤 | L122-132 | server 自己消化 `<think>...</think>` 段，不会传给 ESP32；M2 shim 不需要做这件事 |
| function-call 流 | L138-178 (`response_with_functions`) | 同样依赖 SDK 字段：`delta.tool_calls`、`chunk.usage` (CompletionUsage 类型) |

**Failure path**：

- L114-117 `for chunk in responses` 阶段，任何 chunk 缺 `choices` 或
  `choices[0].delta` 抛 IndexError → 静默 `content = ""`；不抛错。
  → 意味着 **M2 shim 漏字段 server 不会日志报错，只会"机器人没声音"**。
  这就是 ADR-0001 pitfall #5 的根因。

## 2. MCP 接入点 — 握手序列

文件：`mcp_endpoint_handler.py` `connect_mcp_endpoint()` (L14-43)。
WS 目的地：`ws://<server>:8004/mcp_endpoint/mcp/?token=<...>`
（文档 `docs/mcp-endpoint-integration.md:23`）。

```
M1 / mcp-pipe                              xinnan-tech server
     │                                              │
     │  ── WS connect (token in query) ──►          │   websockets.connect()
     │                                              │
     │  ◄── 1. initialize (id=1) ──                 │   send_mcp_endpoint_initialize  L224
     │      jsonrpc 2.0, params.protocolVersion     │     payload.params:
     │      = "2024-11-05", clientInfo =            │       protocolVersion 2024-11-05
     │      XiaozhiMCPEndpointClient/1.0.0          │       capabilities {roots, sampling}
     │                                              │
     │  ── result(id=1, serverInfo{name,ver}) ─►    │   handler L88-99
     │                                              │
     │  ◄── 2. notifications/initialized (no id) ── │   L31 send_mcp_endpoint_notification
     │                                              │
     │  ◄── 3. tools/list (id=2) ──                 │   L34 send_mcp_endpoint_tools_list  L262
     │                                              │
     │  ── result(id=2, tools=[…], nextCursor?) ─►  │   handler L100+，cursor 分页 L272
     │                                              │
     │  (M1 客户端 ready；后续随时 tools/call)       │   call_mcp_endpoint_tool  L290+
     │  ◄── tools/call (id=N) name+arguments ──     │     params: {name, arguments}
     │  ── result(id=N, content[0].text) ─►         │   handler L78-87
```

**关键事实：**

- 是 **server 主动连 M1**：xiaozhi server 是 MCP **client**，M1 / mcp-pipe
  跑在外面当 **server**（与一般"server 暴露 MCP，client 连入"反过来）。
  → M1 设计上要监听 WS、等 server 拨过来。
- token 只在 URL query (`?token=abc`)，**没有独立的 auth/hello 帧**。
- 工具名要走 `sanitize_tool_name`（`mcp_endpoint_client.py:60`），名字含
  特殊字符会被改写；M4 的 `AddTool` 命名要先确认与 sanitize 兼容。
- `tools/list` 用 id=2，**支持 cursor 分页**（`send_mcp_endpoint_tools_list_continue` L272）。

## 3. OpenAI SSE 字段对照表 — M2 shim 必输 vs 可选

按 `core/providers/llm/openai/openai.py` 实际读取路径推导（**`stream=True` 模式下**）：

| 字段（JSON path） | M2 shim 必须输出？ | 来源 / 缺失后果 |
|---|---|---|
| `choices[0].delta.content` (str) | **必须**（普通文本流） | L116-118：缺 → SDK 给空串 → 静音 |
| `choices[0].delta.tool_calls` | **仅 function-call 时**必须 | L168：`getattr(delta, "tool_calls", None)`，可缺 |
| `choices[0].finish_reason` | OpenAI SDK 内部需要 | 缺 → SDK 可能死循环，建议每流末发 |
| `usage` (= `openai.types.CompletionUsage` 实例) | **可选**；缺只是少一行日志 | L169-176：仅在 `response_with_functions` 时被读 |
| `id`, `object`, `created`, `model` | OpenAI SDK 解析必需 | 缺 → SDK 抛 ValidationError；M2 必须发齐 |
| `service_tier`, `system_fingerprint` | 可缺 | SDK 容忍 |
| `<think>...</think>` 包装的内容 | 不要发 | server 会过滤但混在 content 流里也是浪费 |

**M2 shim 实现要点：**

- 用官方 `openai` SDK 的 chunk 数据类直接 `model_dump_json()` 序列化最稳，
  绝对不要手拼 JSON。
- chunk 之间用 `data: <json>\n\n`，结束发 `data: [DONE]\n\n`。
- M2 必须保证最后一个 chunk 的 `choices[0].finish_reason = "stop"`，
  否则 SDK 端可能 hang。

> 实测验证手段（M2 落地时）：跑 `openai.OpenAI(base_url="http://m2:8089/v1")`
> 直接对 M2 发 `chat.completions.create(stream=True)` 跑通 ≠ 跑通 server
> 路径，但 **跑通了基本能保 server 路径也通**（因为 server 用的也是这套 SDK）。
