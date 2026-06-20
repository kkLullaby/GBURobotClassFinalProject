# ottagent

> **把开源 AI Agent 装进 ESP32 桌面机器人 — voice → tool-call → 真做事 (舵机真动, 喇叭真说)**
>
> [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![ESP-IDF](https://img.shields.io/badge/ESP--IDF-5.5.2-blue.svg)](https://github.com/espressif/esp-idf) [![Python](https://img.shields.io/badge/Python-3.10+-brightgreen.svg)](https://www.python.org/) [![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-purple.svg)](https://github.com/NousResearch/hermes-agent)
>
> 中文 | [English](#english)
>
> 大湾区大学 (GBU) 机器人课期末作业 — **完整复刻教程开放, 任何人可以照着搭一台**.

---

## ✨ 一句话定位

把 ESP32-S3 OttoRobot 变成 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的第一具**物理化身**——不是又一个智能音箱，而是一个**能听话、真做事**的桌面 AI 助手：

- 你说 **"挥挥手"** → **舵机真挥**（DeepSeek 经 hybrid router 调 `self_otto_action(hand_wave)`）
- 你说 **"帮我看 final 文件夹有什么"** → 喇叭说出真目录名（hermes-z 真跑 `ls` + DeepSeek 总结）
- 你说 **"用 git log 看最近三次提交"** → 喇叭说真 commit 信息

**真在做事，不是录音回放。**

## 🎬 Demo

> 占位: 项目演示视频会贴在 [Releases](../../releases) 或者 [demo-script-h033.md](docs/demo-script-h033.md) 录屏链接.

| Take | 你讲 | 路由 | 喇叭/物理 |
|---|---|---|---|
| 1 | "挥挥手" | DeepSeek + tools | 🤚 **手真挥** |
| 2 | "向前走两步" | DeepSeek + tools | 👣 **真走** (servo 真转) |
| 3 | "坐下" | DeepSeek + tools | 🪑 **真坐** |
| 4 | "帮我看 final 文件夹有什么目录" | hermes-z + shell tool | 🔊 "目录有 5 个: docs, esp, openai-shim..." |
| 5 | "现在几点了" | hermes-z + date tool | 🔊 "现在是 X 点 X 分" |
| 6 | "读 README 告诉我项目目标" | hermes-z + file tool | 🔊 elevator pitch |

## 🎯 创新点 (在拓扑, 不在硬件)

| | 智能音箱 (小爱 / 天猫) | ottagent |
|---|---|---|
| 后端 | 厂商私有, 锁死 | OpenAI 兼容, 可换 (DeepSeek/Claude/Ollama/Nous Portal) |
| 协议 | 私有 ws/RPC | 标准 OpenAI Chat + MCP + Hermes channel ABI |
| Tool 扩展 | 内置 skill (Alexa 风) | hermes-z + 任意 MCP server (shell/file/browser/lark/...) |
| Channel mesh | 单设备 | hermes 多 channel 联动 (cron / telegram / discord / 飞书 / ...) |
| 物理动作 | 无 | OttoRobot 26 个舵机动作 + 21 个 emoji + 屏幕显字 |
| 开源 | ❌ | ✅ (MIT) |

可作为 PR 贡献给 Hermes 社区, 成为它官方支持的首个 ESP32 embodiment.

## 🏗️ 架构

```
ESP32-S3 OttoRobot ←─── WiFi ───→ xinnan-tech docker server (STT/TTS/WebSocket)
                                            ↓ OpenAI-compat HTTP
                                    openai-shim (FastAPI)
                                            ↓ Hybrid Router 看 user text
                            ┌───────────────┴───────────────┐
                       motor keyword (走/挥/坐/笑/...)   其余 (查/读/总结/聊天)
                            ↓                                 ↓
                  raw_deepseek_proxy (tools 透传)      HermesAgentBackend
                            ↓                                 ↓
                  DeepSeek tool_calls                   hermes -z PROMPT --yolo
                            ↓                                 ↓
                  xinnan-tech execute                   hermes agent + MCP tools
                            ↓                            (shell/file/git/browser/...)
                  mcp_endpoint /call/ → ESP32                ↓
                            ↓                            stdout → SSE → 喇叭说
                       🤖 舵机真动                          🔊
```

详见 [docs/architecture.md](docs/architecture.md) + ADR [0005](docs/adr/0005-openai-compat-transcript-egress.md) / [0006](docs/adr/0006-hermes-agent-backend-voice-replace-llm.md) / [0007](docs/adr/0007-hybrid-backend-router.md).

## 🚀 Quickstart

> ⏱️ **新机器从 0 到真挥手**: 约 3 小时.
> 详细完整指南 → **[docs/DEPLOY.md](docs/DEPLOY.md)**

```bash
# 1. Clone (含 submodule)
git clone --recurse-submodules https://github.com/kkLullaby/ottagent.git
cd ottagent

# 2. 起 docker (xinnan-tech 后端 — 自己 clone + 配 LLM key)
#   见 docs/DEPLOY.md Part 3

# 3. 装 Python 包 + Hermes Agent
for pkg in xiaozhi-mcp-adapter openai-shim hermes-xiaozhi-plugin; do
  (cd $pkg && uv pip install --system -e '.[test]')
done
uv tool install hermes-agent
hermes auth add deepseek --api-key 'sk-<你的 DeepSeek key>'

# 4. 烧 ESP32 (一次性)
source ~/esp-idf-5.5.2/export.sh
cd esp/xiaozhi-esp32 && idf.py set-target esp32s3
idf.py menuconfig    # Board Type → ottoRobot
# (append OTTO_ROBOT 3 个 CONFIG, 见 DEPLOY.md Part 6)
idf.py -p /dev/ttyACM0 build flash monitor

# 5. 起 shim (hybrid 模式)
cd openai-shim
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
nohup env \
  OPENAI_SHIM_BACKEND=hybrid \
  DEEPSEEK_API_KEY='sk-<你的 key>' \
  HERMES_BIN=$(which hermes) \
  PYTHONPATH=src python -m uvicorn openai_shim.app:app \
    --host 0.0.0.0 --port 8089 \
  > /tmp/shim.log 2>&1 & disown

# 6. 对机器人讲 "挥挥手" 🤚
```

## 🧩 模块 (M1-M4)

| 模块 | 路径 | 作用 | LOC |
|---|---|---|---|
| **M1** | `xiaozhi-mcp-adapter/` | Python sidecar, 接 mcp_endpoint pipe (现 H035 hybrid 不依赖, 见 ADR-0007) | ~600 |
| **M2** | `openai-shim/` | FastAPI OpenAI 兼容 shim, **5 backend** + **hybrid router** | ~500 |
| **M3** | `hermes-xiaozhi-plugin/` | Hermes channel plugin (HMAC verify + MessageEvent dispatch) | ~250 |
| **M4** | `esp/xiaozhi-esp32/main/boards/otto-robot/` | ESP32 端 MCP tools (上游 12 + 自加 2: show_emoji + show_text = **14 个**) | ~70 |

**总自写代码 ~1.4k LOC** (Python + C++).

## 🔌 Channels (已接 + 计划)

| Channel | 状态 | Handoff |
|---|---|---|
| xiaozhi (ESP32 voice) | ✅ 已接 | M1+M3+M4 |
| hermes terminal (TUI) | ✅ 内置 | hermes 自带 |
| webhook (HTTP POST) | ✅ 内置 | hermes 自带 |
| Discord | ✅ 内置 | hermes 自带 |
| Slack | ✅ 内置 | hermes 自带 |
| Telegram | ✅ 内置 | hermes 自带 |
| 飞书 (Lark) | 📋 计划 (H036) | [docs/handoffs/active/...036.md](docs/handoffs/active/2026-06-20-next-agent-bootstrap-036.md) |
| 微信 | 📋 计划 | (受 API 限制, polish 项) |
| Cron (定时触发) | ✅ 部分 (需 channel registry 注册 cron_deliver) | (H037) |

## 🎓 关键决策

| ADR | 决定 | 影响 |
|---|---|---|
| [0001](docs/adr/0001-adopt-agent-arch.md) | 采纳三角色 agent 协作 (planner/executor/auditor) | 整个开发流程 |
| [0005](docs/adr/0005-openai-compat-transcript-egress.md) | M3 transcript 走 OpenAI-compat messages, 不走 MCP callback | 实现量 5-6 → 1-2 天 |
| [0006](docs/adr/0006-hermes-agent-backend-voice-replace-llm.md) | voice → hermes-z 替换 LLM (项目最终形态) | 答辩高光 |
| [0007](docs/adr/0007-hybrid-backend-router.md) | Hybrid router: motor → raw DeepSeek+tools; 其余 → hermes-z | 保留舵机能力 + 保留 hermes 工具能力 |

完整列表: [docs/adr/INDEX.md](docs/adr/INDEX.md).

## 📚 项目文档

| 文档 | 内容 |
|---|---|
| [docs/DEPLOY.md](docs/DEPLOY.md) | **完整部署指南** (硬件 BOM + 软件依赖 + 一键 quickstart + troubleshooting) |
| [docs/architecture.md](docs/architecture.md) | 高保真架构图、组件清单、协议层 |
| [docs/adr/INDEX.md](docs/adr/INDEX.md) | 7 个架构决策记录 |
| [docs/demo-script-h033.md](docs/demo-script-h033.md) | 答辩 demo 脚本 (6 take + Q&A + 数据页) |
| [docs/handoffs/INDEX.md](docs/handoffs/INDEX.md) | 35+ 开发 handoff 流水 (从 hello world 到 voice 真闭环) |
| [docs/retros/week0.md](docs/retros/week0.md) | 第 1 周复盘 (16 bitter lessons) |
| [CLAUDE.md](CLAUDE.md) | 三角色 agent 协作纪律 (给 AI 助手用) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 |
| [ROADMAP.md](ROADMAP.md) | 短期/中期/长期路线图 |
| [docs/xiaohongshu-drafts.md](docs/xiaohongshu-drafts.md) | 3 版小红书宣传文案 |

## 🛠️ 开发

```bash
# 跑各模块测试 (31 tests total)
cd xiaozhi-mcp-adapter && PYTHONPATH=src python -m pytest tests/   # 6/6
cd openai-shim && PYTHONPATH=src python -m pytest tests/           # 20/20
cd hermes-xiaozhi-plugin && PYTHONPATH=src python -m pytest tests/ # 5/5

# 看 hermes 真实时 reason
tail -f ~/.hermes/logs/agent.log
```

## 🙏 致谢

- 上游 [78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) (虾哥 + 社区)
- [Nous Research / Hermes Agent](https://github.com/NousResearch/hermes-agent)
- [xinnan-tech / xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server)
- [Espressif ESP-IDF](https://github.com/espressif/esp-idf) + ESP-SR + ESP-CAM
- [DeepSeek](https://www.deepseek.com/) (主要 LLM 后端, 也支持 OpenAI / Anthropic / Ollama / Nous Portal)
- 大湾区大学机器人课师生 (项目摇篮)

## 📜 LICENSE

[MIT](LICENSE).

子模块 `esp/xiaozhi-esp32/` 是上游 78/xiaozhi-esp32 (MIT) 的 gitlink, 未修改源码.

---

## English

**ottagent** — embedding open-source AI Agent into an ESP32-S3 desktop robot.

### One-liner

Make the ESP32-S3 OttoRobot the first **physical embodiment** of [Hermes Agent](https://github.com/NousResearch/hermes-agent). Not yet another smart speaker — a desktop AI assistant that **listens and actually does things**:

- Say **"wave hand"** → 🤚 servo really moves (DeepSeek via hybrid router calls `self_otto_action(hand_wave)`)
- Say **"check final folder contents"** → 🔊 speaker reads real directory names (hermes-z really runs `ls` + DeepSeek summarizes)
- Say **"git log latest 3 commits"** → 🔊 speaker reads real commit info

**Really doing things, not playback.**

### Innovation (in topology, not hardware)

| | Smart speaker (Alexa-like) | ottagent |
|---|---|---|
| Backend | Vendor-locked | OpenAI-compatible, swappable |
| Protocol | Proprietary RPC | Standard MCP + Hermes channel ABI |
| Tool extension | Built-in skills | hermes-z + any MCP server |
| Channel mesh | Single device | hermes multi-channel coordination |
| Physical actions | None | OttoRobot 26 servo motions + 21 emojis + screen text |
| Open source | ❌ | ✅ (MIT) |

### Architecture

```
ESP32-S3 OttoRobot ←── WiFi ──→ xinnan-tech docker server (STT/TTS/WebSocket)
                                          ↓ OpenAI-compat HTTP
                                  openai-shim (FastAPI)
                                          ↓ Hybrid Router on user text
                           ┌──────────────┴──────────────┐
                    motor keyword              other (query/chat)
                           ↓                              ↓
                  raw_deepseek_proxy            HermesAgentBackend
                  (tools passthrough)           (hermes -z + tools)
                           ↓                              ↓
                   DeepSeek tool_calls           shell/file/git/browser/...
                           ↓                              ↓
                  xinnan-tech execute            stdout → SSE → speaker
                           ↓
                  mcp_endpoint /call/ → ESP32
                           ↓
                       🤖 servo moves                    🔊 speaks
```

### Quickstart

See [docs/DEPLOY.md](docs/DEPLOY.md) for full setup (BOM → working demo in ~3 hours).

### Modules

| Module | Path | Purpose | LOC |
|---|---|---|---|
| **M1** | `xiaozhi-mcp-adapter/` | Python sidecar bridging xiaozhi MCP endpoint | ~600 |
| **M2** | `openai-shim/` | FastAPI OpenAI-compat shim + hybrid router | ~500 |
| **M3** | `hermes-xiaozhi-plugin/` | Hermes channel plugin | ~250 |
| **M4** | `esp/xiaozhi-esp32/main/boards/otto-robot/` | ESP32 MCP tools (14 total: 12 upstream + 2 added) | ~70 |

Total self-written: ~1.4k LOC.

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome for: new channels (Lark, Telegram), MCP tools, hardware variants, translations, replica showcases.

### License

[MIT](LICENSE).
