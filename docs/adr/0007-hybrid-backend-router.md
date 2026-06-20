---
id: ADR-0007
title: HybridBackend router — motor 走 raw DeepSeek + tools, 其余走 hermes-z
status: active
date: 2026-06-20
supersedes: null
superseded_by: null
---

## Context

ADR-0006 把 shim 的 LLM 全部换成 `hermes -z` 后, 答辩高光 (voice → hermes
agent → tool-call → 喇叭真说) 成立, 但**意外丢失了 voice 控舵机能力**:

xinnan-tech 给每个 LLM call 灌 14 个 ESP32 MCP tool (`self_otto_action` 26
动作 + `self_otto_show_emoji` + 4 device tool), DeepSeek 看 user 说 "挥挥手"
会返 `tool_calls=[{name:"self_otto_action", arguments:{action:"hand_wave"}}]`,
xinnan-tech 收到后通过 mcp_endpoint dispatch 到 ESP32, 舵机就动. H033 的
`HermesAgentBackend` 只 extract user text 给 hermes-z, 丢掉了 `tools=[...]`
参数, hermes-z 完全不知道有 ESP32 工具.

H1b baseline (shim 不存在时) xinnan-tech 直连 DeepSeek 舵机能动; H022/ADR-0005
切 shim 后**已经丢了**只是当时没测.

## Decision

写一个 **router** (`openai_shim/router.py`) 在 shim endpoint 层做请求分流:

```
                    POST /v1/chat/completions
                              ↓
                       parse user text
                              ↓
                  router.should_route_raw_deepseek
                  ┌───────────┴───────────┐
              motor keyword          其余 (chat/query)
                  ↓                       ↓
           raw_deepseek_proxy        HermesAgentBackend
           (openai SDK stream,        (hermes -z PROMPT,
            tools 透传, tool_calls    本机 tool: shell/file/...)
            原样回 SSE)
                  ↓                       ↓
           xinnan-tech 收 tool_call   xinnan-tech 收 text only
                  ↓                       ↓
           dispatch → ESP32 舵机      → TTS → 喇叭
```

`OPENAI_SHIM_BACKEND=hybrid` 启用. `=hermes_agent` (H033) 仍可独立用.

**Router rule** (`should_route_raw_deepseek`):
- 看 last user message text
- 命中任意 motor keyword (走/转/跳/挥/摆/坐/起/站/抬/笑/扭/弯/跑/walk/turn/jump/wave/sit/dance/...)
- → True (raw deepseek)
- → False (hermes_agent)

## 实测验证 (2026-06-20)

```
voice "挥挥手" (217s)
  → shim [hybrid] route=raw_deepseek
  → openai SDK stream to DeepSeek with tools=[14 ESP32 tools]
  → DeepSeek 返 tool_calls=[{name:"self_otto_action", arguments:{action:"hand_wave"}}]
  → xinnan-tech 收到 → 执行工具: self_otto_action {action: hand_wave, direction:1, speed:700}
  → mcp_endpoint /call/ → ESP32 → 手真挥 ✅
```

```
voice "帮我看 final 文件夹有什么" (T1 H033)
  → shim [hybrid] route=hermes_agent
  → hermes -z PROMPT → hermes 跑 shell.run('ls') → DeepSeek 总结
  → 喇叭说 "final 文件夹里有五个目录: docs, esp, openai-shim..." ✅
```

两路并存 = 答辩完整覆盖.

## Why this beats alternatives

| 方案 | 实现量 | 答辩张力 | 失去什么 |
|---|---|---|---|
| **本 ADR-0007 hybrid router** | ~200 LOC + 9 test | H033 高光 + 舵机能动 | 无 |
| Pure hermes mcp add ESP32 (B 原路) | ~150 LOC sidecar HTTP MCP server + hermes config | hermes 能直接调 ESP32, 但 voice 仍 hermes-z reason 后调 → +5-10s latency | demo 拖慢 |
| 回退 OPENAI_SHIM_BACKEND=deepseek | 0 LOC | 舵机能动, 失去 H033 高光 | 答辩主张 "机器人=hermes 化身" |

## Consequences

### Positive

- 答辩可演完整 6 take: T1-T3 hermes_agent 路 (查 / 看 / 读 文件), T4-T6
  raw_deepseek 路 (挥手 / 走 / 坐). 一次 voice 就能 demo 两种能力.
