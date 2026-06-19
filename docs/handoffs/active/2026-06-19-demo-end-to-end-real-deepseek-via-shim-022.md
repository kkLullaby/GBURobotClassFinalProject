---
id: 2026-06-19-demo-end-to-end-real-deepseek-via-shim-022
from: planner
to: user
parent: 2026-06-19-m2-deepseek-backend-021
supersedes:
status: pending
created: 2026-06-19
artifacts:
  - ~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml
    (改：llm 提供商 base_url 指 shim:8089)
  - openai-shim 启动实例 (OPENAI_SHIM_BACKEND=deepseek + DEEPSEEK_API_KEY=... +
    HERMES_TRANSCRIPT_URL=http://localhost:8644/...)
  - hermes gateway run + webhook subscribe xiaozhi-transcript (HMAC 已知 secret)
  - ESP32 一次完整 voice 对话
---

## Why user-led

ADR-0005 主线机器侧全验证完毕：
- H018 SSE shim ✅
- H019 HermesBackend fork ✅ (5/5 mock 测)
- H020 真 Hermes 收 transcript + spawn agent ✅
- H021 DeepSeekBackend ✅ (4/4 mock 测)

**剩 1 步**：把 xinnan-tech server 的 LLM provider base_url 从 `api.deepseek.com`
切到本地 `shim:8089`，让 ESP32 voice 流过 shim → DeepSeek → 同时 fork 给
Hermes。这是 ADR-0005 实地 demo + Week 1 §1.4 验收终点。

这是 user-led：要 (a) ESP32 物理 + 耳朵听喇叭，(b) 真 DeepSeek API key
(planner 不持有), (c) 切 xinnan-tech config + restart。planner 可代跑 b/c
但 a 必须 user。**与 H016 互不阻塞**：H016 走 mcp_endpoint 反向 tool；H022
走 LLM provider base_url 正向。两条路同时跑也行，但 demo 答辩日只演 H022。

## Objective

把 H020+H021 mock 跑通的 fork 路径，**在真 ESP32 + 真 DeepSeek + 真 Hermes
session 下**演一次：

```
ESP32 麦克风 "我叫 kk"
    ↓ Opus → xinnan-tech server (FunASR)
    ↓ transcript "我叫 kk"
    ↓ server 用 openai SDK 调 base_url="http://127.0.0.1:8089/v1" 的 shim
        (DeepSeekBackend 接 api.deepseek.com)
        +
        (HermesBackend fork → POST http://127.0.0.1:8644/webhooks/xiaozhi-transcript)
    ↓ DeepSeek 流式回 "你好 kk, 很高兴认识你"
    ↓ shim SSE chunk 流回 server
    ↓ server TTS 朗读
    ↓ ESP32 喇叭
    ↓ 你听见

同时 (并行):
    Hermes session spawn → "XiaoZhi user said: 我叫 kk. Assistant replied: 你好 kk..."
    → hermes 收到 transcript → 进 session 历史
    → 你 hermes -c 看就能看到
```

## Constraints

- 不改 `openai-shim/` / `xiaozhi-mcp-adapter/` / `esp/` 任何代码
- 不动 H020 的 `~/.hermes/config.yaml` (webhook platform 已启)
- 真 DeepSeek API key **不**进 git；优先放 env 或 xinnan-tech `data/.config.yaml`
  (gitignored, 在仓库外)
- HMAC secret **不**进 git；shim 不签 HMAC → fork 仍会 401 (预期, 等 H023 修)
- ESP32 wifi 段必须能路由到主机 LAN IP；OTA URL 烧的是哪段就要在哪段
- 错误纪律：链路失败时按 stage 二分；每 stage 最多 2 修法

## Acceptance Criteria

- [ ] **Stage A** — xinnan-tech LLM provider 切到 shim：
      - 备份 `data/.config.yaml.bak.h022`
      - 改 `LLM.<provider>.base_url` 指 `http://<host-IP>:8089/v1`
        （where host-IP 是 docker 容器能访问到的主机 LAN，不是 0.0.0.0/127）
      - 改 `LLM.<provider>.api_key` = 任意值（shim 不校验）
      - 改 `LLM.<provider>.model_name` = `deepseek-chat`（或 shim 接的 model 名）
      - 重启 `docker compose restart xiaozhi-esp32-server`，等 8s
      - 日志含 `初始化组件: llm成功 ...` 不报错
- [ ] **Stage B** — 起 shim with full env：
      ```bash
      cd ~/code/robot_class/final_pro_xiaozhi_robot/openai-shim
      unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
      OPENAI_SHIM_BACKEND=deepseek \
        DEEPSEEK_API_KEY='<你的 deepseek key>' \
        HERMES_TRANSCRIPT_URL='http://127.0.0.1:8644/webhooks/xiaozhi-transcript' \
        /home/kk/miniconda3/bin/python -m uvicorn openai_shim.app:app \
          --host 0.0.0.0 --port 8089
      ```
      uvicorn 起来 + 显示 0.0.0.0:8089 (**不是** 127.0.0.1, docker 容器才能访问)
- [ ] **Stage C** — 起 hermes gateway (复用 H020 配置)：
      ```bash
      hermes webhook subscribe xiaozhi-transcript \
        --prompt 'XiaoZhi user said: {user}. Assistant replied: {assistant}.' \
        --description 'XiaoZhi end-to-end demo (H022)'
      # 记 secret (43 char) — 暂时存 /tmp/h022-env.sh
      hermes gateway run &
      ss -tln | grep 8644  # LISTEN
      ```
- [ ] **Stage D** — 直 curl smoke 验 shim → DeepSeek + → Hermes fork：
      ```bash
      curl -N -X POST http://127.0.0.1:8089/v1/chat/completions \
        -H "Authorization: Bearer fake" -H "Content-Type: application/json" \
        -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"用一句话介绍 ESP32"}],"stream":true}'
      # 期望: 流式 chunk，10-30 个，每个 5-50 字符；DeepSeek 真智能回复
      # shim log: 一行 hermes fork 401 (HMAC 未签, 预期)
      # hermes gateway log: 401 access log，但 server.websocket call 没问题
      ```
- [ ] **Stage E** — ESP32 voice 一轮对话：
      1. ESP32 boot, 连上同 LAN
      2. 对它说："**你好，介绍一下你自己**"
      3. 期望:
         - shim log 出 `POST /v1/chat/completions 200`
         - server log 出 `识别文本: 你好...` + `大模型收到用户消息`
         - 喇叭播放 DeepSeek 回复 (`echoed: ...` 不再出现; 是真智能回复)
         - hermes gateway log 出 `inbound message ... msg='XiaoZhi user said: 你好...'`
- [ ] **Stage F (gold)** — Hermes session 真存在：
      - `hermes sessions list` 多一个新 session
      - `hermes -c` (continue) 进去看，能看到 user/assistant pair
      - **你直接打 "我刚问了什么"** 给 hermes，它能答出 "你问了 ESP32 自我介绍"
        — 证明 transcript 真进 Hermes 上下文
- [ ] 写 ≤25 行 memo 贴 What I Did：
      - Stage A 改的 LLM provider 字段 (provider 名 + base_url 仍指 LAN IP)
      - Stage E 你说的话 + 你听到的回复 (前后各 30 字)
      - 主观端到端 RTT (按下说话到喇叭出声) vs H1b 基线 4-6s
      - Stage F hermes session id + 你随便问的第二轮问题 + Hermes 回答

## Context Pointers

- @docs/adr/0005-openai-compat-transcript-egress.md (主线动机)
- @docs/handoffs/archive/2026-06-19-m2-deepseek-backend-021.md (DeepSeekBackend
  + env 矩阵; 本 handoff 启 shim 用)
- @docs/handoffs/archive/2026-06-19-real-hermes-transcript-handshake-020.md
  (Hermes webhook subscribe 流程; 本 handoff 复用)
- @docs/handoffs/active/2026-06-19-mcp-endpoint-server-bringup-016.md
  (mcp_endpoint 反向通道；本 handoff **不依赖**，H016 已通就并行)
- @openai-shim/README.md §H021 DeepSeek Backend (env 矩阵参考)
- @.claude/memory/shared/global-commands.md (pyx / hermes / docker 命令)
- xinnan-tech `data/.config.yaml` LLM provider 字段：
  `LLM.<provider>: { url: ..., api_key: ..., model_name: ... }`
  改 `url` (而不是 `base_url` — 字段名要看实际 yaml)

## Out of Scope

- 不改 shim / adapter / 固件代码 (HMAC 待 H023)
- 不写 ESP32 → Hermes 反向通道 (Hermes 让机器人说话 → Week 3)
- 不实现 function-calling (Week 2)
- 不实现多 ESP32 / multi-session 复用
- 不实现 metrics / observability

## Candidate Root Causes（demo 跑不通时先查）

1. **shim --host 127.0.0.1 而 docker 访问不到** — 必须 `--host 0.0.0.0`
   或 `--host <LAN IP>`；`localhost` 在容器内是容器本身
2. **xinnan-tech config 字段名错** — 上游 LLM provider 字段可能是 `url`
   不是 `base_url`；不是 `model` 是 `model_name`。**先 grep 现有
   config 看实际 schema**
3. **shim 不接 OpenAI 标准 `/v1/chat/completions` URI** — 我们写的是
   `POST /v1/chat/completions`；xinnan-tech 拼 `base_url + /chat/completions`
   所以 base_url 应是 `http://host:8089/v1`（带 /v1）
4. **DeepSeek API key 失效 / 配额耗尽** — shim log 会显式 401/429；
   `curl https://api.deepseek.com/chat/completions -H "Authorization: Bearer $KEY"`
   sanity check
5. **shim hermes fork 401 阻塞 SSE** — H019 设计已 fire-and-forget，
   不会阻塞；但 log 会刷
6. **ESP32 boot 不去 OTA / 用编译时硬编码 URL** — sdkconfig CONFIG_OTA_URL
   烧的什么就只能 hit 那个；当前 wifi 段必须能路由到
7. **xinnan-tech 缓存了旧 LLM 实例** — config 改完一定要 docker compose
   restart，不要 reload；首次 cold start LLM init ~30s

## Suggested Steps

```bash
# ──────── Stage A: 改 xinnan-tech LLM provider ────────
CONFIG=~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml
cp $CONFIG ${CONFIG}.bak.h022

# 先看现有 LLM provider 是哪个 + 字段名
grep -B2 -A10 -E '^LLM:|^selected_module:' $CONFIG | head -40

# 假设当前 LLM provider 是 DeepSeekLLM:
HOST_IP=$(ip -4 addr show wlp0s20f3 | grep inet | awk '{print $2}' | cut -d/ -f1)
echo "host LAN IP: $HOST_IP"

# 用 yq 或手改 (yq 安全):
# yq -i ".LLM.DeepSeekLLM.url = \"http://$HOST_IP:8089/v1\"" $CONFIG
# 或 vi $CONFIG 手改：
#   LLM:
#     DeepSeekLLM:
#       url: http://10.x.x.x:8089/v1    # ← 改这里
#       api_key: 'fake-shim-doesnt-care'
#       model_name: 'deepseek-chat'

grep -A5 'DeepSeekLLM:' $CONFIG | sed 's|sk-[a-zA-Z0-9_-]*|<KEY>|'

# 重启
cd ~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server
docker compose restart xiaozhi-esp32-server
sleep 10
docker logs xiaozhi-esp32-server 2>&1 | tail -20 | grep -iE 'llm|error'

# ──────── Stage B: 起 shim ────────
cd ~/code/robot_class/final_pro_xiaozhi_robot/openai-shim
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
OPENAI_SHIM_BACKEND=deepseek \
  DEEPSEEK_API_KEY='sk-...' \
  HERMES_TRANSCRIPT_URL='http://127.0.0.1:8644/webhooks/xiaozhi-transcript' \
  /home/kk/miniconda3/bin/python -m uvicorn openai_shim.app:app \
    --host 0.0.0.0 --port 8089
# tab 留着，看 access log

# ──────── Stage C: hermes ────────
hermes webhook subscribe xiaozhi-transcript \
  --prompt 'XiaoZhi user said: {user}. Assistant replied: {assistant}. Please briefly acknowledge.' \
  --description 'H022 end-to-end demo'
# 记 secret 到 /tmp/h022-env.sh
hermes gateway run > /tmp/h022-gateway.log 2>&1 &

# ──────── Stage D: smoke ────────
curl -N -X POST http://127.0.0.1:8089/v1/chat/completions \
  -H "Authorization: Bearer fake" -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"用一句话介绍 ESP32"}],"stream":true}'

# ──────── Stage E: ESP32 ────────
# 对它说话，看 3 tab logs

# ──────── Stage F: hermes 续 ────────
hermes sessions list | head -5
SESSION=<那个 id>
hermes -c $SESSION
# 在 TUI 里打 "我刚问了什么"
```

## Recovery

| 症状 | 修 |
|---|---|
| shim curl 200 OK 但 docker 访问 8089 timeout | shim --host 改 0.0.0.0；防火墙 `sudo iptables -L | grep 8089` |
| docker logs 报 OpenAIError 401 | shim 不校验 auth, 但 DeepSeek 真 key 错 → 看 shim log 的 fork+real 调用 |
| DeepSeek 返回但 server 解析 stream 失败 | shim sse.py 字段 vs xinnan-tech 期望; 看 server log "解析" |
| TTS 失败 (上次见过 Edge TTS connect host fail) | 切 TTS provider；或等几秒重试 |
| ESP32 ASR 识别错字 ("小子"/"小智") | 不影响 demo，是 baseline 已知 |
| hermes session 没新 (fork 全 401) | 等 H023 加 HMAC; 不阻塞 demo 主路径 |

## For Auditor

不发 auditor。完整 batch (H016+H020+H022+H023) 后 demo 答辩前两天一起 review。

## Open Questions for Planner

- demo 答辩 PPT 需要 1 张图把整条链路画清楚——给 designer agent 起
- 录屏 / 备用录像：建议 demo 当天前一晚跑一次完整 H022 录屏当 fallback
- 真 deepseek API 费用：单轮对话 ~500 token in + ~200 out × $0.27/$1.1 per
  1M = $0.0002/轮。100 轮 demo ~2 美分，可控
- Hermes session id ↔ ESP32 device_id 还没 map（每次 fork 都新 chatcmpl
  uuid）。Week 1.5 任务，要做
