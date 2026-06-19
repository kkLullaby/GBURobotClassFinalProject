---
id: 2026-06-19-real-hermes-transcript-handshake-020
from: planner
to: user
parent: 2026-06-19-m2-hermes-fork-transcript-019
supersedes:
status: done
created: 2026-06-19
artifacts:
  - ~/.hermes/config.yaml (改：platforms.webhook.enabled=true)
  - ~/.hermes/.env 或环境变量（WEBHOOK_ENABLED/WEBHOOK_PORT/WEBHOOK_SECRET）
  - hermes webhook subscribe xiaozhi-transcript（注册新 webhook）
  - openai-shim 运行实例（启动时 HERMES_TRANSCRIPT_URL 指向真 Hermes）
---

## Why user-led

H019 在 fake-hermes ASGI mock 下 5/5 PASS，但 Hermes 真 webhook 路径走的是
**`hermes gateway` 的内置 HTTP server**（不是任意 FastAPI），路由处理、HMAC
校验、agent spawn / `--deliver-only` 模板渲染都是 Hermes 内部 logic——pytest mock
无法覆盖。**必须真启 Hermes** 验一次握手才能算 ADR-0005 主线 done。

同时本 handoff 牵动 `~/.hermes/` 的真配置 + agent loop（会真烧 LLM token），
属于"对你的本地环境/账户有副作用"——按 ADR-0003 类型 I**默认归用户**。
Planner main-loop **可代跑**（除了听喇叭那一段），但你已经在主终端且能直接
看 `hermes gateway run` 的实时日志，更快。

跟 H016 同模式。

## Objective

让 H019 那条 fork 路径在**真 Hermes**下走通一次完整握手：

```
curl -X POST /v1/chat/completions      M2 openai-shim                       Hermes webhook gateway (port 8644)
  stream=true                            ├── echo SSE ────────→ curl 收 SSE   
  messages=[{user:"hi"}]                 └── HermesBackend POST              ┌──→ /webhooks/xiaozhi-transcript
                                            transcript payload ─────────────┤    (HMAC 校验 → render prompt template →
                                                                            │     spawn agent session 或 --deliver-only)
                                                                            └──→ logs/sessions/<id>/transcript.jsonl 出现一条
                                                                                  user="hi" / assistant="echoed: hi"
```

验证标准：**Hermes session/log/TUI 任意一处看见 "echoed: hi"** 即握手成功。

## Constraints

- 不改 `openai-shim/`、`xiaozhi-mcp-adapter/`、`esp/`、`docs/contracts/`、
  `docs/adr/`、`docs/handoffs/` 任何既有代码（除本 handoff 自身追加段）
- 不动 H016 起的 mcp-endpoint-server / xiaozhi-server docker
- 不写 ESP32 / 真 LLM provider 集成（H021/H022 才做）
- `~/.hermes/.env` **不进 git**（已有 .gitignore 兜底，再确认一遍）
- **关 proxy** 后再跑（H016 教训：`unset *PROXY` 或最少 `unset ALL_PROXY`）
- HMAC secret 不贴回 memo（**贴 secret 长度 + 前 4 char 即可**）
- 错误纪律：M2 fork 失败 / Hermes webhook 404 / HMAC 不通 → 各自最多试 2 修
  法，超出 status: blocked + 完整日志

## Acceptance Criteria

- [ ] **Stage A** — 配 Hermes webhook platform：
      - 跑 `hermes webhook list` 见到提示后，按提示之一启用 webhook (推荐
        `hermes gateway setup` 走 wizard；或手工改 `~/.hermes/config.yaml`)
      - `~/.hermes/config.yaml` 含 `platforms.webhook.enabled: true` + port
      - 记下：`HOST_PORT` (default 8644), `SECRET` (auto-gen 也行)