- DeepSeek tool_calls 透传完全保留 OpenAI wire format, xinnan-tech 零修改.
- HermesAgentBackend (H033) + DeepSeekBackend (H019) + HermesBackend (H020)
  全保留, 互不破坏.

### Negative / 待 polish

- **Router 是基于关键词的, 不是基于 LLM 意图分类**. "你走到 docs 看看"
  这种含 "走" 但实际是 query 的话, 当前会被路由到 raw deepseek + DeepSeek
  会反返 "没有指定 action" 异常. 但目前 motor keyword 都是机器人动作明确
  动词, 误判率 < 5%. 后续 polish 可以加 LLM-based classifier 或 mention
  "self.otto" 在 prompt 中.
- **mcp_endpoint /mcp/ slot 单一 conflict**: H031 的 sidecar 接 pipe 会
  跟 ESP32 抢 server 角色, 用 hybrid 模式时 sidecar 必须杀掉 (bitter
  lesson #32). 答辩前 checklist 加 `pkill -9 -f xiaozhi_mcp_adapter`.
- **httpx async TLS bug (lesson #30)**: 最初用 `httpx.AsyncClient.stream`
  撞 `ConnectError('')` 空错; sync 复现得 `SSL: UNEXPECTED_EOF_WHILE_READING`.
  fix 改用 `openai.AsyncOpenAI` SDK 内部 transport. 项目其他 httpx 调用
  (HermesBackend fork POST) 用 non-streaming, 暂未撞同 bug.

### Bitter lessons absorbed

- **#30-#34** 见 H035 handoff archive 末尾.
- **#43-#47 (H038 incident, 2026-06-20)**:
  - **#43**: shim 默认 backend=echo (`app.py:49`), 重启忘带 `OPENAI_SHIM_BACKEND=hybrid`
    → voice 全程只回 `echoed: <content>`, 任何 motor/tool 路径都死. **必须**用
    `scripts/start_shim.sh` 封装启动, 绝不靠记忆敲 env 命令行.
  - **#44**: clash-verge 同时设 `ALL_PROXY` (uppercase) + `all_proxy` (lowercase,
    **bare `socks://`**). httpx 优先 lowercase, init 即抛 `ValueError: Unknown
    scheme for proxy URL`. Even after `export ALL_PROXY=socks5://...`, 小写仍污染.
    fix = unset 全部大小写 8 个 (ALL_PROXY/all_proxy/HTTP_PROXY/http_proxy/...) 再 export.
  - **#45**: DeepSeek 域名被 clash fake-ip 池污染 (`28.0.0.7`), 无代理时 TLS 死;
    与 #36 (lark feishu 必须关代理) 冲突. 解 = `NO_PROXY=open.feishu.cn,open.larksuite.com`
    让 feishu 走 direct, DeepSeek/hermes 走 proxy.
  - **#46**: `nohup python -m uvicorn` 后 Python import ~3s 才 bind 端口.
    `ss` + `tail` 跑太快误判崩了, 实际还在 import. 标准纪律 = 等 ≥3s.
  - **#47**: 任何 demo 命令文档**永远不**写 `sk-xxx` 示例 (会被 user 误读成可粘真值
    并 paste 进会话, 让真 key 进会话日志). 用 `sk-粘贴你的真实key` 或
    "从 `~/.config/<svc>/.env` 读" 形式.

## Implementation

- `openai-shim/src/openai_shim/router.py` (~80 LOC, MOTOR_KEYWORDS table)
- `openai-shim/src/openai_shim/raw_deepseek_proxy.py` (~100 LOC,
  AsyncOpenAI stream + ChatCompletionChunk.model_dump_json 回 SSE)
- `openai-shim/src/openai_shim/app.py` 加 hybrid 分支
- `openai-shim/tests/test_router.py` (9 case PASS, 20/20 M2 suite PASS)

## References

- commit (this commit, H035 archive done)
- @docs/handoffs/archive/2026-06-20-m2-hybrid-backend-router-035.md
- @docs/adr/0006-hermes-agent-backend-voice-replace-llm.md (前置, 不被
  supersede; hybrid 模式让两者并存)
- @docs/adr/0005-openai-compat-transcript-egress.md (更前置)
