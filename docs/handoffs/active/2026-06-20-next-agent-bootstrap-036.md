---
id: 2026-06-20-next-agent-bootstrap-036
from: planner
to: next-planner-and-executor
parent: 2026-06-20-m2-hybrid-backend-router-035
supersedes:
status: pending
created: 2026-06-20
artifacts:
  - 本仓库整体已是答辩完成版 + open-source 化
  - 下一阶段目标: 加 channel (手机 / 飞书) + 加 hermes MCP tool (飞书 OpenAPI)
---

## Read me first (开机即读)

你是接手 **ottagent** 项目的下一个 agent. 项目当前状态:

- **答辩已结束**, 已上传 GitHub public repo: `kkLullaby/ottagent`
- 架构闭环 (M1-M4 + H033 + H035): voice → ESP32 → docker → shim
  → (hybrid router) → DeepSeek + tools | hermes-z + tool-call
- 真物理验证: 舵机能动 + voice 真指挥 hermes 调本机工具
- **此 handoff = 你的入口**. 不要读所有历史 handoff (35+ archive), 看完此文档 + 下面几个 must-read 就够.

## Must-read 顺序 (15 min)

1. [README.md](../../../README.md) — 项目总览, 创新点, channels 表格
2. [CLAUDE.md](../../../CLAUDE.md) — 项目工作纪律 (三角色 agent / handoff 协议 / scope)
3. [docs/adr/INDEX.md](../../adr/INDEX.md) — 7 个 ADR, 重点看 0005/0006/0007 (transcript / hermes-z / hybrid)
4. [docs/architecture.md](../../architecture.md) — 高保真架构图 + 数据流
5. [docs/handoffs/INDEX.md](../INDEX.md) — recent done 段了解最近 5 个里程碑
6. [ROADMAP.md](../../../ROADMAP.md) — 短期 / 中期 / 长期目标

## 你要做的 — 用户的下一阶段需求

用户原话: "加上和手机通信, 通过工具连接飞书等一系列功能"

拆解成具体目标:

### 目标 A — 手机 channel (用户↔机器人 双向)

机器人能**被手机控制**, 也能**主动给手机推消息**.

候选方案 (用户没指定, 你需要 propose):
- **A1 Telegram bot** (hermes 已自带 telegram channel, 最简单, ~30 min)
- **A2 微信公众号** (受限制 — 服务号 60s 内回复 / 订阅号无主动推, 不推荐)
- **A3 飞书机器人** (跟目标 B 合并, **首选**)
- **A4 SMS** (Twilio 或国内服务商, 适合纯通知)

参考 hermes 自带 channel 实现:
- `~/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages/hermes_platforms/telegram/`
- `~/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages/hermes_platforms/whatsapp/`

### 目标 B — 飞书 OpenAPI tool (机器人能"做"事)

让 hermes-z 能直接调飞书 OpenAPI, voice 指挥实例:
- "你好小智 → 发个消息给我的 Lark 自己" → hermes 调 `lark.messages.send_self`
- "你好小智 → 看看我今天的飞书日程" → hermes 调 `lark.calendar.list_today`
- "你好小智 → 创建一个会议室预订" → hermes 调 `lark.meeting_room.book`

实现路径:
- **B1 写一个 MCP server** `lark-mcp-server` (Python stdio / HTTP) 暴露飞书 tool
- **B2 `hermes mcp add lark --command python --args -m lark_mcp.main`**
- **B3** hybrid router 不动 — chat/query 路自动会路到 hermes-z, hermes 自动看到 lark tool

### 目标 C — 多 channel mesh (B 完了再做)

让 hermes cron + telegram + lark 同时推 ESP32:
- 早上 8 点 cron 触发: 喇叭说"早安, 今天 3 个会议"
- Telegram 收到老板消息: 喇叭说出来 + 屏幕显
- 飞书有 @ : 同样

## Constraints

- 跟项目当前架构兼容: M1-M4 不动, ADR-0007 hybrid 不动. 加东西在外围 (新 plugin / 新 MCP server).
- 三角色协作: 你是 planner. coding 给 codex (sandbox), 物理实测给 user.
- 每个新模块独立 Python 包: `lark-mcp-server/`, `<channel>-plugin/`.
- **绝不**把 secret commit 进 git. flying-lark token 走 `.env` + `os.environ.get(...)`.
- 兼容当前 demo 路径: 加新东西不破坏 "挥挥手"舵机动 / "查文件夹"喇叭说.

