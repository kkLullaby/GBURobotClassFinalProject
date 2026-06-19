# 小智 AI 聊天机器人 — GBU 期末作业

> 🎓 **ESP32-S3 OttoRobot 形态 | 上游原版 + ESP-IDF 5.5.2**
>
> 本仓库直接跟随 [78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) 上游 `main` 分支，**未对源码或依赖做降级修改**。
> 子目录 `esp/xiaozhi-esp32/` 是上游仓库的 git submodule/gitlink，可随时 `git pull` 升级。

---

## 🌟 项目愿景

> **一句话定位：把 ESP32 小智机器人变成 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的第一具物理化身。**

机器人不再是"独立的语音助手"，而是一个开源、跑在本地、支持 20+ channel 的通用 AI 助手（Hermes Agent）的**新 channel + 设备工具集**。

| 你能做什么 | 怎么做 |
|----------|--------|
| 对着机器人说话，它接到 Hermes 处理 | xinnan-tech xiaozhi-server + 自写 openai-shim → Hermes |
| Telegram / 终端 / Discord 消息让机器人发声 | Hermes 的 `send_message_tool` 跨 channel 投递 |
| 让 LLM 控制机器人表情、动作、屏幕、LED | ESP32 扩展 MCP 工具，自写 adapter 暴露给 Hermes |
| 机器人主动通知（早安播报、PR 监控、消息提醒）| Hermes cron + xiaozhi channel 投递 |
| 把机器人留在现场，远程通过手机让它替你应答 | 跨 channel 消息投递（demo 场景二） |

**创新点（不是硬件，是拓扑）**：
- 把一个**仅活在终端和聊天软件里**的开源 AI 助手**物理化身**为一具能说话、能转头、能感知环境的桌面机器人
- **零私有协议** —— 全程标准 MCP + Hermes 标准 channel 接口
- **后端无关** —— LLM 可在 OpenAI/Anthropic/Ollama/Nous Portal/DeepSeek 等之间无缝切换
- **可作为 PR 贡献给 Hermes 社区**，可能成为它首个 ESP32 embodiment

---

## 📚 项目文档

| 文档 | 内容 |
|------|------|
| [`docs/architecture.md`](docs/architecture.md) | 高保真架构图、组件清单、协议层、选型理由 |
| [`docs/roadmap.md`](docs/roadmap.md) | 4 周路线图、验收标准、风险列表、降级方案 |
| [`docs/demo-script.md`](docs/demo-script.md) | 4 分钟答辩 Demo 脚本（含 8 个评委问答准备）|
| [`docs/research-notes.md`](docs/research-notes.md) | 选型调研笔记，可作课程报告"相关工作"章节素材 |

---

## 📋 项目简介

