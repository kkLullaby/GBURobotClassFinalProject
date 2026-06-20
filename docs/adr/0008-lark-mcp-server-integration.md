---
id: ADR-0008
title: lark-mcp-server — 把飞书 OpenAPI 暴露成 MCP tool 接入 hermes
status: active
date: 2026-06-20
supersedes: null
superseded_by: null
---

## Context

ADR-0007 hybrid router 已让 voice 路径分两路: motor → raw DeepSeek + ESP32 tools;
其余 → `hermes -z`。后者意味着只要往 hermes 注册新 MCP server,机器人就自动获得新能力,
**shim / xinnan-tech / ESP32 端零修改**。

用户下一阶段需求("加上和手机通信,通过工具连接飞书等一系列功能") = 给 hermes 加一个
**飞书 MCP server**,讲"给我发个飞书消息"就让机器人真发一条。

候选方案:
| ID | 方案 | 优 | 劣 |
|---|---|---|---|
| **B1 自建应用 + OpenAPI** (本 ADR) | 全功能 (im/calendar/wiki/docs) + 长期演进 | 需企业管理员审核 |
| B2 自定义机器人 webhook | 零审核 5 min 起 | 只能发不能收,无 tool 调用 |
| B3 个人 access token | 任何账号可用 | 飞书未开放给个人开发者 |

选 **B1**:用户是某企业管理员可走通,长期能扩 calendar/meeting_room/docs 等高价值 tool,
跟 ottagent "voice → tool-call → 真做事" 主张完全契合。

## Decision

新写独立 Python 包 `lark-mcp-server/` 暴露 stdio MCP server,通过 `hermes mcp add` 接入。

```
voice "发个飞书消息说一切正常"
    ↓ STT
    ↓ shim hybrid router → route=hermes_agent
    ↓ hermes -z PROMPT (--yolo --accept-hooks)
    ↓ hermes 看见 MCP tool `lark_send_message_to_self`
    ↓ tool_call → stdio → lark-mcp-server
        ↓ LarkClient (tenant_access_token 缓存)
        ↓ POST /im/v1/messages
    ↓ tool result: "OK message_id=om_xxx"
    ↓ hermes 总结口语化
    ↓ TTS → 喇叭说 "已发送"
```

## 实测覆盖

代码侧 (本 ADR 落地时):
- ✅ 8/8 pytest case PASS (respx mock,happy + 6 error path + 1 cache)
- ✅ stdio MCP server skeleton 编译通过 (`pyx -m lark_mcp.main` 可起)
- ✅ **物理 voice 实测 (2026-06-20)**: voice "给我发个飞书消息说一切正常" → docker server route=hermes_agent → hermes spawn → lark tool_call → 飞书私聊到达 + 喇叭说"已发送". H037 4/4 AC 全过.

## 配置面 / secrets

`~/.config/lark-mcp/.env` (chmod 600,**绝不**入 git):
```
LARK_APP_ID=cli_xxx
LARK_APP_SECRET=xxx
LARK_USER_MOBILE=13xxxxxxxxx
LARK_HOST=https://open.feishu.cn   # 国内版; Lark Suite 改 .com
```

