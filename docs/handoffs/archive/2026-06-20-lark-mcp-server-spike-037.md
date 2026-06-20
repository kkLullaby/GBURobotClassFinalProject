---
id: 2026-06-20-lark-mcp-server-spike-037
from: planner
to: user
parent: 2026-06-20-next-agent-bootstrap-036
status: done
created: 2026-06-20
artifacts:
  - lark-mcp-server/ (新增独立 Python 包)
  - docs/adr/0008-lark-mcp-server-integration.md
---

## Objective

落地 ottagent 下一阶段的"飞书 channel": 让 voice → hermes-z → 飞书 OpenAPI tool
真发出消息。第一期只 1 个 tool (`lark_send_message_to_self`),跑通端到端,后续
calendar/wiki/docs 同模式扩展。

## What planner did (代码侧已完成)

| File | 行数 | 状态 |
|---|---|---|
| `lark-mcp-server/pyproject.toml` | 32 | ✅ |
| `lark-mcp-server/src/lark_mcp/client.py` | ~140 | ✅ token cache + open_id lookup + send |
| `lark-mcp-server/src/lark_mcp/main.py` | ~100 | ✅ stdio MCP server wiring |
| `lark-mcp-server/src/lark_mcp/smoke.py` | ~40 | ✅ 单跑验证脚本 |
| `lark-mcp-server/src/lark_mcp/tools/send_message.py` | ~30 | ✅ |
| `lark-mcp-server/tests/test_send_message.py` | ~140 | ✅ 8/8 PASS |
| `lark-mcp-server/README.md` | ~110 | ✅ |
| `docs/adr/0008-lark-mcp-server-integration.md` | ~80 | ✅ |

**pytest**: `8/8 PASS in 0.20s` (respx mock,covers token / cache / 4 error path / content schema / from_env)

## What user needs to do

### Phase 1 — 飞书后台 (~10 min, you doing now)
- [x] 创建企业自建应用 `ottagent`
- [x] 申请权限: `im:message` + `im:message:send_as_bot` + `contact:user.id:readonly`
- [x] 申请发布 + 管理员同意
- [x] 拿 App ID / App Secret / mobile = (user 手机号,真值在 ~/.config/lark-mcp/.env)

### Phase 2 — 写 .env + smoke 验
```bash
# 1. 创建 .env (path 已固定到 ~/.config/lark-mcp/.env)
mkdir -p ~/.config/lark-mcp
cat > ~/.config/lark-mcp/.env <<'EOF'
LARK_APP_ID=cli_xxx              # ← 你的 App ID
LARK_APP_SECRET=xxx              # ← 你的 App Secret
LARK_USER_MOBILE=13xxxxxxxxx     # ← 你的手机号
LARK_HOST=https://open.feishu.cn
EOF
chmod 600 ~/.config/lark-mcp/.env

# 2. 装包
cd /home/kk/code/robot_class/final_pro_xiaozhi_robot/lark-mcp-server
UV_CACHE_DIR=/tmp/uv-cache uv pip install --system -e '.[test]'

# 3. smoke (绕过 MCP, 直接验飞书凭证有效)
unset ALL_PROXY all_proxy   # 防 httpx socks scheme 报错
pyx -m lark_mcp.smoke "ottagent 自检: 这是机器人发来的消息"
# 期望: 飞书 ottagent app 给你私聊一条 "ottagent 自检: ..."
# 输出: OK message_id=om_xxx open_id=ou_xxx
```

### Phase 3 — 接入 hermes
```bash
hermes mcp add lark \
  --command pyx \
  --args '-m,lark_mcp.main' \
  --env-file ~/.config/lark-mcp/.env

hermes mcp list   # 应见 lark

# 非 voice 验
hermes -z "调用 lark_send_message_to_self 发 'hermes 测试 from -z'"
# 期望: 飞书私聊收 "hermes 测试 from -z"
```

### Phase 4 — voice 端到端 (高光)
```bash
# 确认 ottagent 主链路全在
docker ps --filter name=xiaozhi-esp32-server
docker ps --filter name=mcp-endpoint-server
curl -sS http://localhost:8089/healthz

# 释放 mcp_endpoint slot (bitter lesson #32)
pkill -9 -f xiaozhi_mcp_adapter || true

# 对机器人讲: "你好小智, 给我发个飞书消息说一切正常"
# 期望:
# 1. shim 判定 chat → route=hermes_agent
# 2. hermes-z 看见 lark tool → tool_call → 飞书私聊到达
# 3. hermes 总结 → 喇叭说 "已发送"
```