[小智 AI 聊天机器人](https://github.com/78/xiaozhi-esp32) 是一个开源的 ESP32-S3 智能语音助手项目。本仓库选用其中的 **OttoRobot 形态**（双足舵机机器人 + 小屏幕 + 麦克风 + 喇叭）作为期末作业硬件。

### 核心功能

- 🌐 Wi-Fi 连接 + 4G 网络（ML307，可选）
- 🎤 离线语音唤醒（ESP-SR）
- 🤖 流式 ASR → LLM → TTS 语音对话
- 🖥️ OLED / LCD 屏幕显示、表情动画
- 🦴 OttoRobot 双足舵机动作控制
- 📷 可选摄像头（OV2640 / OV3660）
- 🎛️ 网页 WebSocket 控制面板

---

## 🔧 环境要求

| 工具 | 版本 |
|------|------|
| Ubuntu | 22.04 / 24.04 |
| **ESP-IDF** | **v5.5.2 或更新**（上游硬性要求）|
| 目标芯片 | ESP32-S3 |
| Python | 3.8+ |

---

## 🚀 快速开始

### 1. 安装 ESP-IDF 5.5.2（一次性）

```bash
# 推荐独立安装一份，与可能存在的其他 IDF 版本分开
git clone -b v5.5.2 --recursive https://github.com/espressif/esp-idf.git ~/esp-idf-5.5.2
cd ~/esp-idf-5.5.2
./install.sh esp32s3

# ⚠️ 如果 clone 时没带 --recursive，必须立刻补这一句，否则后续 build 会崩
# （报 "Missing esp-mqtt submodule" 之类）。不要带 --depth=1，会在
# components/bt/controller/lib_esp32c3_family 处中断
git submodule update --init --recursive
```

每次新开终端都要激活：

```bash
source ~/esp-idf-5.5.2/export.sh
```

> 💡 建议在 `~/.bashrc` 加一个 alias：`alias get_idf552='source ~/esp-idf-5.5.2/export.sh'`

### 2. 克隆本仓库（含 submodule）

```bash
cd ~/code
git clone --recurse-submodules https://github.com/kkLullaby/GBURobotClassFinalProject.git
cd GBURobotClassFinalProject/esp/xiaozhi-esp32
```

> ⚠️ 如果忘了 `--recurse-submodules`，进项目后补一句：
> `git submodule update --init --recursive`

### 3. 选择板子类型 ⚠️ 关键步骤

```bash
source ~/esp-idf-5.5.2/export.sh
idf.py set-target esp32s3
idf.py menuconfig
```

进入 menuconfig 后：

```
→ Xiaozhi Assistant
  → Board Type
    → 选择  ottoRobot       ← 必须选这个！（Kconfig prompt 实际是小写 o + 驼峰）
```

> ❗ **默认是 `Bread Compact WiFi`（面包板版），引脚映射与 Otto 硬件完全不同**。
> 选错板子会导致烧录后屏幕黑屏、麦克风/喇叭无声、按键无响应。

保存退出（`S` → 回车 → `Q`）。

### 4. ⚠️ OTTO_ROBOT 板：menuconfig 之后必须 append 3 个 CONFIG

上游 README 漏说，但 `main/boards/otto-robot/config.json` 的 `sdkconfig_append`
要求 3 个 CONFIG，没有它们 build 会在 2206/2212 处崩
（`websocket_control_server.cc` 报 `httpd_ws_*` 未声明）：

```bash
cat >> sdkconfig <<'EOF'

# OTTO_ROBOT 板要求 (from main/boards/otto-robot/config.json sdkconfig_append)
CONFIG_HTTPD_WS_SUPPORT=y
CONFIG_CAMERA_OV2640=y
CONFIG_CAMERA_OV3660=y
EOF
```

### 5. 编译 + 烧录 + 串口监视

```bash
idf.py build flash monitor    # 全冷 build ~7 min
```

退出 monitor：`Ctrl + ]`

---

## 🔄 跟踪上游更新

```bash
# 进入子目录拉取 xiaozhi-esp32 最新代码
cd esp/xiaozhi-esp32
git fetch origin
git checkout main
git pull origin main

# 回到 super-repo，记录子模块新版本
cd ../..
git add esp/xiaozhi-esp32
git commit -m "chore: bump xiaozhi-esp32 to upstream main"
```

---

## 📁 仓库结构

```
final_pro_xiaozhi_robot/
├── .gitignore                  # 排除 build/、managed_components/、esp-idf/
├── README.md                   # 本文件
└── esp/
    └── xiaozhi-esp32/          # 78/xiaozhi-esp32 的 gitlink（上游原版）
        ├── main/boards/otto-robot/   # OttoRobot 板子专用代码
        ├── sdkconfig.defaults.esp32s3
        └── ...
```

> 📝 `esp/esp-idf/` 不入库 —— 开发者各自安装到 `~/esp-idf-5.5.2`。

---

## 🔍 常见问题

### Q: `idf.py set-target esp32s3` 时 version solving failed？

A: 确认 IDF 版本 ≥ 5.5.2：`idf.py --version`。若仍是 5.3.x，需要重新 source 5.5.2 的 `export.sh`。

### Q: 编译时找不到 `esp_video_init.h` 之类的头文件？

A: 通常是组件没拉全。在 `esp/xiaozhi-esp32/` 里执行：
```bash
rm -rf build managed_components dependencies.lock
idf.py reconfigure
```

### Q: 烧录后屏幕黑、按键无效？

A: **99% 是板子类型没选对**。重新 `idf.py menuconfig` → `Xiaozhi Assistant` → `Board Type` → `Otto Robot`。
改完后需要清干净再编：`rm -rf build sdkconfig && idf.py set-target esp32s3 && idf.py menuconfig`。

### Q: 我之前那一套 ESP-IDF 5.3.2 + 大量降级 hack 的代码呢？

A: 已经在 git 历史里。子目录 `esp/xiaozhi-esp32/` 的 `backup-pre-cleanup-20260616` 分支保留了当时的完整状态，可以 `git checkout backup-pre-cleanup-20260616` 切回去查看。

### Q: flash 后串口 `/dev/ttyUSB0` 不存在？

A: ESP32-S3 OttoRobot 用内置 USB-OTG，串口是 **`/dev/ttyACM0`** 不是 `ttyUSB0`。
先 `ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null` 看实际名字，再
`idf.py -p /dev/ttyACM0 flash monitor`。

### Q: flash 完后 monitor 卡在 `waiting for download`？

A: 烧完没自动 reset。**按板上 RST 键** 一下，板子进 normal boot，monitor
会立刻出现 `Booting` / `Free heap` 日志。不要 Ctrl+] 退出 monitor。

### Q: 第一次烧完没 wifi，怎么配？

A: 走 BluFi 蓝牙配网。用手机装 "EspBlufi" / "ESP-Touch" / 类似 app，扫到
ESP32 蓝牙广播后传 SSID + 密码。详细见上游
[`esp/xiaozhi-esp32/docs/blufi_zh.md`](esp/xiaozhi-esp32/docs/blufi_zh.md)。

### Q: 对机器人说"小智"，ASR 识别成"小子"？

A: 默认 FunASR SenseVoice 模型对"智"发音识别不稳；不影响 LLM 理解（DeepSeek
能从上下文猜出来），后期可换更精准的 ASR provider 解决。

---

## 🙏 致谢

- 上游项目 [78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) 及虾哥团队
- [Espressif ESP-IDF](https://github.com/espressif/esp-idf)
- OttoRobot 社区
