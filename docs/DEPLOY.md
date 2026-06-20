# Deployment Guide — 从硬件到 voice 真闭环

> 目标读者: 开源社区复刻者. 你买了 ESP32-S3 OttoRobot, 想跑通项目.
> 时长预期: 全新机器 → 真 voice "挥挥手"舵机动 = 约 **3 小时**.
> 难点不在硬件, 在网络 + 多服务编排.

---

## Part 0 — 硬件 BOM

| 硬件 | 型号 / 规格 | 价格参考 | 必须? |
|---|---|---|---|
| **主板** | ESP32-S3-N16R8 (8MB PSRAM + 16MB Flash) | ¥40-60 | ✅ |
| **机器人套件** | OttoRobot DIY 套件 (含 8 路 SG90 舵机, 12V 锂电池 18650 × 2) | ¥150-250 | ✅ (要看动作) |
| **屏幕** | ST7789 1.69" 240×280 SPI | ¥25 | ✅ (要看表情) |
| **麦克风** | MAX9814 自动增益 | ¥10 | ✅ |
| **喇叭** | MAX98357A I2S 数字功放 + 3W 喇叭 | ¥20 | ✅ |
| **摄像头** | OV2640 / OV3660 (M5Camera 兼容) | ¥30 | ❌ (vision 用) |
| **USB-C 线** | **数据线**, 不是充电线! | 自备 | ✅ |
| **手机热点 / WiFi** | 任何 2.4GHz | 自备 | ✅ |

**机器人板型选择**:
- 上游 `78/xiaozhi-esp32` 支持 7 种 board. 本项目用 `OTTO_ROBOT`.
- 如果只想跑 voice → tool 不要动作, 任何 ESP32-S3 板都行 (改 menuconfig Board Type)

**舵机校准**:
- 第一次跑 voice 控舵机前, 用 `self.otto.set_trim` (各舵机微调) 校准初始站姿
- 不校准会跑偏 / 摔倒 / 卡舵机

---

## Part 1 — 软件依赖

### 1.1 操作系统

任何 Linux (我们在 Ubuntu 24.04 测过) / macOS / WSL2 都行.
**不**支持 Windows 原生 (ESP-IDF 在 Windows 跑得起来但 docker compose path 易碎).

### 1.2 必备命令行工具

```bash
# Python ≥ 3.10 (推荐 conda)
which python3 && python3 --version

# Docker + docker compose v2
docker --version && docker compose version

# Git ≥ 2.30 (要支持 submodule + sparse-checkout)
git --version

# uv (Python 包管理)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Hermes Agent (本项目核心 dependency)
uv tool install hermes-agent
hermes --version    # 期望 ≥ 0.16.0
```

### 1.3 ESP-IDF 工具链 (烧固件用)

```bash
# 在用户 home (不入项目 git)
cd ~
wget https://github.com/espressif/esp-idf/releases/download/v5.5.2/esp-idf-v5.5.2.tar.gz
tar xf esp-idf-v5.5.2.tar.gz
mv esp-idf-v5.5.2 esp-idf-5.5.2
cd esp-idf-5.5.2

# 必须 init submodule (上游忘说, 漏跑 → set-target 崩)
git submodule update --init --recursive   # ~15 min, 不要 --depth=1

# 装工具链
./install.sh esp32s3
source ./export.sh
idf.py --version   # 期望 ESP-IDF v5.5.2

# 加 alias 到 ~/.bashrc
echo "alias get_idf552='source ~/esp-idf-5.5.2/export.sh'" >> ~/.bashrc
```

---

## Part 2 — 克隆本项目

```bash
git clone --recurse-submodules https://github.com/kkLullaby/GBURobotClassFinalProject.git
cd GBURobotClassFinalProject

# 验 submodule 拉到了
ls esp/xiaozhi-esp32/main/  # 应该有内容
```

---

## Part 3 — 后端服务 (Docker)

> **xinnan-tech xiaozhi-esp32-server** 是 ESP32 voice ↔ LLM 的桥. minimal 模式
> 不要 MySQL / Redis, 适合本地 demo.

