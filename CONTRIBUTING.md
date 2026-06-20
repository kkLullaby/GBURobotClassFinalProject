# Contributing

> 中文 | [English](#english)

欢迎为 **ottagent** 做出贡献！本项目把 ESP32-S3 OttoRobot 变成了
[Hermes Agent](https://github.com/NousResearch/hermes-agent) 的第一具
物理化身，欢迎以下几种贡献方式。

## 你可以贡献什么

| 类型 | 示例 |
|---|---|
| **新 channel** | 接入飞书 / 钉钉 / Telegram / WhatsApp / 微信公众号 (M3 plugin) |
| **新 MCP tool** | 给 hermes-z 加飞书 OpenAPI 调用 / 钉钉群消息 / 第三方 LLM 等 |
| **新硬件** | 移植到其他 ESP32 板型 / 加摄像头 / 加触摸屏 |
| **新功能** | 让机器人主动巡逻 / 跟随声源转头 / 多设备 mesh |
| **文档翻译** | 英文 / 日文 / 韩文 README / DEPLOY.md |
| **复刻案例** | 你自己做了一台 → 拍照 + 短视频, 我们贴到 README 案例墙 |

## 开始之前

1. **读完 [README.md](README.md) 和 [docs/DEPLOY.md](docs/DEPLOY.md)**
2. 看 [docs/architecture.md](docs/architecture.md) 理解四层架构 (M1-M4)
3. 看 [docs/adr/INDEX.md](docs/adr/INDEX.md) 了解关键架构决策
4. 在 [GitHub Issues](../../issues) 找 `good first issue` 或 `help wanted` 标签

## 开发流程

```bash
# 1. Fork + clone
git clone --recurse-submodules https://github.com/<你的 fork>/ottagent.git
cd ottagent

# 2. 创建特性分支
git checkout -b feat/lark-channel

# 3. 跑本地测试 (各模块独立)
cd openai-shim     && PYTHONPATH=src python -m pytest tests/  # 20/20 应 PASS
cd ../xiaozhi-mcp-adapter && PYTHONPATH=src python -m pytest tests/  # 6/6 应 PASS
cd ../hermes-xiaozhi-plugin && PYTHONPATH=src python -m pytest tests/  # 5/5 应 PASS

# 4. 提 PR 到 main 分支
git push origin feat/lark-channel
# 然后到 GitHub 开 Pull Request
```

## PR 检查清单

提 PR 前请确认：

- [ ] 新代码有对应测试 (≥ 1 case)
- [ ] 现有测试全 PASS (3 个 Python 包 + ESP-IDF build 若改了 esp/)
- [ ] 改了架构决策 → 写新 ADR `docs/adr/NNNN-<title>.md`
- [ ] **绝不**把 API key / token / 密码 commit 进 git
- [ ] commit message 简洁 + 说明 why (不只是 what)
- [ ] PR 描述含: 改了什么 / 为什么 / 怎么测的

## Coding style

- **Python**: PEP 8, 4 space, double quotes 字符串. 命名 snake_case.
- **C++ (ESP-IDF)**: 跟 upstream `78/xiaozhi-esp32` 风格走 (2 space, CamelCase class).
- **Commit message**: 中英文都行, 但首行 ≤ 72 char.

## 文档与代码同步

如果你新增了一个：
- **Python 模块** → 加 README.md 段落或更新 `docs/architecture.md`
- **MCP tool** → 更新 `docs/contracts/` 里相关 .md
- **新 channel** → 加到 [README.md 的 Channels 表格](README.md#channels)

## Bitter lessons (开发踩坑笔记)

本项目维护一份 [bitter lessons 列表](docs/retros/) — 你踩了坑后,
请把根因写进对应 handoff 的 What I Did, 留给后人.

## 大方向 (Roadmap)

见 [ROADMAP.md](ROADMAP.md).

---

## English

Welcome contributing to **ottagent** — making ESP32-S3 OttoRobot
the first physical embodiment of [Hermes Agent](https://github.com/NousResearch/hermes-agent).

### How to contribute

- New channels (Lark, DingTalk, Telegram, WhatsApp, WeChat MP, ...)
- New MCP tools for hermes-z
- New hardware variants
- Translations
- Replica show-and-tell (we'll feature on README)

### Workflow

1. Fork, clone with `--recurse-submodules`
2. Branch
3. Run tests in each Python package
4. Open PR to `main` with clear description

### PR Checklist

- [ ] Tests added for new code
- [ ] All existing tests pass
- [ ] New ADR if architecture changed
- [ ] No secrets committed
- [ ] Concise commit msg explaining "why"

See full Chinese version above for detail.
