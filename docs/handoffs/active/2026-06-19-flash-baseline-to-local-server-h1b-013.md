---
id: 2026-06-19-flash-baseline-to-local-server-h1b-013
from: planner
to: user
parent: 2026-06-19-idf-build-verify-h1a-012
supersedes:
status: pending
created: 2026-06-19
artifacts:
  - esp/xiaozhi-esp32/sdkconfig (改 OTA_URL)
  - esp/xiaozhi-esp32/build/ (重 build)
  - ~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml (改 server.websocket)
---

## Why user-led

按 [ADR-0003](../adr/0003-executor-runs-in-main-loop.md) 类型 II：
- 连真实 USB 设备（codex / claude sandbox 都没设备访问权）
- 改 LAN-reachable 地址要 user 视具体网络环境定（家里 wifi / 工位 / 移动热点 IP 都不一样）
- monitor serial output 是交互式的（要按 Ctrl+] 退出）

planner 自己能跑的部分（改 sdkconfig / 改 server config / build）也写出来给参考，但要求 user 亲自在终端跑、亲自连 USB。

## Objective

把 [H012](archive/2026-06-19-idf-build-verify-h1a-012.md) build 出来的 `xiaozhi.bin`
**烧到真 ESP32-S3 OttoRobot**，让它**连本地 docker server** 而不是上游
`api.tenclass.net`，端到端验证 baseline 链路在本机能跑：开机 → 上 wifi →
拉 OTA → 取 ws endpoint → WS hello 互握 → 录音上行 → server 收到 + LLM
回 → ESP32 播 TTS。

H1b 完成 = **Week 0 真正闭环**，M2 openai-shim 可以开工。

## Constraints

- 不动 `esp/xiaozhi-esp32/main/` 任何源码（包括 boards/otto-robot/，M4 才动）
- 不引入 API key 到 git 跟踪文件（OTA_URL 是 LAN 地址不算 secret，但提交前
  必看 git status）
- 不切上游 commit（保持 `b392c63`）
- 错误处理纪律按 [H010 §Error-handling discipline](archive/2026-06-19-mcp-transcript-egress-spike-010.md)
- monitor 看到 device 上线 + 一轮对话 ok 后立刻 Ctrl+] 退出，**不**留 monitor 跑（占串口）

## Acceptance Criteria

- [ ] `idf.py flash monitor` 后 ESP32 串口日志含 `WiFi connected` 或等价
- [ ] OTA 日志：`POST https://<your-LAN-ip>:8003/xiaozhi/ota/` 返回 200，
      解析到 `websocket.url = ws://<your-LAN-ip>:8000/xiaozhi/v1/`
- [ ] WS hello 日志：ESP32 端 `Session ID: <...>`；server 端
      `docker logs xiaozhi-esp32-server | grep <device-mac>` 含 `connected`
- [ ] 对机器人说一句话（任意），server logs 含 `STT result` + `LLM ...
      DeepSeek` + `TTS chunk`；ESP32 喇叭播出回复
- [ ] sanity 验 contract §8：复测 wscat 直接打 ws endpoint 拿到 hello
      回应（这步可以在 ESP32 烧之前做，验 server 配置对）
- [ ] 把这 5 项实测结果 + ESP32 device MAC + LAN IP（不带 wifi 密码！）+
      flash 总耗时 写一段 ≤15 行 memo 贴回 What I Did
- [ ] **不**让 monitor 一直跑

## Context Pointers

- @docs/contracts/api/v1/esp32-to-server-handshake.md (**先读这份**——
  握手协议字段全在这)
- @docs/handoffs/archive/2026-06-19-idf-build-verify-h1a-012.md (H1a 已 build
  好，本任务只 flash 不重 build，除非改了 OTA_URL 要 reconfigure)