- [ ] **Stage B** — 起 Hermes gateway + 注册 webhook：
      - `hermes gateway run` 在一个 tab 跑（前台，看实时 log）；日志含
        `Webhook listener on 0.0.0.0:8644` 或类似
      - 另一 tab：`hermes webhook subscribe xiaozhi-transcript \
            --prompt 'XiaoZhi user said: {user}. Assistant replied: {assistant}.' \
            --description 'XiaoZhi robot transcript ingress (H020)' \
            --deliver-only --deliver log`
        (`--deliver log` 走 0-cost path，不烧 LLM token，**先验路径**)
      - `hermes webhook list` 看到 `xiaozhi-transcript` 在列
- [ ] **Stage C** — 起 openai-shim 指向真 Hermes：
      ```bash
      cd ~/code/robot_class/final_pro_xiaozhi_robot/openai-shim
      unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
      HERMES_TRANSCRIPT_URL='http://localhost:8644/webhooks/xiaozhi-transcript' \
      /home/kk/miniconda3/bin/python -m uvicorn openai_shim.app:app --port 8089
      ```
      uvicorn 起来等就绪
- [ ] **Stage D** — 触发一次完整 round-trip：
      ```bash
      curl -N -X POST http://localhost:8089/v1/chat/completions \
        -H "Authorization: Bearer fake" -H "Content-Type: application/json" \
        -d '{"model":"echo","messages":[{"role":"user","content":"hi"}],"stream":true}'
      ```
      `data: {...content:"echoed: hi"...} ... data: [DONE]` 收到
- [ ] **Stage E** — 验 Hermes 那侧确实收到：
      - Hermes gateway tab 出现 `POST /webhooks/xiaozhi-transcript 200 OK`
        或类似 access log
      - `--deliver log` 模式下，Hermes 输出（或 `~/.hermes/logs/` 下某 log）
        渲染出 `XiaoZhi user said: hi. Assistant replied: echoed: hi.`
      - **如果**走真 agent 模式（不加 `--deliver-only`）：`hermes sessions list`
        会多一个新 session，`hermes sessions show <id>` 可见 user/assistant
        message
- [ ] **Stage F (可选)** — HMAC 验证：若 webhook 启了 secret，shim 的 POST
      未签 HMAC，Hermes 该 403/401。这是 H019 留的功能空白——验证它**确实**
      403，记 Open Q 给 planner 决定 H021/H022 是否补 HMAC
- [ ] 写 ≤15 行 memo 贴回 What I Did：
      - webhook port + secret 长度 (不贴 secret)
      - hermes gateway 启动到 webhook listener 实际多久（首次冷启可能 5-30s）
      - Stage E 的渲染文字（应该一字不差含 echoed: hi）
      - **可选**：把 deliver target 换成你的某个 telegram/discord chat，让
        机器人回声真打到手机；写一句感受

## Context Pointers

- @docs/adr/0005-openai-compat-transcript-egress.md (**先读** — 本 handoff
  是 ADR-0005 实地落地的最后一公里；H019 已搞机制，本 handoff 验真)
- @docs/handoffs/archive/2026-06-19-m2-hermes-fork-transcript-019.md (H019
  done — HermesBackend 实现 + fake-hermes 测；本 handoff 在真 Hermes 上重测)
- @openai-shim/src/openai_shim/hermes_backend.py (POST payload schema：
  `{user, assistant, model, session, timestamp_unix}`)
- @openai-shim/README.md §H019 Hermes Fork (env 变量名 + 示例)
- @.claude/memory/shared/global-commands.md §Hermes (hermes CLI 速查)
- Hermes webhook 文档（如果上游有的话）：`hermes webhook subscribe --help`
  + `hermes gateway --help` 已贴过
- H016 unblock 段（proxy 教训）：
  @docs/handoffs/active/2026-06-19-mcp-endpoint-server-bringup-016.md
  §Planner Unblock §Stage C

## Out of Scope

- 不写真 LLM backend（H021 才做）
- 不连 ESP32 / 不开 xinnan-tech 那条链路（H022 才合一）
- 不写 ESP32 → Hermes 的**反向**通道（Hermes 想让机器人说话 → ESP32 朗读）
  — 这是 Week 3 的事
