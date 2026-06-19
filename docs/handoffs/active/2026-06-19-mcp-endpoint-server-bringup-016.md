---
id: 2026-06-19-mcp-endpoint-server-bringup-016
from: planner
to: user
parent: 2026-06-19-m1-spike-echo-tool-015
supersedes:
status: pending
created: 2026-06-19
artifacts:
  - ~/code/xinnan-tech/mcp-endpoint-server/ (clone + docker compose)
  - ~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml (加 mcp_endpoint 字段)
  - 2 个 endpoint URL 的 token / port memo
---

## Why user-led

ADR-0003 类型 II：要 docker daemon + 拿 LAN IP + 改仓库外 server config + 重启。
跟 H011 同模式。Planner main-loop **可以**代跑，但你**已经在主终端**且能直接观察 logs，
快 5 分钟。

## Objective

让 M1 spike (H015 echo tool round-trip) 真的从 mock WS 升级到**真 xinnan-tech
8004 mcp_endpoint 子服务**，并且通过 ESP32 端的语音"叫 echo 工具"触发完整链路：

```
ESP32 (语音) → xinnan-tech server (port 8000) → LLM thinking 决定调 echo
        → 通过 mcp_endpoint (port 8004) 反向调 M1 pipe
        → echo_tool stdio process 回包
        → LLM 把结果朗读 → ESP32 喇叭
```

## Constraints

- 不动 `xiaozhi-mcp-adapter/` 任何代码（M1 spike 已 PASS，本任务**只**用它跑通真链路）
- 不改 ESP32 固件（已在 H1b 烧到 LAN server，复用）
- 不引入 token / api key 到 git 跟踪文件
- 不动其它 docker 容器（voice-agent-pg / n8n 等）
- 错误处理纪律按 H010 §Error-handling discipline
- monitor 看到一轮对话 ok 立刻退出（不要 monitor 跑整夜）

## Acceptance Criteria

- [ ] `~/code/xinnan-tech/mcp-endpoint-server/` clone 完成（git log 留 1 行 commit）
- [ ] `docker compose up -d` 起 `mcp-endpoint-server` 容器，`docker ps` 含其 Status=Up
- [ ] `ss -tln | grep :8004` 显示 LISTEN
- [ ] 从 `docker logs mcp-endpoint-server` 抽出 2 个 URL：
      - 智控台 endpoint：`http://<container-ip>:8004/mcp_endpoint/health?key=<...>`
      - 单模块 endpoint：`ws://<container-ip>:8004/mcp_endpoint/mcp/?token=<...>`
      - **替换 `<container-ip>` 为你的 LAN IP**（H1b 用过的 `10.206.218.66` 或当前主机连热点的 IP）
- [ ] 浏览器 / curl 访问"智控台 endpoint"返回 JSON
      `{"result":{"status":"success","connections":{...}},"jsonrpc":"2.0"}` (或近似)
- [ ] xiaozhi-server `data/.config.yaml` 末尾加 `mcp_endpoint: ws://<host-ip>:8004/...?token=<...>`，
      重启 `docker compose restart xiaozhi-esp32-server`
- [ ] xiaozhi-server logs 出现 `mcp接入点是  ws://<...>` 行（含真实 token，**不**贴 memo 里）
- [ ] 主终端跑：
      ```bash
      cd ~/code/robot_class/final_pro_xiaozhi_robot/xiaozhi-mcp-adapter
      MCP_ENDPOINT='ws://<host-ip>:8004/mcp_endpoint/mcp/?token=<...>' \
        /home/kk/miniconda3/bin/python -m xiaozhi_mcp_adapter.pipe
      ```
      logs 出现 `connected to MCP endpoint:` + 收到 `initialize` 后没崩
- [ ] ESP32 上对机器人说："**调用 echo 工具，参数 hi**"（或类似让 LLM 走 tool 路径的话），
      M1 pipe logs 出现 `tools/call` echo + result `echoed: hi`