- @docs/handoffs/archive/2026-06-19-xinnan-docker-bringup-user-011.md (server
  已起在 ws://localhost:8000；OTA 在 http://localhost:8003)
- @docs/diagnoses/2026-06-19-esp32-baseline-server-url-switch.md (为什么必须
  改 sdkconfig 而不能靠 BluFi 切 URL)
- @docs/adr/0002-week0-baseline-correction.md §不符 3 (H1a/H1b 拆段的动机)
- @docs/adr/0005-openai-compat-transcript-egress.md (H1b done 后 M2/M3 路径
  就明朗了)
- @esp/xiaozhi-esp32/main/Kconfig.projbuild:3-7 (CONFIG_OTA_URL 默认值)
- @.claude/memory/shared/global-commands.md §ESP32 (build/flash 命令)

## Out of Scope

- 不写 M1/M2/M3 任何代码
- 不优化 server 配置（FunASR/EdgeTTS 默认就够）
- 不动 voice-agent-pg / n8n 等本机其它服务
- 不上 wss / TLS（H1b 走 LAN 明文；生产化是后话）
- 不测多轮长对话/上下文记忆 / 不测 M4 工具（那是 Week 2+）

## Steps

### Pre-flight

1. **确认 H011 server 还活着**：
   ```bash
   docker ps --filter name=xiaozhi-esp32-server --format '{{.Names}} {{.Status}}'
   # 期望 Up ...
   curl -sS http://localhost:8003/xiaozhi/ota/   # 期望"OTA接口运行正常..."
   ```

2. **拿你的 LAN IP**（ESP32 wifi 上来后能 ping 到的）：
   ```bash
   ip addr show | grep -E 'inet 10\.|inet 192\.|inet 172\.(16|17|18|19|2[0-9]|3[01])\.' \
     | grep -v 'docker\|br-\|veth' | head -3
   # 选一条跟 ESP32 同 wifi 网段的 IP，记为 $HOST_IP
   ```

   ⚠️ **当前实测**：`server.websocket` 配的是 `ws://0.0.0.0:8000/...`，
   ESP32 拉 OTA 后会拿到 `ws://0.0.0.0:...`，**0.0.0.0 是不可达地址**，
   连不上。Stage A 必须改成你的 LAN IP。

### Stage A — 改 server 配置 `server.websocket` 指向你的 LAN IP

```bash
SERVER_CONFIG=~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml

# 备份
cp $SERVER_CONFIG ${SERVER_CONFIG}.bak

# 改 ws URL（把 0.0.0.0 换成 $HOST_IP）
sed -i "s|ws://0.0.0.0:8000/|ws://$HOST_IP:8000/|" $SERVER_CONFIG

# 验
grep -E 'websocket:' $SERVER_CONFIG
# 期望：  websocket: ws://10.x.x.x:8000/xiaozhi/v1/

# 重启 server 让它读新 config
cd ~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server
docker compose restart
sleep 3
docker logs xiaozhi-esp32-server 2>&1 | tail -10

# 验改对了
curl -sS http://$HOST_IP:8003/xiaozhi/ota/
# 期望：OTA接口运行正常，向设备发送的websocket地址是：ws://$HOST_IP:8000/xiaozhi/v1/
```

### Stage A-bis — wscat sanity check（可选但推荐，验 contract §8）

```bash
# 装 wscat（如果没装）
which wscat || npm i -g wscat

# 模拟 ESP32 接入：
wscat -c "ws://$HOST_IP:8000/xiaozhi/v1/" \
  -H "Protocol-Version: 1" \
  -H "Device-Id: aa:bb:cc:dd:ee:ff" \
  -H "Client-Id: test-uuid-h1b"

# 进交互后粘下面这行（一行，注意 JSON）：
> {"type":"hello","version":1,"features":{"mcp":true,"aec":false},"transport":"websocket","audio_params":{"format":"opus","sample_rate":16000,"channels":1,"frame_duration":60}}

# 期望立刻收到：
< {"type":"hello","transport":"websocket","session_id":"...","audio_params":{...}}

# Ctrl+C 退出 wscat
```

A-bis 通了 = server 端 100% 正常，剩下问题都在 ESP32 端，省一大半排错时间。

### Stage B — 改 sdkconfig `CONFIG_OTA_URL`

```bash
cd ~/code/robot_class/final_pro_xiaozhi_robot/esp/xiaozhi-esp32
source ~/esp-idf-5.5.2/export.sh

# 备份现有 sdkconfig
cp sdkconfig sdkconfig.h1a-baseline

# 修改 OTA URL（保留 H012 加的 OTTO 3 个 CONFIG）
sed -i "s|^CONFIG_OTA_URL=.*$|CONFIG_OTA_URL=\"http://$HOST_IP:8003/xiaozhi/ota/\"|" sdkconfig

# 验
grep -E '^CONFIG_OTA_URL' sdkconfig
# 期望：CONFIG_OTA_URL="http://<your-LAN-ip>:8003/xiaozhi/ota/"

# 重新 build（增量，只重 build OTA URL 嵌入的 firmware）
time idf.py build 2>&1 | tail -5
# 期望：Project build complete.；耗时 < 2 min（增量）
```

### Stage C — 连 USB + flash + monitor

```bash
# 连 USB-C 线到 ESP32-S3 OttoRobot，让它进 download 模式
# （Boot 按住 + RST 按一下再松 Boot；不同板子可能不一样）

# 查串口
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
# 期望看到 /dev/ttyUSB0 或 /dev/ttyACM0；记为 $PORT

# 加 dialout 组（如果 permission denied）
groups | grep -q dialout || { sudo usermod -aG dialout $USER; echo "需要 logout 再 login"; }

# flash + monitor
idf.py -p $PORT flash monitor    # 退出 monitor: Ctrl+]
```

监 monitor 看下面 4 段日志按顺序出现：

1. `Booting`/`Otto` / `Free heap` — boot ok
2. `WiFi connected` 或 `wifi:state: ... -> run` — wifi ok
3. `ota.cc` 相关：`GET <你的 OTA URL>` + `websocket url:` — OTA 拉到 server 地址
4. `WebsocketProtocol` 或 `Session ID:` — WS 握手 ok

第 4 段出现 = 链路通。然后对机器人说话，看 `STT result` 和 server logs。
**确认 ok 立即 Ctrl+] 退出 monitor**，不要让它一直占串口。