- 不实现 HMAC 签名于 shim 侧（H021 / H022 才补，本 handoff 只观察现象）
- 不改 ~/.hermes/config.yaml 的 `model.provider` / `model.default`
- 不改 openai-shim 任何代码（只设 env 启它）
- 不 commit ~/.hermes/ 到 git

## Suggested Steps

```bash
# ────────── Stage A: 配 webhook platform ──────────
# 推荐 wizard
hermes gateway setup
# 选 webhook → enable → port 留 default 8644 → secret 选 auto

# 或手工
cat >> ~/.hermes/config.yaml <<'EOF'
platforms:
  webhook:
    enabled: true
    extra:
      host: "0.0.0.0"
      port: 8644
EOF

# ────────── Stage B: 起 gateway + subscribe ──────────
# tab A
hermes gateway run
# 等看到 "webhook" listener 起来；log 含 0.0.0.0:8644

# tab B
hermes webhook subscribe xiaozhi-transcript \
  --prompt 'XiaoZhi user said: {user}. Assistant replied: {assistant}.' \
  --description 'XiaoZhi robot transcript ingress (H020)' \
  --deliver-only --deliver log

hermes webhook list

# ────────── Stage C: 起 openai-shim 真连 ──────────
# tab C
cd ~/code/robot_class/final_pro_xiaozhi_robot/openai-shim
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
HERMES_TRANSCRIPT_URL='http://localhost:8644/webhooks/xiaozhi-transcript' \
  /home/kk/miniconda3/bin/python -m uvicorn openai_shim.app:app --port 8089

# ────────── Stage D: curl 触发 ──────────
# tab D
curl -N -X POST http://localhost:8089/v1/chat/completions \
  -H "Authorization: Bearer fake" -H "Content-Type: application/json" \
  -d '{"model":"echo","messages":[{"role":"user","content":"hi"}],"stream":true}'

# ────────── Stage E: 验 Hermes 收到 ──────────
# 看 tab A (hermes gateway run) 日志，期望出现 POST /webhooks/xiaozhi-transcript
# 看 hermes logs
ls -la ~/.hermes/logs/ | tail -5
tail -50 ~/.hermes/logs/gateway*.log 2>/dev/null
# 如启 deliver-only --deliver log → 渲染的 prompt 应出现在 gateway log
```

## Recovery

| 症状 | 可能原因 | 修 |
|---|---|---|
| `hermes gateway run` 报 webhook 没启 | platforms.webhook.enabled 没 set 或 wizard 漏 | 手工写 ~/.hermes/config.yaml 那 3 行；重启 gateway |
| port 8644 占用 | 老 Hermes 进程残留 | `ss -tln | grep 8644`; `pkill -f hermes` 后重起 |
| webhook list 不显示 xiaozhi-transcript | subscribe 用的 profile 跟 gateway run 不同 | `hermes profile list`; 显式 `--profile <name>` |
| shim 启动报 HermesBackend import 错 | H019 commit 没 sync | `git pull && cd openai-shim && uv pip install --system -e '.[test]'` |
| curl 收到 SSE 但 Hermes 没收到 | proxy / firewall / port 错 | 重读 H016 §Stage C unblock 段；`unset ALL_PROXY` |
| Hermes 收到但 prompt 渲染缺字段 | payload 字段名跟 prompt template 对不上 | shim payload 是 `user/assistant/model/session/timestamp_unix`；template 用 `{user}` `{assistant}` 即可 |
| Hermes 403 / HMAC 错 | 启了 secret 但 shim 没签 | Stage F：记 Open Q 给 planner，**不**在本 handoff 修 shim |

## For Auditor

不发 auditor。本 handoff 物理验证，做完直接进 H021。M2 完整集成累计后批 review。

## Open Questions for Planner

- 如果 HMAC 必须签 → 写 H021.bis 给 shim 加签名（httpx interceptor 或自手算
  `hmac.new(secret, body, sha256).hexdigest()`，header `X-Hermes-Signature`
  之类）
