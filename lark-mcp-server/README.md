# lark-mcp-server

MCP server exposing Lark / Feishu OpenAPI as tools for Hermes Agent — part of the [ottagent](../README.md) project.

> 让 hermes 能调飞书 OpenAPI,从而让机器人 voice → "给我发个飞书消息说 X" → 真发出去。

## 当前 tool

| name | 干什么 | 状态 |
|---|---|---|
| `lark_send_message_to_self` | 给应用 owner 的飞书私聊发文本消息 | ✅ done |

后续(参见 [ROADMAP](../ROADMAP.md)): `lark_list_calendar_today` / `lark_book_meeting_room` / `lark_search_docs` / ...

## 装

```bash
cd lark-mcp-server
UV_CACHE_DIR=/tmp/uv-cache uv pip install --system -e '.[test]'
pyx -m pytest -xvs tests/       # 8/8 PASS in <1s
```

## 配凭证

### Step 1 — 申请飞书自建应用

1. 打开 <https://open.feishu.cn/> → 开发者后台 → 创建企业自建应用
2. 应用名: `ottagent`(随便起)
3. 左侧 **凭证与基础信息** → 拿 `App ID` (`cli_xxx`) 和 `App Secret` (32 字符)
4. 左侧 **权限管理** → 申请并发布:
   - `im:message`
   - `im:message:send_as_bot`
   - `contact:user.id:readonly`
5. 左侧 **版本管理与发布** → 创建版本 1.0.0 → 申请线上发布(需企业管理员同意)

> ⚠️ 必须是企业版 + 你和接收者在**同一企业**内,否则 `batch_get_id` 查不到 open_id。
> 个人版 / 跨企业请见后续路线 (B2: webhook 机器人,免审核但能力弱)。

### Step 2 — 写 `.env`

```bash
mkdir -p ~/.config/lark-mcp
cat > ~/.config/lark-mcp/.env <<'EOF'
LARK_APP_ID=cli_粘贴你的App_ID
LARK_APP_SECRET=粘贴你的App_Secret
LARK_USER_MOBILE=13xxxxxxxxx
LARK_HOST=https://open.feishu.cn
EOF
chmod 600 ~/.config/lark-mcp/.env
```

国际版 Lark Suite 用户改:
```
LARK_HOST=https://open.larksuite.com
```

### Step 3 — 单跑验证 (smoke)

```bash
pyx -m lark_mcp.smoke "ottagent 自检: 这是我的机器人发来的消息"
# 期望: 飞书 app 给 LARK_USER_MOBILE 这台手机的飞书账号发一条私聊
# 输出: OK message_id=om_xxx open_id=ou_xxx
```

如失败:
- `code=99991663`: app_secret 错
- `mobile xxx not found in tenant`: 手机号没在该企业里,或缺 `contact:user.id:readonly` 权限
- `code=230001`: open_id 拿到了但 receive_id 不被接受 → 应用没发布

## 接入 Hermes Agent

> ⚠️ 踩坑实录: hermes 的 MCP add 有 4 个非显然要求,踩齐 4 个才能 work。详见 ADR-0008 bitter lessons #38-#41。

```bash
# Step 0 — hermes 自身 venv 必须装 mcp extras 否则 MCP server 全被标 disabled
uv tool install --force --with 'hermes-agent[mcp]' hermes-agent

# Step 1 — 加载 .env 到 shell 让下面变量展开
set -a; source ~/.config/lark-mcp/.env; set +a

# Step 2 — add (注意 3 个坑: ① 绝对路径不能 alias ② --args 空格分不能逗号串 ③ --env 不是 --env-file)
hermes mcp add lark \
  --command /home/kk/miniconda3/bin/python \
  --args -m lark_mcp.main \
  --env LARK_APP_ID="$LARK_APP_ID" \
        LARK_APP_SECRET="$LARK_APP_SECRET" \
        LARK_USER_MOBILE="$LARK_USER_MOBILE" \
        LARK_HOST="$LARK_HOST" \
        LARK_ENV_FILE="$HOME/.config/lark-mcp/.env"

# Step 3 — 验
hermes mcp list   # 应见 lark (即使 Status 标 disabled 也能调,见 bitter lesson #41)

hermes -z "请调用 lark_send_message_to_self 工具,text 参数填 'hermes 测试'"
# 期望: 飞书收到 "hermes 测试" + 终端打印 message_id=om_xxx
```

## voice 验 (端到端 ottagent demo)

确保 ottagent 全链路在跑:

```bash
docker ps --filter name=xiaozhi-esp32-server    # LISTEN
docker ps --filter name=mcp-endpoint-server      # LISTEN
curl -sS http://localhost:8089/healthz           # shim hybrid 模式
pkill -9 -f xiaozhi_mcp_adapter || true          # 释放 mcp_endpoint slot (bitter lesson #32)
```

**双层 timeout 必须先调大**(bitter lesson #42):

```bash
# 1. shim subprocess timeout (hermes cold spawn + lark tool 一来回 ≈ 30-90s)
pkill -f 'openai_shim.app:app'
HERMES_AGENT_TIMEOUT_S=300 /home/kk/miniconda3/bin/python -m uvicorn \
  openai_shim.app:app --host 0.0.0.0 --port 8089 --log-level info \
  > /tmp/shim.log 2>&1 &

# 2. xinnan-tech 调 shim 的 LLM provider timeout (在 data/.config.yaml 你的 shim LLM 块下):
#   timeout:
#     read: 300
#     connect: 5
#     write: 10
#     pool: 5
# 改完 docker compose restart 重启
```

对机器人讲:
> "你好小智,给我发个飞书消息说一切正常"

期望:
1. shim 路由判定为 chat (不是 motor) → `[hybrid] route=hermes_agent`
2. hermes-z 看到 lark tool,生成 `tool_calls=[{name:lark_send_message_to_self, arguments:{text:"一切正常"}}]`
3. tool 真调,飞书私聊到达 (~30-60s)
4. hermes 总结成 "已发送" → 喇叭真说

✅ **实测通过** 2026-06-20 (H037)

## 已知限制 / 后续

- **企业版限定**:个人订阅号 + 跨企业 N/A → 后续 fallback 路线见 [docs/adr/](../docs/adr/)
- **未来加 tool**:calendar/today、meeting_room/book、wiki/search、docs/create。每个都是 `tools/<name>.py` + 在 `main.py` 注册 + 5 个 mock test。
- **回调侧 (飞书→机器人)** 暂不支持。需要再写一个 hermes plugin 接 Lark webhook 事件。

## License

MIT. See [LICENSE](../LICENSE).
