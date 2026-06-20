---
id: 2026-06-20-shim-startup-script-038
from: planner
to: user
parent: 2026-06-20-lark-mcp-server-spike-037
status: done
created: 2026-06-20
artifacts:
  - scripts/start_shim.sh
---

## Objective

把 openai-shim 的启动从"用户记忆里的 env 命令行"封装成 **可重复脚本**, 修
"shim 重启后变 echo 模式" 复发 bug, 并永久解 clash-verge proxy + DeepSeek
fake-ip 互斥问题。

## Trigger

H037 lark demo 完成后 user 重启 shim 时漏带 `OPENAI_SHIM_BACKEND=hybrid`,
voice 全程只回 `echoed: <content>`, 任何动作/tool 都不工作。复盘发现连
锁三个独立问题:

1. **shim 默认 backend=echo** (`app.py:49`) — 重启忘带 env = demo 死
2. **clash-verge 同时设大小写 proxy env**, lowercase `all_proxy=socks://`
   (bare scheme) 让 httpx init 抛 `ValueError: Unknown scheme for proxy URL`
3. **DeepSeek 域名被 clash fake-ip pool 污染** (`28.0.0.7`), 无代理时
   TLS 死, 有代理时 lark feishu 又连不出去 (#36/#37 反向)

## What I did

| File | 状态 | 说明 |
|---|---|---|
| `scripts/start_shim.sh` | ✅ 新增 | 完整封装重启逻辑, 从外部 .env 读 key |
| `~/.config/openai-shim/.env` | ✅ user 创建 chmod 600 | 只放 `DEEPSEEK_API_KEY`, 不入库 |
| `docs/adr/0007-hybrid-backend-router.md` | ✅ Bitter lessons 追加 #43-#47 |

`scripts/start_shim.sh` 核心 4 段:
1. 杀旧 shim + sleep 2 让 port 释放
2. source `~/.config/lark-mcp/.env` (让 hermes subprocess 继承 LARK_*) +
   source `~/.config/openai-shim/.env` (DEEPSEEK_API_KEY)
3. unset 大小写 8 个 proxy env, 再 export `socks5://` + `NO_PROXY=feishu`
4. 显式 export `OPENAI_SHIM_BACKEND=hybrid` + `HERMES_AGENT_TIMEOUT_S=300`

## Acceptance Criteria

- [x] `bash scripts/start_shim.sh` 后 `ss -tln | grep :8089` 见 LISTEN
- [x] `/proc/$PID/environ` 含 `OPENAI_SHIM_BACKEND=hybrid` + `ALL_PROXY=socks5://...` (非 bare socks)
- [x] motor smoke 真返 DeepSeek `reasoning_content` chunk (不是 `echoed:`)
- [x] voice "挥挥手" → 舵机真挥
- [x] voice "你好" → hermes 路径 + 喇叭说话
- [x] voice "给我发个飞书消息" → 飞书真到

## Bitter lessons (新增 #43-#47, 已回灌 ADR-0007)

- **#43 (主)**: shim 默认 backend=echo, 任何重启 = 必须显式 `OPENAI_SHIM_BACKEND=hybrid`.
  fix = `scripts/start_shim.sh` 封装, **绝不靠记忆**敲启动命令。
- **#44**: clash-verge 同时设 `ALL_PROXY` (uppercase) + `all_proxy` (lowercase bare `socks://`).
  httpx 优先读 lowercase, init 即抛 ValueError. fix = unset 两个 case + 显式 `socks5://`.
- **#45**: DeepSeek 域名被 clash fake-ip 池污染 (`28.0.0.7`), 无代理时 TLS 死.
  与 #36 (lark 必须关代理) 冲突. 解 = `NO_PROXY=open.feishu.cn,open.larksuite.com`
  让 feishu 走 direct, 其余 (DeepSeek/hermes) 走 proxy.
- **#46 (process)**: `nohup python -m uvicorn` 启动后 Python 还要 ~3s import 才 bind.
  `tail` 跑太快误判崩了. 标准纪律 = 等 ≥3s 再 ss + tail.
- **#47 (security)**: classifier 拦了 inline key 写 shell, 但 **user 仍可能直接在
  会话里 paste 真 key**. 任何 demo 文档**永远只写**"从 `~/.config/<svc>/.env` 读",
  示例里**不要出现** `sk-xxx` (会被误读成可粘真值), 用 `sk-粘贴你的真实key`。

## Out of scope

- 把 start_shim.sh 移植到 systemd unit (可选 polish, 当前 nohup 够用)
- Goal C 多 channel mesh (telegram, sms) — 留 H039+