- 真 agent 模式 vs `--deliver-only`：demo 要 user 跟 Hermes 真对话才有用，
  所以 H022 demo 那次必须**去掉 `--deliver-only`**；H020 先用 deliver-only
  省 token + 验路径
- session id 协调：shim 每次 fork 用 `chatcmpl-<uuid>` 当 session，但 Hermes
  webhook spawn 出来的 session 是它自己的 id；如果想"一通对话 = 一个 Hermes
  session"，要么 shim 把同一 chatcmpl id 复用整轮、要么用 ESP32 device_id
  代替（Week 1.5 任务）
- 演示侧：deliver target 换成 telegram / discord 比 log 更有冲击力——可放
  H022 demo polish

## Planner Unblock — Stage A–E (2026-06-19, main-loop per ADR-0003 II)

User 让 planner 代跑 H020 + H016 (D 段 ESP32 物理不可代)。H020 全 5 段可
main-loop 跑，开干。

### Stage A — 启用 webhook platform ✅

```
$ cat >> ~/.hermes/config.yaml <<EOF
platforms:
  webhook:
    enabled: true
    extra:
      host: "127.0.0.1"
      port: 8644

## Planner Unblock — Stage A–E (2026-06-19, main-loop per ADR-0003 II)

User 让 planner 代跑 H020（H016 Stage D 物理段无 ESP32 不可代）。H020 全 5
段 main-loop 可跑，开干。

### Stage A — 启用 webhook platform ✅

手工往 `~/.hermes/config.yaml` 追加 `platforms.webhook.enabled: true` +
`host: 127.0.0.1` + `port: 8644`。`hermes webhook list` 不再报 "platform
not enabled"，改报 "No dynamic webhook subscriptions"。

### Stage B — gateway run + subscribe ✅

**坑 1**：`--deliver-only` 跟 `--deliver log` 互斥。CLI 报：

> Error: --deliver-only requires --deliver to be a real target (telegram,
> discord, slack, ...) — not 'log'.

放弃 `--deliver-only`，默认 deliver=log + agent 模式（每 trigger 烧一个
小 prompt，约 100 token 可控）：

```
$ hermes webhook subscribe xiaozhi-transcript \
    --prompt 'XiaoZhi user said: {user}. Assistant replied: {assistant}. \
              Please briefly acknowledge in one sentence.' \
    --description 'XiaoZhi robot transcript ingress (H020)'

  Created webhook subscription: xiaozhi-transcript
  URL:    http://127.0.0.1:8644/webhooks/xiaozhi-transcript
  Secret: <43-char base64, prefix InNt...>   # auto-gen, 不贴全
```

启 gateway：

```
$ unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
$ hermes gateway run &
$ ss -tln | grep 8644
LISTEN 0  128  127.0.0.1:8644  0.0.0.0:*

(gateway log)
INFO gateway.platforms.webhook: [webhook] Reloaded 1 dynamic route(s): xiaozhi-transcript
INFO gateway.platforms.webhook: [webhook] Listening on 127.0.0.1:8644 — routes: xiaozhi-transcript
INFO gateway.run: ✓ webhook connected
INFO gateway.run: Gateway running with 1 platform(s)
```

启动 ~3s 完成（不是文档说的 5-30s）。两个启动 WARNING（stale systemd unit
+ no user allowlist）无害。

### Stage C — uvicorn shim 真连 ✅

```
$ HERMES_TRANSCRIPT_URL='http://127.0.0.1:8644/webhooks/xiaozhi-transcript' \
    pyx -m uvicorn openai_shim.app:app --port 8089
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8089
```

### Stage D — curl 触发 ⚠️ HMAC 401（预期失败）

SSE 端正常：

```
$ curl -sN -X POST http://127.0.0.1:8089/v1/chat/completions \
    -H "Authorization: Bearer fake" -H "Content-Type: application/json" \
    -d '{"model":"echo","messages":[{"role":"user","content":"hi from H020"}],"stream":true}'

