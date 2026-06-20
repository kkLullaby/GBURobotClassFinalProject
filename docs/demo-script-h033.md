# Demo Script (H033 现实可演版) — 2026-06-20 实测

> **关系**: 这是 [demo-script.md](demo-script.md) 的 H033 落地版.
> 旧版是基于 ADR-0005 plugin webhook fork 的愿景脚本 (cron/cross-channel/screen 显字).
> 本版基于 ADR-0006 HermesAgentBackend 的 voice → hermes-z → tool → 喇叭真闭环,
> 今天可现演, 不依赖 demo-script.md 里仍待 polish 的部分.

**时长**: 5-7 min, 4 段 take, 每段 ≤90s
**核心主张**: 不是又一个智能音箱, 是把 Hermes Agent 装进了会动的桌面机器人
**实测于**: 2026-06-20 12:30 (T1 已录, T2-T4 待 user 录)

---

## 前置环境 (30 秒一次性起)

```bash
# 验热点 IP
ss -tln | grep -E ':(8000|8003|8004)\s'
curl -sS http://10.206.218.66:8003/xiaozhi/ota/

# 起三件套 (sidecar / shim / gateway)
pkill -9 -f 'uvicorn|hermes gateway'; sleep 3

cd ~/code/robot_class/final_pro_xiaozhi_robot/xiaozhi-mcp-adapter
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
nohup env PYTHONPATH=src \
  MCP_ENDPOINT='ws://10.206.218.66:8004/mcp_endpoint/mcp/?token=yOHez59gwSMTNMiWL9zY4A0hQ5teG6P0xwjESC0xPUc%3D' \
  /home/kk/miniconda3/bin/python -m uvicorn xiaozhi_mcp_adapter.proxy_http:app \
    --host 127.0.0.1 --port 8650 \
  > /tmp/h030bis/sidecar.log 2>&1 & disown

# DeepSeek key 从 docker 单一来源取 (bitter lesson #28)
DEEPSEEK_KEY=$(grep -E '^\s+api_key:' \
  ~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml \
  | head -1 | awk '{print $2}')

cd ../openai-shim
nohup env \
  OPENAI_SHIM_BACKEND=hermes_agent \
  HERMES_BIN=/home/kk/.local/bin/hermes \
  HERMES_AGENT_TIMEOUT_S=45 \
  HERMES_TRANSCRIPT_URL='http://127.0.0.1:8645/webhooks/xiaozhi-transcript' \
  HERMES_WEBHOOK_SECRET="$(cat /tmp/h028bis-secret.txt)" \
  PYTHONPATH=src /home/kk/miniconda3/bin/python -m uvicorn openai_shim.app:app \
    --host 0.0.0.0 --port 8089 \
  > /tmp/h030bis/shim.log 2>&1 & disown

cd ~
nohup hermes gateway run > /tmp/h030bis/gateway.log 2>&1 & disown
sleep 8

ss -tln | grep -E ':(8089|8645|8650)\s' && echo "三件套就绪 ✅"

# 启 ESP32 monitor (PPT 投影用, STT 文本可见)
cd ~/code/robot_class/final_pro_xiaozhi_robot/esp/xiaozhi-esp32
source ~/esp-idf-5.5.2/export.sh
idf.py -p /dev/ttyACM0 monitor
```

---

## Take 1 — "项目结构" (实测 ✅, 端到端 13s)

**讲稿** (镜头前):
> "这不是又一个智能音箱. 我对它讲话, 它真用我电脑上的工具帮我做事."

**对机器人讲**:
> "你好小智" → 等"叮" → **"帮我看看 final 文件夹里面有什么目录"**

**实测喇叭说** (2026-06-20 12:30:21):
> "final文件夹里有五个目录: docs文档、esp固件、hermes小智插件、
> openai-shim接口层、还有xiaozhi-mcp-adapter适配器"

**ESP32 monitor 日志** (PPT 镜头):
```
I (401350) Application: >> 帮我看看final文件夹里面有什么目录
I (421360) Application: << final文件夹里有五个目录
I (424170) Application: << docs文档、esp固件、hermes小智插件、
                          openai-shim接口层、还有xiaozhi-mcp-adapter适配器
```

**讲完点出**:
- 它真跑了 `ls` (shell tool), 不是死记
- 它用 hermes agent 自动决定调哪个 tool, 我没指定
- 全程零私有协议: OpenAI-compat shim + 标准 MCP + 标准 hermes channel

---

## Take 2 — "git 历史" (待录, ~15-20s)

**对机器人讲**:
> "你好小智" → **"用 git log 看看 final 文件夹最近三次提交"**

