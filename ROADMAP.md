# Roadmap

> 项目正在从 GBU 期末作业 → 开源社区资产 转变。
> 短期目标是把 demo-quality 提升到 production-quality，长期目标
> 是把 ESP32-OttoRobot 做成 [Hermes Agent](https://github.com/NousResearch/hermes-agent)
> 上游官方支持的一具 channel。

## ✅ 已完成 (M1-M4 + H033 + H035)

- [x] **M1** `xiaozhi-mcp-adapter` — Python sidecar 接 mcp_endpoint pipe
- [x] **M2** `openai-shim` — OpenAI-compat FastAPI, 含 EchoBackend / DeepSeekBackend / HermesBackend (fork) / HermesAgentBackend / HybridBackend
- [x] **M3** `hermes-xiaozhi-plugin` — Hermes channel plugin (listener + HMAC verify + MessageEvent dispatch + adapter.send)
- [x] **M4** ESP32 端 MCP tools (show_emoji + show_text) — 14 tool 总数
- [x] **H033 ADR-0006** — voice → hermes-z → tool call → 喇叭真说 (实测端到端 13s, "查项目结构"成功)
- [x] **H035 ADR-0007** — Hybrid router: motor → raw DeepSeek + tools (舵机真动), 其余 → hermes-z (实测"挥挥手"真挥)

## 🚧 进行中

(none — Active queue 已清空)

## 📋 短期 (1-2 周)

### 必做 (production-ready)

- [ ] **H036 (next agent)**: 手机 channel + 飞书 OpenAPI tool 接入 (见 [docs/handoffs/active/2026-06-20-next-agent-bootstrap-036.md](docs/handoffs/active/2026-06-20-next-agent-bootstrap-036.md))
- [ ] **H032**: M3 batch auditor (rubric-based code review)
- [ ] **H037**: cron channel (hermes cron → ESP32 屏幕弹消息)
- [ ] **H038**: hybrid router 加 LLM-based intent classifier (现用 keyword, 误判率 < 5%)

### 可选 polish

- [ ] H034 sidecar 改走 `/call/` 让屏幕显字 dispatch 通 (兼容 H035 hybrid 模式)
- [ ] M4 加 show_qr tool (esp_qrcode ~350KB 挤余量, 用 'scan:<url>' 轻方案)
- [ ] M2 加 conversation memory: `hermes -z --continue <chat_id>` 串 session
- [ ] M1 sidecar 加 ESP32 reconnect retry (现是单次 connect, 断了不重试)

## 🌍 中期 (1-2 月)

- [ ] **多 channel mesh**: hermes cron / kanban / Discord 同时推送到同一台机器人
- [ ] **跟随声源转头**: ESP32 麦克风阵列 (现 1mic, 升级 2mic 算 DOA)
- [ ] **摄像头**: ESP32-S3 + OV2640 → hermes vision tool
- [ ] **PR 到 Hermes Agent**: 把 hermes-xiaozhi-plugin 上游
- [ ] **完整社区文档**: docs/cookbook/ 收集 10+ 实战用例

## 🚀 长期 (3-6 月)

- [ ] **支持其他 ESP32 板型** (esp-hi, BReady 等 7 个上游板)
- [ ] **多设备 mesh**: 一个 hermes session 控多台机器人
- [ ] **本地 LLM**: Ollama / vLLM 完全断网可用 (现需 DeepSeek 等云 API)
- [ ] **儿童陪伴模式**: 安全过滤 + 家长 web UI
- [ ] **车载模式**: HUD 显示 + 蓝牙连车
- [ ] **教育套件**: 简化版 SDK 给中小学 STEM 课用

## 关键决策史

见 [docs/adr/INDEX.md](docs/adr/INDEX.md).

## 贡献流程

见 [CONTRIBUTING.md](CONTRIBUTING.md).
