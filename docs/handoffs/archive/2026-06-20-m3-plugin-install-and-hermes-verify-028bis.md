---
id: 2026-06-20-m3-plugin-install-and-hermes-verify-028bis
from: planner
to: user
parent: 2026-06-19-m3-hermes-plugin-spike-028
supersedes:
status: done
created: 2026-06-20
artifacts:
  - ~/.hermes/plugins/xiaozhi/ (新, 仓库外, symlink 或 cp)
  - shim env file 改 (仓库外)
---

## Why now

H028 Stage A 已 done（hermes-xiaozhi-plugin 包骨架 + 3 pytest PASS）。
现在到 Stage B：**真装 plugin + 真启 Hermes gateway + 让 ESP32 voice 流
经 plugin 而非 generic webhook**。这一步必须 user 物理参与，因为：

1. `hermes gateway run` 是长跑进程，sandbox 跑了会一直挂着
2. 改 `~/.hermes/plugins/` 是用户家目录写
3. ESP32 voice 验证要对机器人讲话
4. shim env 切 webhook URL 后要重启 shim 服务（user 之前自己起的）

跟 H013 / H020 / H022 同模式：**planner 起 coach session 远程指导 user 实操**。

## Objective

让 Hermes 把 ESP32 当作"first-class xiaozhi platform" 收 transcript，
**而不是** generic webhook 路由。done 后 `hermes gateway run` 日志里看到：

```
[gateway.platform_registry] Registered platform adapter: xiaozhi (plugin)
[gateway.run] Connected platform: xiaozhi (XiaoZhi 🤖)
```

且 ESP32 voice 一轮后，`hermes` TUI 里 session 标签是 `[xiaozhi]`
而不是 `[webhook]`。

## Stages

### Stage A (5 min)：装 plugin 到 ~/.hermes/plugins/xiaozhi/

```bash
mkdir -p ~/.hermes/plugins
cp -r ~/code/robot_class/final_pro_xiaozhi_robot/hermes-xiaozhi-plugin/src/hermes_xiaozhi \
      ~/.hermes/plugins/xiaozhi
cp ~/code/robot_class/final_pro_xiaozhi_robot/hermes-xiaozhi-plugin/src/hermes_xiaozhi/plugin.yaml \
   ~/.hermes/plugins/xiaozhi/plugin.yaml
ls ~/.hermes/plugins/xiaozhi/   # 期望: adapter.py __init__.py plugin.yaml
```

(用 cp 不用 symlink — Hermes loader 对 symlink 可能 strict, H028 design §8 风险表)

### Stage B (3 min)：起 hermes gateway run 看 plugin 注册

```bash
# 先 kill 原 generic webhook gateway (如果还在跑)
pkill -f 'hermes gateway' && sleep 2

# 装好 plugin env
export XIAOZHI_WEBHOOK_PORT=8645
export XIAOZHI_WEBHOOK_SECRET="$(openssl rand -hex 22)"
export XIAOZHI_DEVICE_ID="ac:a7:04:30:91:78"
echo "$XIAOZHI_WEBHOOK_SECRET" > /tmp/h028bis-secret.txt   # 留个临时副本给 Stage C 用

# 启 gateway
hermes gateway run 2>&1 | grep -E 'xiaozhi|Platform|webhook|Registered' &
sleep 5
```

**AC**: 上面 grep 出至少这几行：
- `Registered platform adapter: xiaozhi (plugin)`
- `Platform 'xiaozhi' ... connected` 或类似

### Stage C (5 min)：切 shim env 指 plugin webhook

```bash
# 之前的 shim PID
ps aux | grep -E 'uvicorn openai_shim' | grep -v grep

# 拉新 env + restart
pkill -f 'uvicorn openai_shim' && sleep 2
nohup env \
  OPENAI_SHIM_BACKEND=deepseek \
  DEEPSEEK_API_KEY='<原本的 deepseek key>' \
  HERMES_TRANSCRIPT_URL='http://127.0.0.1:8645/webhooks/xiaozhi-transcript' \
  HERMES_WEBHOOK_SECRET="$(cat /tmp/h028bis-secret.txt)" \
  /home/kk/miniconda3/bin/python -m uvicorn openai_shim.app:app --host 0.0.0.0 --port 8089 \
  > /tmp/shim.log 2>&1 & disown
sleep 3
tail -5 /tmp/shim.log
```

