# Tech Stack

> 本项目的"事实"。所有角色都需要知道。
> 通过 CLAUDE.md `@import` 进每个 session。
> 这里**不**记会变的东西（那种东西放对应 rules/ 文件 + 代码侧 fact source）。

## 主要语言 / 框架

- **C++ (ESP-IDF v5.5.2)**：ESP32-S3 OttoRobot 固件，目标芯片 esp32s3
- **Python 3.8+**：M1 xiaozhi-mcp-adapter、M2 openai-shim、M3 Hermes plugin
- **Docker**：xinnan-tech xiaozhi-esp32-server 部署（minimal 模式，无 MySQL/Redis）

## 关键组件（M0-M4）

| ID | 组件 | 形态 | 状态 |
|----|------|------|------|
| M0 | xinnan-tech/xiaozhi-esp32-server | 现成 Docker | v0.9.4 (2026-06-03)，使用即可 |
| M1 | xiaozhi-mcp-adapter | Python service | 待写 |
| M2 | openai-shim | FastAPI 1-2 文件 | 待写 |
| M3 | Hermes xiaozhi channel plugin | Python plugin | 待写 |
| M4 | ESP32 端新 MCP tools | C++ 改 otto_robot.cc | 待写 |

## 上游依赖（只读，submodule）

- **`esp/xiaozhi-esp32/`** = [78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) main 分支
  - 板子型号必须选 `Xiaozhi Assistant → Board Type → Otto Robot`
- **ESP-IDF v5.5.2**（独立安装在 `~/esp-idf-5.5.2/`，不入库）
- **xinnan-tech/xiaozhi-esp32-server** v0.9.4

## 关键参考实现

- M1 抄哪个：[78/mcp-calculator/mcp_pipe.py](https://github.com/78/mcp-calculator)
- M3 抄哪个：Hermes 自带 `plugins/platforms/discord/adapter.py`
- M4 抄哪个：`esp/xiaozhi-esp32/main/boards/esp-hi/esp_hi.cc` (302-390 行 `AddTool` 示例)
- Week 0 参考 pin：Hermes Agent `426f321e84062e00fd5e6e9271aef48263cafffb`；xinnan-tech server `a1973e07b71e018199018060497c58cd45d5d387`

## 协议层

- **xiaozhi 私有 WebSocket**：ESP32 ↔ xinnan-tech server（Opus audio + JSON control，含 `{"type":"mcp", "payload": <JSON-RPC>}` 子帧）
- **标准 MCP（stdio / HTTP）**：M1 ↔ Hermes
- **OpenAI Chat Completions SSE**：xinnan-tech ↔ M2 openai-shim
- **xiaozhi MCP接入点 WS**：`ws://<server>:8004/mcp_endpoint/mcp/?token=...`（M1 反向连接此处）
- **Hermes 自定义 channel API**：M3 实现 `BasePlatformAdapter` ABC

## 数据库 / 外部服务

- 无（minimal 模式下 xinnan-tech 不用 MySQL/Redis）
- LLM provider 走环境变量，可在 OpenAI/Anthropic/Ollama/Nous Portal/DeepSeek 间切换