### Stage D — 跨端验证

```bash
# server 端验：device 出现在 sessions
docker logs xiaozhi-esp32-server 2>&1 | grep -E 'connected|session|device' | tail -10

# 对机器人说一句话后：
docker logs xiaozhi-esp32-server 2>&1 | tail -50 | grep -E 'STT|LLM|TTS|DeepSeek'
```

## Recovery

| 症状 | 可能原因 | 修 |
|---|---|---|
| `ls /dev/ttyUSB*` 没东西 | USB 线只通电不通数据 / driver | 换数据线；`dmesg \| tail` 看 CH340/CP210x driver 加载 |
| flash 报 `Failed to connect` | Boot 没进 download 模式 / 波特率太高 | 按 Boot 按 RST；`idf.py -p $PORT -b 460800 flash` |
| monitor 一直 `Failed to send OTA` | OTA URL 网络不可达 | 在另一台机器 `curl http://$HOST_IP:8003/xiaozhi/ota/` 验；防火墙 / wifi 隔离 |
| WS 一直 `connecting...` 不上 | server.websocket 还是 0.0.0.0 / ESP32 跟 docker 不同子网 | 复查 Stage A；ping 测 |
| 收 `Server hello timeout` | server 收到但响应慢 / 协议版本不匹配 | `docker logs` 看 server 报什么；Protocol-Version 1 是正确的 |
| ESP32 上线但没语音回复 | DeepSeek LLM 调用失败 / FunASR 模型缺 | `docker logs ... \| grep ERROR`；H011 已修过 FunASR 893MB 模型缺失 |

## For Auditor

不发 auditor。**这是 Week 0 闭环的最后一公里**；H1b done 即可，planner
自审。M1 开工前做一次"集中审计"（积累几个 milestone 后批量），不为 H1b
单发。

## Open Questions for planner（H1b done 后回灌的 fact）

下面这些字段先空着，等你跑完填回来：

- ESP32 device MAC = ?
- 实际用的 LAN IP = ?
- flash 总耗时 = ?
- WS 握手 RTT（hello → server hello）= ?（看 monitor 时戳）
- LLM 一轮 RTT（用户说话尾到 TTS 开播）= ?（主观感 < 3s 通过；> 5s 需调优）
- ESP32 baseline 编译的 default vs flashed boot heap free = ?（监控 M4 内存预算）

跑完后 planner 把上面 6 条搬进 `docs/contracts/api/v1/esp32-to-server-handshake.md` §8 实测段。