### Stage D (2 min)：curl smoke 验签 + adapter 收

```bash
curl -sN http://127.0.0.1:8089/v1/chat/completions \
  -H 'Content-Type: application/json' -H 'Authorization: Bearer x' \
  -d '{"model":"deepseek-chat","stream":true,
       "messages":[{"role":"user","content":"hi from H028.bis"}]}' \
  | grep -m 5 'data:'
sleep 2

# 看 hermes gateway 日志
# 期望: "[xiaozhi] received transcript: hi from H028.bis"
# 或类似 session spawned
```

**AC**: hermes gateway log 显示 transcript 通过 xiaozhi platform 进来（**不是** webhook platform）

### Stage E (3 min)：ESP32 voice 真路径

对机器人说："你好"
- xinnan-tech server log: `识别文本: 你好`
- shim log: SSE delta + fork POST 8645 → 200/202
- hermes gateway: `[xiaozhi] session spawn for device ac:a7:04:30:91:78`
- 机器人喇叭: DeepSeek 回复"你好啊..."

### Stage F (1 min)：TUI 看 channel

```bash
hermes   # 进 TUI
# 期望 sidebar 出现 [xiaozhi] 和 ESP32 device 的 session
```

## Constraints

- 不改 `~/code/robot_class/final_pro_xiaozhi_robot/` 任何代码 (Stage A 只是 cp 出去)
- 不动 esp/ submodule
- 不改 M2 shim 代码 (只改 env)
- secret 不入仓库 (放 /tmp/，demo 完删)
- 期间发现的 bitter lesson **回灌** Open Questions

## Acceptance Criteria

- [ ] Stage A 完成；`ls ~/.hermes/plugins/xiaozhi/` 见 3 文件
- [ ] Stage B：hermes gateway log 含 "Registered platform adapter: xiaozhi"
- [ ] Stage C：shim 重启成功 + log 无报错
- [ ] Stage D：curl smoke 通过 + hermes gateway 收到 transcript via xiaozhi
- [ ] Stage E：ESP32 voice → hermes session 显示 `[xiaozhi]`
- [ ] Stage F：TUI sidebar 看到 xiaozhi channel
- [ ] 实测过程贴 What I Did (Stage-by-Stage)
- [ ] Open Questions 记下任何 bitter lesson (供 H027 集中回灌)

## Context Pointers

- @docs/handoffs/active/2026-06-19-m3-hermes-plugin-spike-028.md (Stage A done 状态)
- @docs/designs/active/m3-hermes-plugin-architecture.md §6 (Stage A/B/C 划分)
- @hermes-xiaozhi-plugin/README.md (装法 + env vars)
- @hermes-xiaozhi-plugin/src/hermes_xiaozhi/plugin.yaml (env var name 出处)
- @docs/handoffs/archive/2026-06-19-real-hermes-transcript-handshake-020.md
  (H020 stage 复用模板 — 真 hermes spawn session 实测)
- @docs/handoffs/archive/2026-06-19-demo-end-to-end-real-deepseek-via-shim-022.md
  (H022 ESP32 voice 实地 demo 路径)
- @.claude/memory/shared/global-commands.md §Hermes

## Out of Scope

- send() roundtrip (留 H029)
- 真把 secret 写进 ~/.hermes/.env (留 H029 收尾)
- 跨 channel routing (留 Week 3 §3.6)
- cron job (留 Week 3 §3.5)
- demo polish (留 Week 4)

## Recovery

| 症状 | 修 |
|---|---|
| `hermes gateway run` 报 "Unknown platform 'xiaozhi'" | plugin 没装到 `~/.hermes/plugins/xiaozhi/`；或者 `plugin.yaml` 内 `kind: platform` 漏 |
| `Platform("xiaozhi")` raises | gateway/config.py `_missing_` 不接 → 看是否要在 plugin loader 调用前预 cache |
| Stage D curl 401 | XIAOZHI_WEBHOOK_SECRET 不一致；两边都用 `/tmp/h028bis-secret.txt` 的同一份 |
| Stage E ESP32 不连 | 切热点 / wifi 同段；CONFIG_OTA_URL 不变（H022 教训 #12 retro） |
| Stage F TUI 不见 xiaozhi | `hermes channels list` 看看注册的 platform 名；可能要先有 session 才出现 |

