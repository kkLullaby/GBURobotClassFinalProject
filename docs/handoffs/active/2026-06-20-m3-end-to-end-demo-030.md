---
id: 2026-06-20-m3-end-to-end-demo-030
from: planner
to: user
parent: 2026-06-20-m3-m1-proxy-and-real-send-029v2
supersedes:
status: pending
created: 2026-06-20
artifacts:
  - 仓库外: /tmp/m3-demo-recording.mp4 (可选)
---

## Why now

M3 三件套：
- ✅ H028 plugin 骨架 (3/3 PASS)
- ✅ H028.bis Stages A/B 装 + enable + config
- ✅ H028.ter listener 真起 (4/4 PASS)
- ⏳ H029v2 M1 proxy + adapter.send 真接（待 codex）

H028.ter 完后理论上 H028.bis Stages C/D/E/F (curl smoke → ESP32 voice
→ TUI 见 [xiaozhi]) 应该都通了，但没人去物理验过。H030 是**M3 第一次
端到端实地 demo**——证明 ADR-0005 完整闭环 + 第一具物理化身能用。

依赖：H029v2 done（adapter.send 真能推 show_text 到 ESP32），否则 Stage F
(Hermes 主动让机器人显示文字) 跑不通。

跟 H013 / H022 同模式：planner main-loop 起 coach session 远程指导 user。

## Objective

完整跑通 4 个 demo 场景：

1. **Stage A (transcript ingress)**：对机器人说 "你好" → TUI 看到 `[xiaozhi:ac:a7:04:30:91:78]` 收到 transcript
2. **Stage B (Hermes 真处理)**：Hermes session spawn 跑 agent → 看 session log 含 user/assistant 全文
3. **Stage C (M3 send 反向)**：在 hermes TUI 输 `send xiaozhi:ac:a7:04:30:91:78 "看这里"`
   → 机器人屏幕弹"看这里"
4. **Stage D (cron 演练)**：写 1 个 cron `*/2 * * * * hermes notify xiaozhi "ping"`
   → 2 分钟后机器人屏幕弹 "ping"

## Constraints

- 不改本仓代码（M3 已 done）
- 不改 hermes-agent 本体
- M2 shim 已配好 (H028.bis Stage C 已切 8645 webhook)
- M1 sidecar 起在 8650 (H029v2 done 后跑 `pyx -m uvicorn xiaozhi_mcp_adapter.proxy_http:app --port 8650 &`)
- secret 不入仓库

## Stages

### Stage 0 (5 min)：先决条件 — 所有服务在跑

```bash
# xinnan-tech docker
docker ps --filter name=xiaozhi-esp32-server --format '{{.Status}}'
# 期望: Up

# mcp-endpoint
ss -tln | grep 8004

# M2 shim
ss -tln | grep 8089 && tail -3 /tmp/shim.log

# M1 sidecar (H029v2 done 后)
ss -tln | grep 8650

# Hermes gateway with xiaozhi platform
ss -tln | grep 8645
hermes plugins list | grep xiaozhi
ps aux | grep 'hermes gateway' | grep -v grep
```

### Stage A — transcript ingress (5 min)

对机器人讲："你好"

```
xinnan-tech log: 识别文本: 你好
shim log:        SSE delta + fork POST 8645 → 202
hermes gateway:  XiaoZhi listener received transcript ... 202
                 session spawn for chat_id="xiaozhi:ac:a7:04:30:91:78"
```

TUI: 进 `hermes`，sidebar 看到 `[xiaozhi]` channel 出现新 session

### Stage B — Hermes 真处理 (3 min)

`hermes session show <session-id>` 看 log
- 期望: `msg='XiaoZhi user said: 你好. Assistant replied: <DeepSeek 真智能回复>'`

### Stage C — send 反向 (5 min)

```bash
# 设 adapter MCP URL 给 hermes gateway
export XIAOZHI_MCP_ADAPTER_URL='http://127.0.0.1:8650'
pkill -f 'hermes gateway' && sleep 2
hermes gateway run &
sleep 5

# TUI 触发 send
hermes
# 在 TUI 内: /send xiaozhi:ac:a7:04:30:91:78 "看这里"
```

