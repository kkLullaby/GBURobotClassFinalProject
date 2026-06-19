---
id: 2026-06-20-m3-plugin-install-and-hermes-verify-028bis
from: planner
to: user
parent: 2026-06-19-m3-hermes-plugin-spike-028
supersedes:
status: pending
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
