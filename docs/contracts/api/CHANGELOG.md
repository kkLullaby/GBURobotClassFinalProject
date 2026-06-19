# Contracts API Changelog

> 跨版本变更记录。每条 ≤3 行，附 contract 文件 + 触发它的 ADR/handoff。
> 老条目不删；deprecated 的整版本归 `deprecated/`。

## 2026-06-19

- **v1/esp32-to-server-handshake.md** new. baseline (`78/xiaozhi-esp32@b392c63`
  + xinnan-tech server `a1973e0`) 的 WebsocketProtocol 握手 + JSON 控制帧 +
  MCP 子帧 + xinnan-tech MCP 接入点对比。触发：H012 H1a build done 后 P0 contract。
  影响：M1 / M2 / M3 / M4 都需读，但**尚不修改**（H1b 验证完 §8 实测后才解锁
  M1 开工）。
- **v1/esp32-to-server-handshake.md §4.2.bis + §8.bis** appended (H1b 跑通后
  回灌)。§4.2.bis 记 server 在 hello 后自动发 MCP `initialize`（含 `vision`
  capability + JWT），§8.bis 记 baseline 端到端实测数据（MAC / IP / 串口
  ACM 不是 USB / RTT 等）。非 breaking change，v1 自然延伸。