```bash
# 在仓库外 (一次性下载, 不入本项目 git)
mkdir -p ~/code/xinnan-tech && cd ~/code/xinnan-tech
git clone https://github.com/xinnan-tech/xiaozhi-esp32-server.git
cd xiaozhi-esp32-server/main/xiaozhi-server

# 下 FunASR 模型 (893 MB, **不下会导致容器崩溃循环**)
mkdir -p models/SenseVoiceSmall
# 从 ModelScope 拉:
# https://modelscope.cn/models/iic/SenseVoiceSmall/files
# 把 model.pt (893MB) 放到 models/SenseVoiceSmall/

# 改配置 (需要 LLM API key)
cp data/.config.yaml.example data/.config.yaml
# 编辑 data/.config.yaml:
#   LLM.DeepSeekLLM.api_key: sk-<你的 DeepSeek key>
#   LLM.DeepSeekLLM.url: http://<你的 host IP>:8089/v1
#                        ← 8089 是 openai-shim 的 port, Part 4 起
#   server.websocket: ws://<你的 host IP>:8000/xiaozhi/v1/
#                     ← 这个 host IP 必须是 ESP32 能访问到的 IP
#                       (热点 IP 或局域网 IP, 不能 127.0.0.1)

# 起 docker (minimal 模式, 含 mcp-endpoint-server 子服务)
docker compose up -d
docker ps --filter name=xiaozhi
# 应见: xiaozhi-esp32-server + mcp-endpoint-server, 都 Up

# 验
curl -sS http://<你的 host IP>:8003/xiaozhi/ota/   # 返回 OTA 信息
ss -tln | grep -E ':(8000|8003|8004)\s'             # 三端口 LISTEN
```

**拿 mcp_endpoint token** (后面 sidecar 用):
```bash
docker logs mcp-endpoint-server 2>&1 | grep -E 'mcp/.*token=' | tail -1
# 形如: ws://172.20.0.2:8004/mcp_endpoint/mcp/?token=<TOKEN>
```

---

## Part 4 — Python 包 (M1/M2/M3)

```bash
cd ~/code/robot_class/final_pro_xiaozhi_robot   # 或你 clone 的路径

# 三个 Python 包, 各自 install -e
for pkg in xiaozhi-mcp-adapter openai-shim hermes-xiaozhi-plugin; do
  (cd $pkg && uv pip install --system -e '.[test]')
done

# 跑测确认装好
for pkg in xiaozhi-mcp-adapter openai-shim hermes-xiaozhi-plugin; do
  echo "=== $pkg ==="
  (cd $pkg && PYTHONPATH=src python -m pytest tests/ -q)
done
# 期望: 6 + 20 + 5 = 31 tests PASS
```

---

## Part 5 — 配置 Hermes Agent

```bash
# 配 DeepSeek (或 OpenAI / Anthropic / Ollama / Nous Portal — 任意 OpenAI-compat provider)
hermes auth add deepseek --api-key 'sk-<你的 DeepSeek key>'
hermes config set model '{"default":"deepseek-v4-pro","provider":"deepseek"}'

# 验
hermes -z "1+1=?"   # 期望返回 "2"
```

---

## Part 6 — 烧 ESP32 固件

```bash
get_idf552     # source ~/esp-idf-5.5.2/export.sh
cd esp/xiaozhi-esp32

# 配置 board type
idf.py set-target esp32s3
idf.py menuconfig
# 进 Xiaozhi Assistant → Board Type → ottoRobot
# S 保存, ESC ESC ESC, Q 退出

# OTTO_ROBOT 板要 append 3 个 CONFIG (上游 README 漏说)
cat >> sdkconfig <<'EOF'

# OTTO_ROBOT 板要求 (from main/boards/otto-robot/config.json sdkconfig_append)
CONFIG_HTTPD_WS_SUPPORT=y
CONFIG_CAMERA_OV2640=y
CONFIG_CAMERA_OV3660=y
EOF

# Build (全冷 ~7 min)
idf.py build
# 期望: xiaozhi.bin 约 3.69 MiB

# 接 ESP32 USB-C (数据线!), 烧
ls /dev/ttyACM*   # 应见 /dev/ttyACM0
idf.py -p /dev/ttyACM0 flash monitor

# 烧完会停在 "waiting for download" — 按板上 RST 键让它进 normal mode
# Ctrl + ] 退 monitor (注意是 ], 不是 Ctrl+C)
```

**首次配 WiFi (BluFi)**:
- 用手机 ESP-Touch / BluFi app 连蓝牙传 SSID + 密码
- 上游流程见 `esp/xiaozhi-esp32/docs/blufi_zh.md`

**验 14 tool 注册成功**:
```bash
docker logs xiaozhi-esp32-server 2>&1 | grep '工具数量' | tail
# 期望: 客户端设备支持的工具数量: 14
```

---

## Part 7 — 起 openai-shim (hybrid 模式) — 项目核心

