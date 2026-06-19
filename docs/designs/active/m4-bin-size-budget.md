---
status: current
created: 2026-06-19
scope: M4 (esp/xiaozhi-esp32/main/boards/otto-robot/)
source: H012 H1a baseline build (xiaozhi.bin, OTTO_ROBOT 板, IDF 5.5.2, esp32s3)
---

# M4 Binary Size Budget

> M4 在反豁免区 (`main/boards/otto-robot/`) 加 MCP tools 必须盯这个数。
> 超出 = link 失败 / 烧不进；逼近 = OTA 拍马屁 (双分区都得放得下)。

## Baseline (2026-06-19)

| 项 | 数值 | 来源 |
|---|---|---|
| `xiaozhi.bin` 当前 | **3,688,320 B** (3.5 MiB) | H012 build/xiaozhi.bin |
| app partition 单分区 | **4,128,768 B** (4032 KiB = 3.9 MiB+空头) | partition-table.csv `ota_0` |
| **剩余可用** | **440,448 B** (~430 KiB, 11%) | esptool `check_sizes.py` 输出 `0x6b880 bytes (11%) free` |
| spiffs assets 分区 | 8 MiB @ 0x800000 | 同上 |
| flash 总 | 16 MiB | OTTO_ROBOT 板默认 |

## Partition 内部约束

```
nvs        24K   @ 0x9000        # WiFi 配置/小数据，不动
otadata    8K    @ 0xd000        # OTA 切换记录
phy_init   4K    @ 0xf000
ota_0      4032K @ 0x20000       ← xiaozhi.bin 烧到这里，3.5 MiB + 440 KiB free
ota_1      4032K @ 0x410000      ← OTA 升级时用，必须放得下同一份 firmware
assets     8M    @ 0x800000      # spiffs，emoji gif / 字体
```

**双分区约束**：`ota_0` 和 `ota_1` 大小一致，OTA 必须能把新固件写入备用分区。
所以 M4 加的代码 **同时**占两份空间——只是 link 时验单分区，OTA 升级时验另一分区。
**预算 = min(ota_0, ota_1) free = 440 KiB**。

## M4 预算分配建议

| 预算项 | 推荐上限 | 用途 |
|---|---|---|
| MCP tool 代码 (otto_movements 扩展 / 新 tool) | ~150 KiB | C++ 业务代码 + 字符串 |
| LED / 状态相关 RTOS task | ~30 KiB | 短代码 + 任务栈 |
| 应急安全垫 | ~250 KiB | 给上游下次 minor bump 留余地（lvgl 9.x / esp-sr 任何 release） |

**逼近 350 KiB 占用 → 黄灯**，立刻起 ADR 讨论：删 default board 不用的代码、或换 16MB → 32MB flash 板、或上 NAPP 二次分区方案。

## 监控办法

```bash
# 任何 M4 修改后必须跑：
idf.py build
ls -la build/xiaozhi.bin                 # 看绝对值
idf.py size                              # 看各 component 占用排名
idf.py size-components | tail -30        # 看哪个 component 涨最快
idf.py size-files | grep otto-robot      # 看 OTTO_ROBOT 板自己加了多少
```

CI 化（可选，M4 进入后再考虑）：跑 build，grep `binary size 0x`，断言 < 0x3a0000。

## Why this lives in designs/ not contracts/

- 这是设计约束，不是跨栈接口
- 数值会随上游 bump 漂移（lvgl 9.5 → 9.6 可能涨 50 KiB）；每次 baseline rebuild 后更新本文件
- 引用方：[`docs/roadmap.md`](../../roadmap.md) §Week 2 M4 任务、未来 M4 设计文档

## History

- 2026-06-19 — H012 H1a 建立 baseline，11% free