- [ ] xiaozhi-server logs 同时含 `tools/call` 的成功 result
- [ ] ESP32 喇叭把 LLM 的回复朗读出来（含 "echoed: hi" 或 LLM 解释这段的话）
- [ ] 写 ≤15 行 memo 贴回 What I Did：
      - container IP / host IP / port (8004 是否冲突)
      - mcp_endpoint URL 的 port + path (不贴 token)
      - ESP32 实际说的话 + LLM 选不选 echo tool（这个有不确定性）
      - 主观感受：tool round-trip 加的延迟（vs H1b baseline 的 4-6s）

## Context Pointers

- @docs/handoffs/archive/2026-06-19-m1-spike-echo-tool-015.md (H015 done，M1 spike 已 PASS)
- @docs/handoffs/archive/2026-06-19-xinnan-docker-bringup-user-011.md (server bringup
  模板；本 handoff 是它的子服务延伸)
- @docs/handoffs/archive/2026-06-19-flash-baseline-to-local-server-h1b-013.md
  (LAN IP 套路 + server.websocket 改法)
- @docs/contracts/api/v1/esp32-to-server-handshake.md §4.3 (mcp_endpoint 协议)
- @docs/research-notes/xinnan-tech-openai-and-mcp.md §2 (握手序列细节)
- @.claude/memory/shared/global-commands.md §Python (pyx 别名 / pipe 启动命令)
- 上游 enable 文档：`~/code/xinnan-tech/xiaozhi-esp32-server/docs/mcp-endpoint-enable.md`
- 上游 integration 文档：`~/code/xinnan-tech/xiaozhi-esp32-server/docs/mcp-endpoint-integration.md`

## Out of Scope

- 不写 Hermes 集成（H017+）
- 不改 M1 pipe / echo_tool 代码（H015 已通）
- 不调 LLM prompt / system prompt（让 LLM 在 "调 echo 工具" 这种明示句下选 tool 是合理预期；
  LLM 偷懒不调 tool 不算 H016 失败，记 Open Question 给 planner）
- 不开 8002 / 不开智控台前端（minimal 路径，单模块部署即可）

## Suggested Steps

```bash
# ──────── Stage A: 部署 mcp-endpoint-server ────────
mkdir -p ~/code/xinnan-tech
cd ~/code/xinnan-tech
git clone --depth=1 https://github.com/xinnan-tech/mcp-endpoint-server.git
cd mcp-endpoint-server
git log -1 --format='%H %s' > /tmp/h016-commit.txt   # 记 commit

# 看 compose 文件
cat docker-compose.yml | head -30
docker compose up -d
sleep 5
docker logs mcp-endpoint-server 2>&1 | tail -30
# 期望看到：
#   ===下面的地址分别是智控台/单模块MCP接入点地址====
#   智控台MCP参数配置: http://172.x.x.x:8004/mcp_endpoint/health?key=<KEY>
#   单模块部署MCP接入点: ws://172.x.x.x:8004/mcp_endpoint/mcp/?token=<TOKEN>

# ⚠️ 上面的 172.x.x.x 是 container 内 IP，不可达。**替换成你主机的 LAN IP**
HOST_IP=10.206.218.66   # 你当前热点接的那个 IP（H1b 用的）
# 把日志里 ?key=<KEY> 和 ?token=<TOKEN> 替换出来：
KEY=$(docker logs mcp-endpoint-server 2>&1 | grep -oP 'health\?key=\K[^"\s]+' | head -1)
TOKEN=$(docker logs mcp-endpoint-server 2>&1 | grep -oP 'token=\K[^"\s]+' | head -1)
echo "智控台:  http://$HOST_IP:8004/mcp_endpoint/health?key=$KEY"
echo "M1 pipe: ws://$HOST_IP:8004/mcp_endpoint/mcp/?token=$TOKEN"

# 验智控台 endpoint
curl -sS "http://$HOST_IP:8004/mcp_endpoint/health?key=$KEY"
# 期望：{"result":{"status":"success","connections":{...}},...}

# ──────── Stage B: xiaozhi-server 配 mcp_endpoint ────────
CONFIG=~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml
cp $CONFIG ${CONFIG}.bak.h016

# 末尾加 mcp_endpoint 字段（如果已有就替换）
if grep -q '^mcp_endpoint:' $CONFIG; then
  sed -i "s|^mcp_endpoint:.*|mcp_endpoint: ws://$HOST_IP:8004/mcp_endpoint/mcp/?token=$TOKEN|" $CONFIG
else
  printf '\nmcp_endpoint: ws://%s:8004/mcp_endpoint/mcp/?token=%s\n' "$HOST_IP" "$TOKEN" >> $CONFIG
fi
grep -E 'mcp_endpoint' $CONFIG

# 重启 xiaozhi-server
cd ~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server
docker compose restart xiaozhi-esp32-server
sleep 8
docker logs xiaozhi-esp32-server 2>&1 | tail -20 | grep -E 'mcp接入点|MCP_endpoint|mcp_endpoint'
# 期望看到 mcp接入点是  ws://<...>

# ──────── Stage C: M1 pipe 真连 ────────
cd ~/code/robot_class/final_pro_xiaozhi_robot/xiaozhi-mcp-adapter
MCP_ENDPOINT="ws://$HOST_IP:8004/mcp_endpoint/mcp/?token=$TOKEN" \
  /home/kk/miniconda3/bin/python -m xiaozhi_mcp_adapter.pipe 2>&1 | tee /tmp/h016-pipe.log &
PIPE_PID=$!
sleep 3
grep -E 'connected to MCP endpoint' /tmp/h016-pipe.log    # 期望命中
# 不命中：docker logs mcp-endpoint-server 看反向连接情况

# ──────── Stage D: ESP32 端 voice 测试 ────────
# 1. ESP32 已经在 H1b 烧到 LAN server，开机连热点等就绪
# 2. 对它说："调用 echo 工具，参数是 hi" 或 "请使用 echo 工具回声 hi"
# 3. 监 pipe logs:
tail -f /tmp/h016-pipe.log | grep -E 'tools/call|echo'
# 期望：1-3 秒内出现 tools/call echo {"text":"hi"} + result "echoed: hi"

# 4. 监 server logs (另一终端):
docker logs xiaozhi-esp32-server 2>&1 | tail -50 | grep -E 'tool|echo|LLM'

# 5. 听喇叭：LLM 应该把 echoed: hi 朗读出来（或解释 "回声结果是 hi"）

# ──────── 收尾 ────────
kill $PIPE_PID
# 把上面 4 个 stage 的关键 log 行 + memo 贴回 What I Did
```