## Acceptance Criteria
- [ ] Phase 2 smoke: 手机收到 ottagent 自检消息
- [ ] Phase 3 hermes mcp list 见 lark
- [ ] Phase 3 hermes -z one-shot: 飞书收到消息
- [ ] Phase 4 voice 端到端: 飞书收到 + 喇叭说已发送

## Troubleshooting

| 现象 | 原因 | 解 |
|---|---|---|
| `ValueError: Unknown scheme for proxy URL socks://...` | shell 有 `ALL_PROXY=socks://` | `unset ALL_PROXY all_proxy` 或 `export NO_PROXY=open.feishu.cn` |
| smoke 报 `code=99991663` | App Secret 错 | 复查 .env, 用引号包 |
| smoke 报 `mobile xxx not found in tenant` | 缺 `contact:user.id:readonly` 权限或没发布 | 飞书后台权限管理重申 |
| smoke 报 `code=230001` | open_id 拿到但 receive_id 拒 | 应用没发布或不在企业内 |
| voice 测 hermes 不调 lark tool | hermes 看不见这个 MCP | `hermes mcp list`; `--env-file` 路径绝对 |
| voice 调舵机不动 | sidecar 抢 mcp_endpoint slot | `pkill -9 -f xiaozhi_mcp_adapter` |

## Out of Scope
- Lark 回调 (飞书 → 机器人): 留 H038 加 webhook plugin
- 其他 tool (calendar/wiki/docs/meeting_room): 留 H039+ 按模板扩
- Telegram/SMS channel: 见 H036 next-agent-bootstrap 候选 A1/A4

## Bitter lessons (本次新增)
- **#35**: httpx `AsyncClient()` 初始化即解析 ALL_PROXY,socks scheme 在 `Proxy(url)`
  内抛 `ValueError`。respx mock 救不了 (init 早于 mock). fix=conftest strip + 生产
  `NO_PROXY` 白名单。新写任何 httpx-based client 的项目 conftest 默认应 strip proxy envs。

## References
- @docs/adr/0008-lark-mcp-server-integration.md
- @docs/handoffs/archive/2026-06-20-next-agent-bootstrap-036.md (parent)
- @lark-mcp-server/README.md
- 飞书 OpenAPI: <https://open.feishu.cn/document>

---

## Completion (2026-06-20)

✅ **4/4 AC 全过**:
- Phase 2 smoke: 手机收到 ottagent 自检 ✅ (Merge.yaml fake-ip 修完后)
- Phase 3 hermes mcp list 见 lark ✅ (uv tool install --with 'hermes-agent[mcp]' 后)
- Phase 3 hermes -z one-shot: 飞书收到 message_id=om_x100b6c... ✅
- Phase 4 voice 端到端: voice "给我发个飞书消息说一切正常" → 飞书真到达 + 喇叭说已发送 ✅

### Bitter lessons absorbed (写进 ADR-0008)
- **#35**: httpx AsyncClient init 解析 ALL_PROXY, socks scheme 抛 ValueError, respx 救不了 → conftest strip
- **#36**: clash-verge fake-ip pool (28.0.0.0/8) 污染 DNS, feishu 域名解析到 fake IP → TLS 死. 全局解 = `~/.local/share/.../profiles/Merge.yaml` `prepend-rules` DIRECT feishu/larksuite/bytedance/deepseek
- **#37**: 国外代理出口连不到国内服务 (feishu), NO_PROXY 加 feishu.cn 反而坑 (强 direct 走 fake-ip)
- **#38**: `uv tool install hermes-agent` 默认装 base hermes,**不带 mcp extras** → 所有 MCP server disabled; 必须 `--force --with 'hermes-agent[mcp]'` 重装
- **#39**: `hermes mcp add --args` 是 variadic, `--args "-m lark_mcp.main"` 会被当 1 个 token, 必须 `--args -m lark_mcp.main` 两 token
- **#40**: hermes 起的 subprocess **看不见 bash interactive alias** (e.g. `pyx`), `--command` 必须绝对路径 `/home/kk/miniconda3/bin/python`
- **#41**: `hermes mcp test lark` 报 Connection closed 但实际 `hermes -z` 调用真通 — test 通道有时序 bug, 真路径才是 ground truth
- **#42**: voice 超时 = 双层 timeout (shim `HERMES_AGENT_TIMEOUT_S` + xinnan-tech `.config.yaml` openai LLM `timeout.read`), hermes cold spawn + DeepSeek + lark tool 一来回 ~30-60s, 两层都需 ≥120s

### Out of scope (留下一波)
- Lark 回调 (飞书 → 机器人 voice 触发): 留 H038 加 webhook plugin
- 其他 tool: calendar/today, meeting_room/book, wiki/search, docs/create — H039+ 按 send_message 模板扩 (~30 min/tool)
