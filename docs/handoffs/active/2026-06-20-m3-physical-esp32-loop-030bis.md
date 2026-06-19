---
id: 2026-06-20-m3-physical-esp32-loop-030bis
from: planner
to: user
parent: 2026-06-20-m3-end-to-end-demo-030
supersedes:
status: pending
created: 2026-06-20
artifacts:
  - 仓库外: ~/.hermes/.env (新, 含 unset proxy + ALLOW_ALL_USERS + XIAOZHI_* env)
  - 仓库外: M1 sidecar 接真 mcp_endpoint pipe (sidecar 启动时 _PIPE = pipe.connect)
  - 仓库外: /tmp/m3-demo-recording.mp4 (可选)
---

## Why now

H030 7/7 机器侧 ✅: 
- listener (8645) 真起, 收 HMAC POST 202
- Hermes 真 spawn session, DeepSeek 真处理 19.4s/3 api/72 char
- adapter.send 真调 sidecar (8650) URL+payload 正确
- sidecar 真接 POST, 返 500 因 `_PIPE = None` (M1 没接真 ESP32, **预期**)
- adapter try/except degraded ✅ 不阻塞 Hermes

剩下 **物理最后一公里** 2 项：
1. M1 sidecar 真接 xiaozhi mcp_endpoint pipe (sidecar 启动时 `_PIPE = await connect()`)
2. ESP32 voice 物理对讲 + 屏幕真显回复 + cron 真触发

跟 H013 / H022 / H020 同模式: planner 起 coach 远程指导 user 实操。

## Objective

跑通 M3 完整 4-stage demo 答辩素材:

A. **Voice → Display**: 对机器人说 "你好"，机器人屏幕显示 DeepSeek 真回复 (chat 区, 持久)
B. **TUI send → Display**: hermes TUI 主动 send → 机器人屏幕显字
C. **Cron → Display**: cron 2 分钟一次 → 屏幕弹 "ping"
D. (可选) 录屏 /tmp/m3-demo-recording.mp4 给答辩

## Stages

### Stage 0 (user 实测) — 装持久 env file

```bash
# 写一个 ~/.hermes/.env (Hermes 自己读, 也可 source 到 shell)
cat > ~/.hermes/.env <<EOF
# unset proxy (Week 0 bitter lesson #11/#23)
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

# XIAOZHI plugin 三件套
XIAOZHI_WEBHOOK_PORT=8645
XIAOZHI_WEBHOOK_HOST=127.0.0.1
XIAOZHI_DEVICE_ID=ac:a7:04:30:91:78
XIAOZHI_MCP_ADAPTER_URL=http://127.0.0.1:8650
XIAOZHI_WEBHOOK_SECRET=$(cat /tmp/h028bis-secret.txt)

# demo 期开 allow-all (production 走 platform allowlist)
GATEWAY_ALLOW_ALL_USERS=true
EOF
chmod 600 ~/.hermes/.env
```

### Stage 1 — M1 sidecar 真接 mcp_endpoint pipe (~10 min coding)

M1 的 `proxy_http.py` 目前 `_PIPE = None`, sidecar 启动时也不 connect。
要让它真发字到 ESP32, sidecar 启动时**必须**连一个 `xiaozhi_mcp_adapter.pipe`
实例并把它塞进 `_PIPE`。

两条路:

**路径 A (推荐, ~30 LOC)**: 在 sidecar 加 startup hook + 起 pipe coroutine

```python
# proxy_http.py 加:
import asyncio, os
from .pipe import connect as connect_pipe   # 假定 pipe.py 暴露此 api
from . import show_text_proxy

@app.on_event("startup")
async def _start_pipe():
    url = os.environ["MCP_ENDPOINT"]   # ws://<server>:8004/mcp_endpoint/mcp/?token=...
    pipe = await connect_pipe(url)     # 起 ws + 完成 hello/initialize
    show_text_proxy._PIPE = pipe       # module 全局变量替换
```

**路径 B (临时, ~3 行 shell)**: 起 `xiaozhi_mcp_adapter.pipe` standalone +
sidecar talk pipe via stdio. 但 stdio 跨 process 麻烦; 推荐 A.

→ 本 Stage 是 **真代码改动**, 走新 handoff **H031 (executor codex)**: 加
30 LOC + 1 pytest, sandbox-friendly. **本 H030.bis 不动代码**, 等 H031 done
后回这里继续 Stage 2-4.

### Stage 2 (Stage A) — Voice → Display (~5 min)