data: {"id":"chatcmpl-79253138...","choices":[{"delta":{"content":"echoed: hi from H020"...,"finish_reason":"stop"...}],...}
data: [DONE]
```

但 shim fork 失败：

```
INFO:     127.0.0.1:37938 - "POST /v1/chat/completions HTTP/1.1" 200 OK
Hermes transcript fork failed: Client error '401 Unauthorized' for url
  'http://127.0.0.1:8644/webhooks/xiaozhi-transcript'
```

gateway 那侧：

```
WARNING gateway.platforms.webhook: [webhook] Invalid signature for route xiaozhi-transcript
INFO aiohttp.access: ... POST /webhooks/xiaozhi-transcript HTTP/1.1 401 199 ... python-httpx/0.28.1
```

✅ **正是 H020 §Stage F 预言 + Open Q 留的"HMAC 待补"**——shim 不签 HMAC，
Hermes 401 拒。HermesBackend fire-and-forget 设计正常工作：SSE 主路径不
被 fork 失败拖累。

### Stage D.bis — 手算 HMAC 直送 webhook (绕开 shim 验路径) ✅

为验 Hermes 那侧的解码 + render prompt + spawn agent 链路工作正常，
手算 HMAC：

```
$ SECRET='<43 char from subscribe output>'
$ PAYLOAD='{"user":"hi from H020","assistant":"echoed: hi from H020","model":"echo","session":"chatcmpl-manual-h020","timestamp_unix":1781873681}'
$ SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -hex | awk '{print $2}')

# 试 3 个 header name 找正确格式：
$ curl -X POST .../webhooks/xiaozhi-transcript -H "X-Hermes-Signature: sha256=$SIG" -d "$PAYLOAD"
< HTTP/1.1 401 Unauthorized                       ✗
{"error": "Invalid signature"}

$ curl -X POST .../webhooks/xiaozhi-transcript -H "X-Hub-Signature-256: sha256=$SIG" -d "$PAYLOAD"
< HTTP/1.1 202 Accepted                           ✅
{"status": "accepted", "delivery_id": "1781873719741"}