```bash
cd openai-shim
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

# 从 docker config 单一来源取 DeepSeek key (bitter lesson #28)
DEEPSEEK_KEY=$(grep -E '^\s+api_key:' \
  ~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml \
  | head -1 | awk '{print $2}')

# 起 shim — hybrid 模式 (motor → DeepSeek+tools 舵机动, 其余 → hermes-z tool-call)
nohup env \
  OPENAI_SHIM_BACKEND=hybrid \
  DEEPSEEK_API_KEY="$DEEPSEEK_KEY" \
  HERMES_BIN=$(which hermes) \
  HERMES_AGENT_TIMEOUT_S=45 \
  PYTHONPATH=src python -m uvicorn openai_shim.app:app \
    --host 0.0.0.0 --port 8089 \
  > /tmp/shim.log 2>&1 & disown
sleep 3
ss -tln | grep 8089 && echo 'shim ready ✅'
```

**注意**: hybrid 模式下**不要**起 `xiaozhi-mcp-adapter` 的 sidecar (`port 8650`),
否则会跟 ESP32 抢 mcp_endpoint `/mcp/` slot, 导致 voice 控舵机失败 (bitter lesson #32).

---

## Part 8 — 真物理 demo

走到机器人面前 (≤ 30cm), 按顺序讲:

| Voice | 预期反应 | 路由 |
|---|---|---|
| "你好小智" | 喇叭"叮"一声 + 屏幕进 listening | (wake word, 不走 LLM) |
| "向前走两步" | **舵机真走** + 喇叭说"好的我走两步" | raw_deepseek + tools |
| "挥挥手" | **手真挥** | raw_deepseek + tools |
| "坐下" | **真坐** | raw_deepseek + tools |
| "帮我看 final 文件夹有什么目录" | 喇叭说真目录名 | hermes-z + shell tool |
| "现在几点了" | 喇叭说现在时间 | hermes-z + date tool |
| "用 git log 看最近三次提交" | 喇叭说真 commit | hermes-z + git tool |

如果舵机不动 / 喇叭说"我有点忙" → 看 troubleshooting.

---

## Part 9 — Troubleshooting

| 症状 | 检查 | 修法 |
|---|---|---|
| ESP32 串口找不到 `/dev/ttyACM0` | `ls /dev/ttyACM* /dev/ttyUSB*` | 换数据线 / 加 udev rule / `getfacl /dev/ttyACM0` 看用户权限 |
| `idf.py` 命令找不到 | `which idf.py` | source 时不要带 pipe (`source ./export.sh \| tail` 会丢 PATH) |
| ESP32 boot 卡 `waiting for download` | 按板上 RST 键 | 这不是错, 是 boot 模式 |
| 容器 `xiaozhi-esp32-server` 不断重启 | `docker logs xiaozhi-esp32-server` 看 EOFError | 没下 FunASR `model.pt` (893 MB) |
| 喇叭说 "小智有点忙" / "请检查网络" | `tail /tmp/shim.log` 看 ConnectError | (a) DeepSeek key 错 (b) httpx async TLS bug → 用 `OPENAI_SHIM_BACKEND=hybrid` 走 openai SDK 路径 |
| voice 控舵机 voice OK 但舵机不动 | `docker logs mcp-endpoint-server \| grep "没有连接的MCP服务器"` | sidecar 抢了 ESP32 的 server 角色 → `pkill -9 -f xiaozhi_mcp_adapter`, 按 ESP32 RST 重连 |
| voice 转脚到一半被 docker 端 cut | docker LLM timeout 短 | data/.config.yaml 加 `LLM.DeepSeekLLM.timeout: 90` |

---

## Part 10 — 一键检查脚本

```bash
# scripts/preflight.sh (复制粘贴跑)
#!/bin/bash
set -e
echo "== Docker =="
docker ps --filter name=xiaozhi --format '{{.Names}}: {{.Status}}'
echo
echo "== 端口 LISTEN =="
ss -tln | grep -E ':(8000|8003|8004|8089)\s' || echo "❌ 缺端口"
echo
echo "== hermes 可用 =="
hermes -z "ping" 2>&1 | head -3 | tail -1
echo
echo "== ESP32 真连了 =="
docker logs xiaozhi-esp32-server 2>&1 | grep '工具数量' | tail -1
```

---

## 进一步学习

- 架构: [docs/architecture.md](architecture.md)
- 4 大模块: [README.md](../README.md#模块-m1-m4)
- 决策史: [docs/adr/INDEX.md](adr/INDEX.md)
- 已踩过的坑 (开发笔记): [docs/retros/week0.md](retros/week0.md)
- 答辩 demo 脚本: [docs/demo-script-h033.md](demo-script-h033.md)