## Recovery

| 症状 | 可能原因 | 修 |
|---|---|---|
| `docker compose up -d` 报端口 8004 占用 | 旧 mcp-endpoint 或其它服务 | `docker ps | grep 8004`；不行就 compose 文件改 `18004:8004`，记进 memo |
| logs 出不来 KEY/TOKEN | 第一次启动还没 generate / 输出格式变了 | `docker logs mcp-endpoint-server` 全文搜 `token`/`key` |
| `mcp_endpoint` 配进去 server restart 后 logs 没出现 `mcp接入点是` | yaml 格式错（缩进 / 引号） | `cat` 重检；TOKEN 含 `=` 不影响，**不要**加引号 |
| M1 pipe 起来报 `websockets.exceptions.InvalidURI` | TOKEN 含特殊字符没 URL-encode | 一般无；如有，用 `urllib.parse.quote(TOKEN)` 包装 |
| pipe `connected` 后 ESP32 voice 调 tool 没反应 | LLM 没选 tool / function calling 没启 | server `data/.config.yaml` 看 `intent: function_call`（H011 已配）；如不在，加上重启 |
| LLM 调了但没 echoed 结果朗读 | TTS 把 raw text 当作 text-only 念了出来，可能就是想要的 | 听内容，含 "echoed" 关键字算成功 |

## For Auditor

不发 auditor。M1 真链路打通在 H017 (Hermes 集成) 完成后做集中 review。

## Open Questions for Planner

跑完贴 memo 时如果遇到：

- 8004 端口冲突 → port 改 18004，**回灌**到 [contract §4.3](../contracts/api/v1/esp32-to-server-handshake.md) +
  [shared/global-commands](../../.claude/memory/shared/global-commands.md)
- LLM 不主动调 echo tool → 记一条 Open Q 给 planner，回灌 ADR-0005 §Trade-off
  讨论"function_call 触发条件"
- mcp-endpoint-server 默认 token 是否 rotate / 持久化 → 影响 demo 长期可用