期望:
- adapter log: `POST http://127.0.0.1:8650/tools/show_text → 200`
- sidecar log: `call_show_text(device=ac:..., text=看这里, kind=chat)`
- M1 stdio: 发 jsonrpc → xinnan-tech mcp_endpoint → ESP32
- ESP32 屏幕: 弹 "看这里"（chat 区，持久）

### Stage D — cron (5 min)

```bash
# 列现有 cron
hermes cron list

# 加一个 2 分钟一次的 ping
hermes cron add --schedule '*/2 * * * *' --deliver xiaozhi --message 'ping'

# 等 2 分钟，看机器人屏幕
```

期望: 每 2 min 机器人屏幕弹 "ping"

```bash
# 验完删
hermes cron remove ...
```

## Acceptance Criteria

- [ ] Stage 0 所有服务 LISTEN
- [ ] Stage A：TUI 见 `[xiaozhi:ac:...]` 新 session 出现
- [ ] Stage B：session log 含完整 user/assistant 文本（不是空 msg）
- [ ] Stage C：TUI send → 机器人屏幕真显示 "看这里"
- [ ] Stage D：cron 2 分钟触发 → 屏幕弹 "ping"
- [ ] What I Did 贴 Stage-by-Stage 实测日志
- [ ] (可选) 录屏 /tmp/m3-demo-recording.mp4
- [ ] 任何发现的 bitter lesson 写 Open Questions 供 H027 集中回灌

## Context Pointers

- @docs/handoffs/active/2026-06-20-m3-plugin-install-and-hermes-verify-028bis.md (Stages A/B 已 done)
- @docs/handoffs/active/2026-06-20-m3-xiaozhi-adapter-listener-028ter.md (listener 真起)
- @docs/handoffs/active/2026-06-20-m3-m1-proxy-and-real-send-029v2.md (M1 proxy + send 真接)
- @docs/handoffs/archive/2026-06-19-demo-end-to-end-real-deepseek-via-shim-022.md (H022 ESP32 voice 实地 demo 流程参考)
- @docs/handoffs/archive/2026-06-19-real-hermes-transcript-handshake-020.md (H020 Stage E 真 hermes spawn session 参考)
- @docs/designs/active/m3-hermes-plugin-architecture.md §2 (拓扑图)
- @.claude/memory/shared/global-commands.md

## Out of Scope

- 改本仓代码（任何 bug 写新 handoff fixup）
- Cross-channel routing (留 Week 3 §3.6)
- TTS（机器人**说话**而非显示，留架构限制）
- 录屏自动化 (留 Week 4 demo polish)

## Recovery

| 症状 | 修 |
|---|---|
| Stage 0 8645 不 LISTEN | H028.ter 新 adapter.py 没 cp 到 ~/.hermes/plugins/xiaozhi/ |
| Stage A 401 | secret 不一致；shim env XIAOZHI_WEBHOOK_SECRET 和 gateway env 必须同源 |
| Stage A session 不 spawn | hermes 日志查 handle_message 是否被调；可能是 platforms.xiaozhi.enabled 没 true |
| Stage C sidecar 不 reachable | `ss -tln | grep 8650`；起 `pyx -m uvicorn xiaozhi_mcp_adapter.proxy_http:app --port 8650 &` |
| Stage C ESP32 屏幕没字 | M1 真连 mcp_endpoint? 看 sidecar log call_show_text 收没收；ESP32 boot 看 tool count >=14 |
| Stage D cron 不触发 | `hermes cron list` 看 next_fire 时间；可能 hermes scheduler 没起 |

## For Auditor

H030 done 后 + H029v2 done 后 → 起 **M3 batch auditor handoff (H031)**:
review hermes-xiaozhi-plugin + xiaozhi-mcp-adapter 的 M3 增量;
按 rubric `docs/rubrics/m3-plugin-review.md` (planner 起 H031 前先写)

## Open Questions (实测后回填)

- Hermes cron 是否支持 `deliver=xiaozhi`?
- ESP32 端 chat 区显示长文本（>30 字）会怎么？换行/截断/省略？
- 真用户 demo 答辩时该走哪 3 个场景？(写进 demo-script.md)