**预期喇叭说**:
> "最近三次提交是 H033 加 HermesAgentBackend 让语音真指挥 hermes, H031
> sidecar 真接 mcp endpoint pipe, H030 全链路通."

**讲完点出**:
- 同一个 voice 调出**不同 tool**: T1 是 shell, T2 还是 shell 但传 `git log`
- hermes agent 内部自己决定 — 我不用教它 git 是啥

---

## Take 3 — "读 README 摘要" (待录, ~20-25s)

**对机器人讲**:
> "你好小智" → **"读一下 final 文件夹的 README 告诉我项目目标"**

**预期喇叭说**:
> "项目要把 ESP32 OttoRobot 改造成 Hermes Agent 的第一具物理化身,
> 创新点在拓扑——零私有协议, 后端无关, 可作为 PR 贡献给 hermes 社区."

**讲完点出**:
- 这就是项目的 elevator pitch, **是机器人真读了 README 总结的**, 不是预录
- 演示了长文本 tool-call (filesystem.read), 不只是 shell.run

---

## Take 4 (可选) — "创造性任务" 数文件数

**对机器人讲**:
> "你好小智" → **"在 final 文件夹里, 数一下 docs 目录有几个 markdown 文件"**

**预期**:
> "docs 目录有 N 个 markdown 文件." (hermes 真跑 `find docs -name '*.md' | wc -l`)

---

## 录屏规范

- **镜头**: 机器人 + 电脑显示器 (ESP32 monitor 文本 + shim/sidecar log)
- **收音**: 喇叭中文清晰, 不要混入风扇/键盘声
- **段长**: 60-90s/段, 拼起 4-5 min
- **工具**:
  ```bash
  # ffmpeg 屏幕录 (含 pulse audio)
  ffmpeg -f x11grab -framerate 30 -i :0 \
         -f pulse -i default \
         -c:v libx264 -preset ultrafast -crf 22 \
         -c:a aac -t 90 \
         /tmp/demo-take${N}.mp4
  ```
- **不剪**: 一镜到底是"现场 demo"; 剪过就不是了

---

## 答辩 Q&A 准备 (3 个最常问)

### Q1 "为什么不直接用 DeepSeek API 写一个语音助手?"
A: 那只是 voice → 1 个模型. 我们要的是 voice → agent (有 tool, 有 memory,
有 cron, 有跨 channel) → 多模型. 机器人是 channel, 不是终端.

### Q2 "Hermes Agent 已支持 Discord/Slack, 为什么再加 ESP32?"
A: 因为 ESP32 → 物理世界. Discord 给桌面用户, 桌面用户已经有键盘. 物理
机器人是为了把 agent 带到没键盘的场景 (车里、厨房、孩子房间).

### Q3 "和小爱同学/天猫精灵的区别?"
A: 那些是私有协议绑死后端. 我们这条链 (OpenAI-compat + MCP + hermes channel)
全开放, 后端 LLM 可换 (DeepSeek/Claude/Ollama/Nous Portal), tool 可装
(filesystem/browser/任何 MCP server). 一次写就跨平台贡献给 hermes 社区.

---

## 实测数据 (PPT 数据页)

| 指标 | 值 |
|---|---|
| ESP32 固件 | xiaozhi.bin 3.69 MiB, 11% 余量 |
| MCP tool 总数 | 14 (12 上游 + 2 H024 加: show_emoji + show_text) |
| Voice → 喇叭端到端 | T1 实测 ~13s ("项目结构" + ls), 预期 T3 ~25s (README 读) |
| 服务进程数 | 5 docker (mcp-endpoint + xiaozhi-server + ...) + 3 host (shim + sidecar + hermes gateway) |
| 自写代码总量 | M1 ~600 LOC + M2 ~500 + M3 plugin ~250 + M4 ~70 = ~1.4k LOC |
| Bitter lessons | 29 条 (Week 0-3, 全归档到 retros) |

---

## 录屏前 checklist

- [ ] 手机热点开着, ESP32 + 电脑都连了
- [ ] docker server config `websocket: ws://<新热点 IP>:8000/xiaozhi/v1/`
- [ ] 三件套 (sidecar 8650 + shim 8089 + gateway 8645) 全 LISTEN
- [ ] shim env `OPENAI_SHIM_BACKEND=hermes_agent` 正确:
      `PID=$(pgrep -f openai_shim.app) && tr '\0' '\n' < /proc/$PID/environ | grep SHIM`
- [ ] ESP32 boot log 有 `客户端设备支持的工具数量: 14`
- [ ] 网络: unset all proxies (`echo $HTTP_PROXY` 应为空)
- [ ] hermes gateway 没 hit "Unauthorized user" (env 有 `GATEWAY_ALLOW_ALL_USERS=true`)