$ curl -X POST .../webhooks/xiaozhi-transcript -H "X-Webhook-Signature: $SIG" -d "$PAYLOAD"
< HTTP/1.1 202 Accepted                           ✅ (也接受, 见 Bonus #5)
```

**关键发现**：Hermes webhook HMAC header **是 GitHub 风格**
`X-Hub-Signature-256: sha256=<hex>`，不是 `X-Hermes-Signature`。

### Stage E — 验 Hermes 那侧渲染 prompt + spawn agent ✅

`~/.hermes/logs/agent.log` 含 Stage D.bis 触发后的完整链路：

```
INFO gateway.platforms.webhook: [webhook] POST event=unknown
  route=xiaozhi-transcript prompt_len=117 delivery=1781873719741
INFO aiohttp.access: ... POST /webhooks/xiaozhi-transcript HTTP/1.1 202 271

INFO gateway.run: inbound message: platform=webhook
  user=xiaozhi-transcript chat=webhook:xiaozhi-transcript:1781873719741
  msg='XiaoZhi user said: hi from H020. Assistant replied: echoed: hi from H020. Please'

INFO [20260619_205520_be1c7197] agent.conversation_loop: conversation
  turn: session=20260619_205520_be1c7197 model=deepseek-v4-pro
  provider=deepseek platform=webhook history=0
  msg='XiaoZhi user said: hi from H020. Assistant replied: echoed: hi from H020. Please...'
```

**ADR-0005 主线全验证**：
- ✅ Hermes webhook 解 payload（5 字段全识别）
- ✅ prompt template 渲染含 `echoed: hi from H020` 完整字串
- ✅ Hermes spawn agent session `20260619_205520_be1c7197`
- ✅ agent.conversation_loop 起来读到正确 msg

agent 后续调 DeepSeek `APIConnectionError`（10s 内 3 次重试失败）——本机
→ api.deepseek.com 网络问题（`unset *PROXY` 后直连失败；hermes 子进程
继承父级 env，也丢了 proxy）。**不算 H020 失败**，是 H022 demo polish
要处理的事。

### AC verification 汇总

| AC | Stage | 结果 |
|---|---|---|
| webhook platform enabled + 8644 LISTEN | A/B | ✅ |
| hermes webhook subscribe xiaozhi-transcript | B | ✅ secret 43 char auto-gen |
| `hermes gateway run` + listener up | B | ✅ ~3s 冷启 |
| uvicorn shim with HERMES_TRANSCRIPT_URL | C | ✅ 1s |
| curl SSE round-trip `echoed: hi from H020` | D | ✅ |
| Hermes 收到 transcript POST | D | ⚠️ shim path 401 (HMAC 未签); D.bis 手算 HMAC 用 `X-Hub-Signature-256` 走通 202 |
| Hermes 渲染 prompt template | E | ✅ `msg='XiaoZhi user said: hi from H020...'` |
| Hermes spawn agent session | E | ✅ session `20260619_205520_be1c7197` |
| Agent reads correct msg | E | ✅ history=0 + 完整 msg |
| memo 贴回 | (本段) | ✅ |

**机器侧全通**。

### Bonus 观察 / 待回灌

1. **Hermes webhook 强制 HMAC**：`--secret` 不可空。demo 答辩日要么：
   (a) shim 加 HMAC 签名（**推荐 H021.bis**，~5 行：拼 body 前算
   `hmac.new(secret.encode(), body_bytes, sha256).hexdigest()`，header
   `X-Hub-Signature-256: sha256=<hex>`），(b) fork ~/.hermes 找配置关
   HMAC，(c) curl 手算 HMAC 走旁路
2. **Header 名是 GitHub 风格 `X-Hub-Signature-256`**——不是 H020 handoff
   §F Open Q 假设的 `X-Hermes-Signature`；**回灌**到 H021.bis handoff
3. **`--deliver-only` + `--deliver log` 互斥**：log 不算 real target；
   要 0-token 必须用真 telegram/discord channel + `--deliver-only`；
   demo 答辩用真 channel 视觉效果更好
4. **DeepSeek connection error**：unset *PROXY 后 hermes 子进程没 proxy
   连不出去。修法：写 `HTTPS_PROXY=http://127.0.0.1:7897` 进
   `~/.hermes/.env`（hermes 子进程会读），父级 shim 仍 unset 走直连 LAN
5. **两个 header name 都被接受 202**：`X-Hub-Signature-256` 跟
   `X-Webhook-Signature` 都通——Hermes 校验函数有 fallback 路径；
   **待 H022 batch review 时查 gateway 源码确认白名单**
6. **agent loop 自动重试 3 次**：DeepSeek 失败后重试间隔指数退避
   2.4s → 5.6s → 给 demo 答辩日预估 RTT 上限：~20s（fork-spawn-deepseek-retry）
7. **`hermes gateway run` 两个启动 WARNING 无害**：stale systemd unit 跟
   no user allowlist；后者意味 webhook user 不在 allowlist，但 webhook
   平台允许；正式 demo 可加 allowlist 加固

### Bitter lesson 候选

- **环境 env 跟 hermes 子进程**：hermes 用 `subprocess` 拉起 agent，agent
  进程继承 parent env。父级 `unset *PROXY` 跑 gateway → agent 也丢 proxy
  → outbound 失败。**修法**：把 proxy 配进 `~/.hermes/.env`（它会传给 agent
  独立于 parent），parent shell 仍 unset。**待回灌** shared/global-commands
  §Hermes

### Files touched

- 改 `~/.hermes/config.yaml`（加 platforms.webhook）—**仓库外**
- 临时建后又移除：webhook subscription `xiaozhi-transcript` (secret 不入库)
- 新 `/tmp/h020-env.sh`（含 secret，不入库）
- 改本 handoff (本段)
- 待更：`docs/handoffs/INDEX.md` 同步 status / move to archive
