---
status: current
---

verdict: (d) other

upstream: `a1973e07b71e018199018060497c58cd45d5d387`

结论：ASR 完整 transcript 没有官方 MCP-client 出口；实际外发是 LLM `messages`，另有设备 WS 展示帧和可选 manager-api 上报。

证据：
- `main/xiaozhi-server/core/providers/asr/base.py:124` 取 `raw_text`，`:149` 成 `enhanced_text`，`:172-174` 调 `enqueue_asr_report(...)` 和 `startToChat(...)`。
- `main/xiaozhi-server/core/handle/receiveAudioHandle.py:91` 发设备 STT 展示，`:96` 把 `actual_text` 投给 `conn.chat`。
- `main/xiaozhi-server/core/handle/sendAudioHandle.py:325-328` 设备 WS frame：`{"type":"stt","text":stt_text,"session_id":...}`；`stt_text` 已去标点/emoji，JSON transcript 只取 `content`，不是完整出口。
- `main/xiaozhi-server/core/connection.py:926` 写 user message，`:981-996` 调 LLM；`core/providers/llm/openai/openai.py:94-115` / `:140-161` 以 OpenAI-compatible `messages` 发出。
- 可选上报：`core/handle/reportHandle.py:175-195` 入 ASR report queue；`config/manage_api_client.py:222-242` POST `/agent/chat-history/report`，含 `content`/`audioBase64`。
- MCP endpoint 不是 transcript callback：`core/providers/tools/mcp_endpoint/mcp_endpoint_executor.py:37-40` 仅工具执行时调用；`mcp_endpoint_handler.py:353-364` 发 JSON-RPC `method:"tools/call"`，参数来自 tool arguments。

所以不是 (a)；设备帧也不是面向 MCP 的完整 (b)；也不是 (c)，因为 transcript 会进入 LLM 和可选管理端。

## M3 工作量影响

走 M2 `openai-shim` 捕获 OpenAI-compatible `messages` 最小：抽取 user message 并转交 Hermes，几十行、<1 天。若坚持 MCP-only，需要改 server 增加 ASR event/notification 或 hook，约 1-2 天，且不再是零改上游。