hermes 接入 (**实测正确语法**, 见 bitter lesson #38-#40):
```bash
# 0. hermes 自身 venv 必须带 mcp extras
uv tool install --force --with 'hermes-agent[mcp]' hermes-agent

# 1. 加载 .env 到 shell 让下面变量展开
set -a; source ~/.config/lark-mcp/.env; set +a

# 2. add (注意: 绝对路径 + --args 空格分 + --env KEY=VAL)
hermes mcp add lark \
  --command /home/kk/miniconda3/bin/python \
  --args -m lark_mcp.main \
  --env LARK_APP_ID="$LARK_APP_ID" \
        LARK_APP_SECRET="$LARK_APP_SECRET" \
        LARK_USER_MOBILE="$LARK_USER_MOBILE" \
        LARK_HOST="$LARK_HOST" \
        LARK_ENV_FILE="$HOME/.config/lark-mcp/.env"
```

## Consequences

### Positive
- 新增 channel **不动**任何已有模块: shim / xinnan-tech / ESP32 / hybrid router / hermes core 全零改。
- 同一 stdio MCP server 模板可拷贝扩展 (calendar/wiki/docs),边际成本 ~30 min/tool。
- 答辩可演 voice → 飞书消息真到,跟 H033 查文件夹同一个高光基础。

### Negative
- **企业版限定**: 个人开发者 + 跨企业用户 N/A。后续 B2 webhook 路线可作 fallback。
- **审核延迟**: 应用要企业管理员同意,新人 onboard 不能秒跑。
- **socks proxy 兼容性**: httpx 默认读 `ALL_PROXY`,系统装了 socks proxy 会导致 init 崩。
  conftest 已 strip;生产环境用 `unset ALL_PROXY` 或 `NO_PROXY=open.feishu.cn` 解决。

### Bitter lessons absorbed
- **#35**: httpx `AsyncClient()` 初始化时即解析 `ALL_PROXY`,socks scheme 会
  在 `Proxy(url)` 抛 `ValueError: Unknown scheme`. respx mock 不能救,因 init 早于 mock
  生效。fix = 测试 conftest strip proxy env;生产用 `NO_PROXY` 白名单。
- **#36**: clash-verge fake-ip pool (28.0.0.0/8) 污染 DNS,feishu 域名解析到 fake IP →
  TLS 死。**全局解** = `~/.local/share/io.github.clash-verge-rev.clash-verge-rev/profiles/Merge.yaml`
  里加 `prepend-rules: DOMAIN-SUFFIX,feishu.cn,DIRECT` (+ larksuite/bytedance/deepseek),
  这个 merge 文件 overlay 所有 clash 订阅,持久生效。
- **#37**: 国外代理出口连不到国内 feishu。第一直觉把 feishu 加 `NO_PROXY` 反而坑 —
  强 direct 走 fake-ip 直接死。正解: clash 层 DIRECT 规则,shell `NO_PROXY` 只白名单
  那些代理触不到的真实 IP/loopback。
- **#38**: `uv tool install hermes-agent` 默认装 base hermes,**不带 mcp extras** → 所有
  MCP server 在 hermes 里被标 `disabled`,`hermes mcp test` 报 `requires 'mcp' Python SDK`。
  必须 `uv tool install --force --with 'hermes-agent[mcp]' hermes-agent` 重装。
- **#39**: `hermes mcp add --args` 是 variadic (`[ARGS ...]`),`--args "-m lark_mcp.main"`
  把整串当 1 个 token 传给 python(报 No such file),必须 `--args -m lark_mcp.main`
  两 token 空格分。同理 `--env` 是 variadic `KEY=VAL`,**没有** `--env-file` flag。
- **#40**: hermes spawn 的 subprocess 是 **非 interactive shell**,看不见你 `~/.bashrc`
  里的 `alias pyx=...`,只能用绝对路径 `/home/kk/miniconda3/bin/python`,否则 exit=127
  No such file or directory。
- **#41**: `hermes mcp test lark` 报 `Connection closed (7132ms)` 但实际 `hermes -z`
  调用真通(message_id 真返回)。test 通道 stdio handshake 有时序 bug,**真路径 (hermes -z)
  才是 ground truth**,disabled 标可忽略。
- **#42**: voice 端到端超时 = **双层 timeout**。① shim `HERMES_AGENT_TIMEOUT_S`
  (默认 60s); ② xinnan-tech `.config.yaml` openai LLM provider `timeout.read`
  (默认 60s 但用户配 45s)。hermes cold spawn + load MCP server + DeepSeek 第一 token +
  lark tool 一来回 ≈ 30-90s,两层都必须 ≥120s 才稳。修复路径:
  ```bash
  HERMES_AGENT_TIMEOUT_S=300 ... uvicorn ...
  # + xinnan-tech config: timeout: {read: 300, connect: 5, write: 10, pool: 5}
  ```

## Implementation
- `lark-mcp-server/pyproject.toml` (deps: mcp, httpx, python-dotenv)
- `lark-mcp-server/src/lark_mcp/client.py` (~140 LOC, token cache + open_id lookup + send)
- `lark-mcp-server/src/lark_mcp/main.py` (~80 LOC, stdio server + tool wiring)
- `lark-mcp-server/src/lark_mcp/smoke.py` (~40 LOC, 单跑验证脚本)
- `lark-mcp-server/src/lark_mcp/tools/send_message.py` (~30 LOC)
- `lark-mcp-server/tests/test_send_message.py` (8 case)
- `lark-mcp-server/README.md` (装 + 验 + hermes 接入步骤)

## References
- @docs/handoffs/active/2026-06-20-lark-mcp-server-spike-037.md (本次 handoff)
- @docs/adr/0007-hybrid-backend-router.md (前置,不被 supersede)
- @docs/adr/0006-hermes-agent-backend-voice-replace-llm.md
- 飞书 OpenAPI: <https://open.feishu.cn/document>