```bash
# Restart hermes gateway 读 ~/.hermes/.env
pkill -f 'hermes gateway' && sleep 3
hermes gateway run > /tmp/h030/gateway.log 2>&1 &

# 重启 shim 切到 plugin webhook (H028.bis Stage C 已设过, 此处复制)
pkill -f 'uvicorn openai_shim' && sleep 2
cd ~/code/robot_class/final_pro_xiaozhi_robot/openai-shim
nohup env \
  OPENAI_SHIM_BACKEND=deepseek \
  DEEPSEEK_API_KEY='<你的 key>' \
  HERMES_TRANSCRIPT_URL='http://127.0.0.1:8645/webhooks/xiaozhi-transcript' \
  HERMES_WEBHOOK_SECRET="$(cat /tmp/h028bis-secret.txt)" \
  /home/kk/miniconda3/bin/python -m uvicorn openai_shim.app:app --host 0.0.0.0 --port 8089 \
  > /tmp/shim.log 2>&1 & disown
sleep 3

# 起 M1 sidecar with MCP_ENDPOINT
cd ../xiaozhi-mcp-adapter
nohup env \
  MCP_ENDPOINT='ws://127.0.0.1:8004/mcp_endpoint/mcp/?token=...' \
  PYTHONPATH=src /home/kk/miniconda3/bin/python -m uvicorn \
  xiaozhi_mcp_adapter.proxy_http:app --port 8650 \
  > /tmp/h030/sidecar.log 2>&1 & disown
sleep 3

# 验所有 LISTEN
ss -tln | grep -E ':8004|:8089|:8645|:8650'
```

对机器人讲 "你好"
- xinnan-tech log: `识别文本: 你好`
- shim log: SSE delta + fork POST 8645 → 202
- hermes agent.log: `inbound message: platform=xiaozhi ... msg='XiaoZhi user said: 你好...'`
- hermes agent.log: `response ready: ... response=N chars`
- sidecar log: `call_show_text(device=ac:..., text=<回复>, kind=chat)`
- ESP32 屏幕: chat 区显 "<DeepSeek 回复>" ✅

### Stage 3 (Stage B) — TUI send → Display (~3 min)

```bash
hermes
# 在 TUI: /send xiaozhi:ac:a7:04:30:91:78 "看这里"
```

机器人屏幕弹 "看这里" ✅

### Stage 4 (Stage C) — Cron → Display (~5 min + 2 min wait)

```bash
hermes cron add --schedule '*/2 * * * *' --deliver xiaozhi --message 'ping'
# 等 2 min, 看屏幕弹 "ping" ✅
hermes cron list                # 看 next_fire
hermes cron remove <id>         # 验完删
```

### Stage 5 (可选) — 录屏

```bash
# OBS 或 ffmpeg 录 ESP32 屏幕 + hermes TUI + shim/gateway log
ffmpeg -f x11grab -i :0 -c:v libx264 -t 120 /tmp/m3-demo-recording.mp4
```

## Acceptance Criteria

- [ ] ~/.hermes/.env 写好, chmod 600
- [ ] H031 (M1 sidecar 真接 pipe) done
- [ ] Stage 2: voice → 屏幕真显 DeepSeek 回复
- [ ] Stage 3: TUI send → 屏幕真显字
- [ ] Stage 4: cron → 屏幕真触发
- [ ] What I Did 贴 Stage-by-Stage 实测日志
- [ ] (可选) 录屏

## Context Pointers

- @docs/handoffs/active/2026-06-20-m3-end-to-end-demo-030.md (Stage A/B 机器侧 ✅ + 真黄金证据)
- @docs/handoffs/archive/2026-06-20-m3-m1-proxy-and-real-send-029v2.md (M1 sidecar 设计原型)
- @docs/handoffs/archive/2026-06-19-mcp-endpoint-server-bringup-016.md (mcp_endpoint 起法 + token 拿)
- @docs/handoffs/archive/2026-06-19-demo-end-to-end-real-deepseek-via-shim-022.md (H022 实测 voice 路径)
- @xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/pipe.py (现有 pipe 实现)
- @xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/proxy_http.py (待 H031 加 startup hook)
- @.claude/memory/shared/global-commands.md §Hermes / §xinnan-tech

## Out of Scope

- TTS 让机器人**说话**而非显示 (架构限制, demo 用显示)
- 改本仓代码 (改动走 H031)
- 跨 channel routing (Week 3 §3.6)
- 真用户 demo 答辩剧本编排 (Week 4 polish)

## Recovery

| 症状 | 修 |
|---|---|
| H031 done 后 sidecar 启动仍 RuntimeError | pipe.connect 抛？看 mcp_endpoint 8004 有没起；token 失效 |
| voice 转脚后没 fork 到 8645 | shim env XIAOZHI_WEBHOOK_SECRET 必须跟 gateway 同源 |
| 屏幕没字 | M4 tool count 该 14；ESP32 boot 看 `客户端设备支持的工具数量: 14` |
| cron 没触发 | `hermes cron list` 看 next_fire 时间 + scheduler 健康 |

## For Auditor

H030 + H030.bis + H031 全 done 后 → **M3 batch auditor handoff (H032)**:
review M1 sidecar 真接 + M3 plugin + adapter + 端到端 demo;
按 rubric `docs/rubrics/m3-plugin-review.md` (planner 起 H032 前先写)

## Open Questions

- 屏幕显示长文本 (>30 字) 实际行为? (H028.ter design §7 留 H030 验)
- cron deliver=xiaozhi 是否 hermes 直接支持还是要 platform_registry 注册
  cron_deliver_env_var? (read ntfy adapter:register, 见 cron_deliver_env_var
  字段; XiaoZhi register 没设, 可能需补)
- 真答辩用哪 3 个 voice query? (H030.bis done 后写 docs/demo-script.md)