## Suggested first 3 steps

### Step 1 — 跟用户对齐方案 (10 min)

把 A1-A4 + B 的选择列给用户 ask. 关键问题:
- 用户用的是飞书 (Lark) 国内版还是 Lark Suite 国际版? (API host 不同)
- 用户有飞书 app self-build 权限吗? (要拿 app_id / app_secret)
- 优先 personal (个人助理) 还是企业 (团队协作)?

### Step 2 — 写 lark-mcp-server spike (executor codex 1h)

最小可演: 1 个 tool `lark_send_message_to_self`, 走 stdio MCP 协议. 5-10 个 case.

Handoff template:
```
id: 2026-XX-XX-lark-mcp-spike-037
from: planner
to: executor
status: pending
Objective: ...
Constraints: codex-sandbox-friendly: mock requests; 不真起 socket
Acceptance Criteria:
- [ ] pyproject.toml + src/lark_mcp/main.py (stdio MCP server)
- [ ] tool lark_send_message_to_self(text: str) — schema 完整
- [ ] 5+ pytest case (含 token 错 / API 5xx / network error)
- [ ] README 50 行
Out of Scope: 真飞书 OpenAPI 调用 (留 H037.bis user 物理)
```

### Step 3 — 装 + 物理实测 (H037.bis user)

把 lark-mcp-server 接入 hermes:
```bash
hermes mcp add lark --command python --args -m lark_mcp.main \
  --env LARK_APP_ID=... LARK_APP_SECRET=...
```

讲: "你好小智 → 给我发个飞书消息说你好"
期望: 飞书收到自己发的消息, 喇叭说 "已发送".

## 别犯的错 (bitter lessons 速查)

| # | 教训 | 如何避免 |
|---|---|---|
| 17 | codex 同时 PyPI DNS + rm policy 双卡 | Suggested Steps 写 `PYTHONPATH=src ... pytest`; Constraints 写"cleanup 不能 rm" |
| 18 | codex sandbox 不能 bind 任何 port | 起 server-起测必 blocked → planner main-loop 接 |
| 26 | codex TestClient lifespan hang in sandbox | 同上 |
| 27 | mcp_endpoint `/mcp/` (server) vs `/call/` (client) 角色 | 一个 single_module 只有 1 个 server slot |
| 28 | DeepSeek key 不要让 user 手 paste 占位符 | 命令模板用 `$(grep api_key data/.config.yaml ...)` |
| 30 | httpx async stream + TLS 抛空 ConnectError | 改用 openai SDK 内部 transport |
| 31 | sync httpx 是 debug 神器 | async 抛空错时, sync 复现拿完整 trace |
| 32 | mcp_endpoint `/mcp/` slot 单一, sidecar + ESP32 mutual exclusive | hybrid 模式杀 sidecar |
| 33 | "一次能再次不能" 第一直觉看进程/抢占 | 不要先改代码, 先看 `ps`/`docker logs`/链路状态 |
| 34 | DeepSeek function name pattern `^[a-zA-Z0-9_-]+$` | xinnan-tech 已把 `self.otto.action` 转 `self_otto_action`, 别手写 dot |

完整 lesson 列表在 `docs/retros/` (H027 batch retro 后会汇总).

## Resources

- Hermes Agent 文档: <https://github.com/NousResearch/hermes-agent>
- 飞书 OpenAPI 文档: <https://open.feishu.cn/document>
- xinnan-tech server: <https://github.com/xinnan-tech/xiaozhi-esp32-server>
- MCP 协议规范: <https://modelcontextprotocol.io/>
- 78/xiaozhi-esp32: <https://github.com/78/xiaozhi-esp32>

## 当前服务状态 (handoff 写时)

- gbu-final 分支已 push 到 GitHub
- demo 录屏已完成 (user 自己保管)
- 物理: ESP32 已烧 H024 固件 (tool count = 14), 已连 user 手机热点
- shim 当前 (handoff 写时) 应是 hybrid 模式 8089, gateway 8645, mcp-endpoint-server 8004
  (如果你接手时这些都不在, 按 [docs/DEPLOY.md](../../DEPLOY.md) Part 7 重起)