## For Auditor

不发 auditor。M3 三件套 (H028 + H028.bis + H029) 全 done 后 batch review。

## Open Questions

- (User 实测后回填) Hermes loader 是用 `plugin.yaml` 的 `name:`
  字段还是目录名 `xiaozhi/` 当 platform 名？
- (User 实测后回填) 之前 H020 留的 generic `webhook` platform 还在用吗？
  跟 xiaozhi 重复路由怎么办？
- (User 实测后回填) hermes 启动如果发现 plugin 但没设 env，行为是 skip
  还是 crash？

## What I Did (planner main-loop coach session, 2026-06-20)

### Stage A ✅ (5 min wall-clock)

```
mkdir -p ~/.hermes/plugins
cp -r .../hermes-xiaozhi-plugin/src/hermes_xiaozhi  ~/.hermes/plugins/xiaozhi
ls ~/.hermes/plugins/xiaozhi/   # → __init__.py adapter.py plugin.yaml ✓
```

### Stage B ⚠️ PARTIAL — plugin loaded ≠ adapter connected

实测发现 **3 个层叠 gate**，**handoff 写法只覆盖 1 个**：

1. **Plugin discovery** ✅ — Hermes loader 扫到 `~/.hermes/plugins/xiaozhi/`
2. **Plugin enable** ⚠️ — user-source plugins **必须 opt-in**
   (`hermes plugins enable xiaozhi-platform`)，handoff Stage A 没提
   - 自动写入 `~/.hermes/config.yaml` 的 `plugins.enabled: [xiaozhi-platform]`
   - 之后 plugin `register(ctx)` 才被调用 → log: `Plugin xiaozhi-platform registered platform: xiaozhi`
3. **Platform connect** ❌ — gateway 框架要求 `~/.hermes/config.yaml`
   `platforms.<name>.enabled: true` 才会构造 adapter + 调 `connect()`；
   补完后 plugin 加载 OK 但 8645 **依然不 LISTEN**

**Root cause** (打开 `~/.hermes/plugins/xiaozhi/adapter.py:71`):

```python
async def connect(self) -> bool:
    # TODO(H028.bis): start the signed webhook listener on webhook_port.
    return True
```

**H028 Stage A 已经把这个 TODO 留给本 handoff (H028.bis)**：
> H028 Constraints: "**不**起 aiohttp / 不真听 webhook (留 H028.bis)"

但 **H028.bis Constraints 反而禁止改本仓代码**：
> "不改 `~/code/robot_class/final_pro_xiaozhi_robot/` 任何代码 (Stage A 只是 cp 出去)"

→ **两个 handoff 形成约束矛盾**，本 handoff 物理上不可能在不改 plugin
源码的前提下完成 Stage B "Connected platform: xiaozhi"。

### Stages C/D/E/F — BLOCKED on Stage B

C 切 shim env 改 webhook URL = 朝 dead 端口发，必然失败；
D/E 同；F TUI sidebar 在 adapter 没 connect 前不会出现 `[xiaozhi]`。

### Bitter lessons (供 H027 集中回灌)

1. **user-plugin opt-in 是 hermes 隐式 gate**：bundled platform 自动加载
   (`plugins.py:1166`)，但 user-source 不在 `plugins.enabled` allow-list
   里就静默 skip。`hermes plugins list` 看 status；`hermes plugins enable
   <name>` 写入 config.yaml。本 handoff Stage A "ls 见 3 文件" 不够，
   还要补 enable。
2. **plugin 注册 ≠ adapter connect**：plugin loader 调 `register(ctx)`
   只是登记 PlatformEntry；adapter `connect()` 由 gateway runtime 在
   `platforms.<name>.enabled: true` 时才调。两个 gate 都要过。
3. **adapter Stage A 是骨架**：`connect() return True` 不起 listener，
   gateway 日志看不出问题（无 ERROR，因为 connect 返 True 算成功），
   只能通过 `ss -tln | grep 8645` 验。Stage A 桩对 Hermes 框架"看起来 OK"，
   是最阴的 silent-fail。

### What I Changed (回滚清单)

