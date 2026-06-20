# scripts/

ottagent 运维脚本。

## 一键启动 demo

```bash
bash scripts/start_all.sh
```

跑前需要 (一次性, 后续重启不用动):

| 项 | 说明 |
|---|---|
| 手机开热点 | 笔记本 + ESP32 OttoRobot 都连这个热点 |
| ESP32 配过这个 SSID | 没配过先 BluFi (见 `docs/blufi_zh.md`) |
| clash-verge 在跑 | DeepSeek 走代理 (`#45 fake-ip`) |
| `~/.config/openai-shim/.env` (chmod 600) | `DEEPSEEK_API_KEY=sk-...` |
| `~/.config/lark-mcp/.env` (chmod 600) | `LARK_APP_ID/SECRET/USER_MOBILE` |

`start_all.sh` 自动做:

1. **pre-flight**: docker / clash / hermes / 两个 `.env` / compose 文件存在
2. **IP 同步**: 检测笔记本当前 wifi IP, 不匹配则改 `xinnan-tech/.config.yaml` + restart 容器
3. **docker up**: `mcp-endpoint-server` + `xiaozhi-esp32-server` (已在则跳)
4. **杀 sidecar**: 防 `mcp_endpoint /mcp/` slot 抢占 (bitter `#32`)
5. **shim**: 调 `start_shim.sh` 用 hybrid mode 起
6. **smoke**: HTTP 发 "挥挥手" 看真 DeepSeek 是不是回 stream
7. **cheatsheet**: 打印 voice 测试三句话 + 实时观察命令

## 一键停

```bash
bash scripts/stop_all.sh           # 停 (容器保留, 下次秒起)
bash scripts/stop_all.sh --down    # 彻底清掉容器
```

## ⚠️ ESP32 OTA URL 飘移问题

ESP32 固件里硬编码了 OTA server 地址 (烧固件时 menuconfig 配的)。
如果换了 wifi → 笔记本 IP 变 → ESP32 boot 时 hit 不到 OTA → 喇叭不响。

**3 个解法**:

1. **手机 hotspot 用 DHCP 静态绑定**: 大多数 Android 在 "热点设置 → 已连接设备"
   能给笔记本 MAC 锁一个 IP (推荐, 一劳永逸)
2. **路由器固定 DHCP**: 跟 1 类似, 给笔记本 wifi MAC 绑固定 IP
3. **重 BluFi + 重烧 OTA URL**: 麻烦, 但绝对管用 (见 `esp/xiaozhi-esp32/docs/blufi_zh.md`)

知道烧的是哪个 IP? 看 `esp/xiaozhi-esp32/sdkconfig` 里 `CONFIG_OTA_URL` 或 monitor
重启时 boot 日志第一段。

## 单独工具

- `start_shim.sh` — 只起 shim (假设 docker 已在), 被 `start_all.sh` 调
- 直接调试 shim: `tail -f /tmp/shim.log`
- 直接调试 server: `docker logs -f xiaozhi-esp32-server`

## 当出问题时按顺序检查

```bash
# A. 端口都活吗
ss -tln | grep -E ':(8000|8003|8004|8089) '

# B. shim 是真 hybrid 吗 (不是回到 echo)
PID=$(pgrep -f openai_shim.app:app | head -1)
cat /proc/$PID/environ | tr '\0' '\n' | grep OPENAI_SHIM_BACKEND
# 应见 OPENAI_SHIM_BACKEND=hybrid

# C. ESP32 是不是真连上 server
docker logs xiaozhi-esp32-server 2>&1 | tail -30 | grep -E 'connected|session|register'

# D. DeepSeek 通吗
curl -sS -N -X POST http://localhost:8089/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-v4-pro","stream":true,"messages":[{"role":"user","content":"挥手"}]}' \
  --max-time 20 | head -2
# 应见 reasoning_content / choices, 不该见 echoed: 或 connection error

# E. lark 通吗 (走 hermes)
hermes -z "调 lark_send_message_to_self 发 '一键脚本验测'"
# 飞书私聊应到一条
```

## Bitter lessons 这两个脚本固化的

- `#32` mcp_endpoint slot 单一 → 自动 kill sidecar
- `#42` voice 双层 timeout → `HERMES_AGENT_TIMEOUT_S=300`
- `#43` shim 默认 backend=echo → 显式 `OPENAI_SHIM_BACKEND=hybrid`
- `#44` clash 大小写 proxy env → unset 全部 8 个再 export
- `#45` DeepSeek fake-ip vs lark direct 冲突 → `NO_PROXY=feishu`
- `#46` uvicorn 启动 import 慢 → 等 ≥3s 再 verify
- `#47` 永远不在 demo 文档 inline `sk-xxx` 示例