- `~/.hermes/config.yaml`：加 `plugins.enabled: [xiaozhi-platform]` + 
  `platforms.xiaozhi.{enabled, extra.host=127.0.0.1, extra.port=8645}`
- `~/.hermes/plugins/xiaozhi/`：cp 全套（3 文件）
- `/tmp/h028bis/`：临时 log 目录 (`gateway.log`, `gateway2.log`)
- `/tmp/h028bis-secret.txt`：HMAC secret 副本（owner=kk 600）
- 老 generic-webhook gateway (PID 3242704) 已 kill；新 gateway PID 3474503 在跑（但只 listening 8644）

### 建议路径

需要 planner 起一个续接 handoff 处理 adapter 真起 listener。两个方向：

(a) **H028.ter (planner → executor)**: 改 `hermes-xiaozhi-plugin/src/hermes_xiaozhi/adapter.py`
    的 `connect()`, 真起 aiohttp listener on 8645 + HMAC verify + 把
    POST body 转 `MessageEvent` → `self.dispatch_message(event)`。参考
    `gateway/platforms/webhook.py:147-220`。~80 LOC + pytest 加 1 case。
    完事再 cp 一次到 `~/.hermes/plugins/xiaozhi/` 再 restart gateway 跑
    Stage C-F。

(b) **复用 generic webhook**：放弃 xiaozhi-as-first-class-platform，
    继续用 generic `webhook` 平台 + route filter，回到 H020/H022 模式。
    M3 这个"创新点拓扑"会缩水。

**推荐 (a)** — M3 plugin 是项目核心创新点（CLAUDE.md §项目简介："**创新点
不在硬件，在拓扑**"），(b) 等于放弃创新点。adapter 起 listener 是显然
的工作量，应该写下来交给 executor，不是塞回本 handoff。

本 handoff 建议 status: blocked，等 planner 决策 + 写新 handoff。

## Planner Resolution — 2026-06-20

H028.bis Stages A/B 由 user 已经走通：
- ✅ Stage A `~/.hermes/plugins/xiaozhi/` cp 完
- ✅ Stage B "enable plugin" 三层 gate 全配 (plugins enable + platforms.xiaozhi.enabled=true)
- ❌ Stage B "8645 真 LISTEN" 撞 constraint conflict → 写 [H028.ter](2026-06-20-m3-xiaozhi-adapter-listener-028ter.md) 解决

**H028.ter done** (planner 跑测 **4/4 PASS in 0.39s**, listener 实代码 90+ LOC):
- aiohttp web.Application 真起 + HMAC verify + JSON parse + MessageEvent dispatch
- 不用 user 再 reopen H028.bis；ter 完后 Stage C-F 自动可走

### What user should do after this archive

```bash
# 1. 推新 adapter.py 到 hermes plugins dir
cp ~/code/robot_class/final_pro_xiaozhi_robot/hermes-xiaozhi-plugin/src/hermes_xiaozhi/adapter.py \
   ~/.hermes/plugins/xiaozhi/adapter.py

# 2. 重启 gateway
pkill -f 'hermes gateway' && sleep 2
export XIAOZHI_WEBHOOK_PORT=8645
export XIAOZHI_WEBHOOK_SECRET="$(cat /tmp/h028bis-secret.txt)"
hermes gateway run &
sleep 5

# 3. 验
ss -tln | grep 8645              # 期望 LISTEN
curl -X POST -H 'X-Hub-Signature-256: sha256=<...>' \
    http://127.0.0.1:8645/webhooks/xiaozhi-transcript \
    -d '{"user_text":"hi","assistant_text":"oh","device_id":"ac:..."}' 
# 期望 202

# 4. 真 ESP32 voice → hermes log 看 [xiaozhi] session spawn
```

→ 这是物理验证，留 **H030 (M3 端到端 demo, user-led)** 走，不再 reopen
本 handoff。本 handoff 的 "起 listener" 任务 = H028.ter 已 done。

### Bitter lessons (供 H027 集中回灌)

记 H028.bis "What I Did" §Bitter lessons 已写的 3 条 (user-plugin opt-in /
plugin 注册 ≠ adapter connect / adapter Stage A 桩 silent-fail) +
H028.ter #18 (codex sandbox 不能 bind socket)。

### Status flow

pending → blocked (constraint conflict) → **done** (via H028.ter unblock)
