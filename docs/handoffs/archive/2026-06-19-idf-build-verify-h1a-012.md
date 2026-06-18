---
id: 2026-06-19-idf-build-verify-h1a-012
from: planner
to: executor
status: done
parent:
created: 2026-06-19
artifacts:
  - esp/xiaozhi-esp32/sdkconfig (新建; gitignored)
  - esp/xiaozhi-esp32/build/    (新建; gitignored; ~1GB)
  - esp/xiaozhi-esp32/managed_components/  (新建; gitignored)
---

## Objective

H1a: 用用户刚装好的 IDF 5.5.2（`~/esp-idf-5.5.2/`）在 `esp/xiaozhi-
esp32/`（已是 submodule pin `b392c63`）跑：

1. `idf.py set-target esp32s3`
2. `idf.py menuconfig` 选板子型号 `ottoRobot`（注意：实际 Kconfig
   prompt 是小写 o 驼峰 `"ottoRobot"`，不是 README 写的 "Otto Robot"）
3. `idf.py build`

只为验证**本机工具链 + 上游代码本机能编**。**不**插 USB、**不** flash、
**不** monitor。H1b (flash) 等 USB 线 + H011 docker 起来后另起。

## Constraints

- 不动 `esp/xiaozhi-esp32/` git 跟踪的任何源码（sdkconfig/build/
  managed_components 都已 gitignored，写出来不算"动"）
- 不切上游 commit（保持 `b392c63`）
- 不 flash、不连真设备、不 monitor
- 错误处理纪律见 §Error-handling discipline
- 第一次 `idf.py build` 慢（10-20 min 编译全套上游 + ESP-SR + LVGL），
  这是预期，**不**算 block
- 编译过程会下 managed_components（espressif 仓库），网络一次走完，
  这是预期；走 5-30 min，**不**算 block

## Acceptance Criteria

- [ ] `idf.py --version` 输出 `ESP-IDF v5.5.2`
- [ ] `idf.py set-target esp32s3` 成功（CMake configure 无 error）
- [ ] menuconfig 完成后 `grep -E 'CONFIG_BOARD_TYPE.*=y' esp/xiaozhi-
      esp32/sdkconfig` 含 `CONFIG_BOARD_TYPE_OTTO_ROBOT=y`
- [ ] `idf.py build` 跑完无 error，最后一行类似 `Project build complete.
      To flash, run: idf.py flash`
- [ ] `ls esp/xiaozhi-esp32/build/xiaozhi.bin` 存在，文件大小 > 1 MB
      （上游 firmware 实际产物名可能是 `xiaozhi-esp32.bin` 或类似；
      `ls esp/xiaozhi-esp32/build/*.bin` 列出有 ≥1 个 ≥1 MB 的 bin
      即可）
- [ ] 把以下信息（≤15 行 memo）贴 What I Did：
      - 实际跑到的编译耗时（壁钟时间）
      - flash 出的 partition layout（`idf.py partition-table` 输出末段）
      - 任何 warning 计数（grep `warning:` build 输出）
      - sdkconfig 关键行（`grep -E 'CONFIG_(BOARD_TYPE|IDF_TARGET|XIAOZHI)' sdkconfig`）

## Context Pointers

- @docs/adr/0002-week0-baseline-correction.md §不符 3 (H1a/H1b 拆段动机)
- @docs/adr/0001-adopt-agent-arch.md §"本项目特有 pitfall" #1 (板子型号
  选错黑屏无声) + #2 (IDF 必须 5.5.2) + #3 (managed_components 缺时清干净)
- @docs/handoffs/archive/2026-06-19-xinnan-server-bringup-008.md (A 段
  diagnosis：baseline 不能不重烧切 URL，所以 H1a 必须验证本机能 build，
  H1b 必须发)
- @CLAUDE.md §常用命令 + §Project Scope (esp/xiaozhi-esp32/ 默认只读，
  本任务的写都在 gitignored 路径下)
- @.claude/memory/shared/global-commands.md §ESP32 编译/烧录/监视
- @docs/adr/0003-executor-runs-in-main-loop.md (main loop / codex 跑；
  sandbox 大概率写不了 `~/esp-idf-5.5.2/python_env` 之类的更新路径)
- 上游 README: `esp/xiaozhi-esp32/README_zh.md`
- 板子源码: `esp/xiaozhi-esp32/main/boards/otto-robot/` (15 个文件)

## Out of Scope

- **不 flash**、不连 USB、不 monitor
- 不动 `CONFIG_OTA_URL`（H1b 才改 URL 指向本地 server）
- 不改任何 board 配置（除了选 `BOARD_TYPE_OTTO_ROBOT`）
- 不写 M4 任何 MCP 工具代码
- 不动 main/ 任何源码

## Suggested Steps

```bash
# 0. 激活 IDF
source ~/esp-idf-5.5.2/export.sh
idf.py --version    # 期望 ESP-IDF v5.5.2

cd esp/xiaozhi-esp32

# 1. 设 target
idf.py set-target esp32s3

# 2. menuconfig 选板子
#    导航：Xiaozhi Assistant → Board Type → ottoRobot
#    保存：S → Enter → Q
idf.py menuconfig

# 3. 验板子选对
grep -E 'CONFIG_BOARD_TYPE.*=y' sdkconfig
# 期望：CONFIG_BOARD_TYPE_OTTO_ROBOT=y

# 4. build（慢，10-20 min）
time idf.py build 2>&1 | tee /tmp/h1a-build.log

# 5. 验产物
ls -la build/*.bin
idf.py partition-table 2>&1 | tail -20
grep -c 'warning:' /tmp/h1a-build.log

# 6. 看是否被 managed_components 缺失之类的坑卡住
# 如果 build 失败且报缺头文件（如 esp_video_init.h）：
#   rm -rf build managed_components dependencies.lock
#   idf.py reconfigure
#   重新 idf.py build
```

## Error-handling discipline

按 H010 §"Error-handling discipline" 全文执行：
- cosmetic 错（命令打错）自己改命令重试
- substantive 错（CMake error / link error / 缺组件）→ status: blocked
  + 完整 stderr + 已 grep 的关键行
- 第一次 build 慢（>10 min）不算 block

## Recovery

- menuconfig 找不到 ottoRobot：在 menuconfig 里按 `/` 搜索 `OTTO_ROBOT`
  跳转过去；如果还没有，`grep -rn BOARD_TYPE_OTTO_ROBOT esp/xiaozhi-
  esp32/main/Kconfig.projbuild` 应该有命中
- managed_components 缺组件 / version 冲突：
  ```bash
  cd esp/xiaozhi-esp32
  rm -rf build managed_components dependencies.lock
  idf.py reconfigure
  idf.py build
  ```
- IDF env 没激活（`idf.py: command not found`）：必须先 `source
  ~/esp-idf-5.5.2/export.sh`（建议 alias `get_idf552`）

## For Auditor

不发 auditor。M1 开工前 planner 自审；H1b done 后会一起 batch audit。

## Executor's Reading
### What I'll do
- 用 `~/esp-idf-5.5.2/export.sh` 激活 IDF，在 `esp/xiaozhi-esp32/` 保持 `b392c63`，设置 `esp32s3` target、选择 `ottoRobot` 板型、运行 build，并把版本、产物、partition、warning、sdkconfig 关键信息记录回 handoff。

### Assumptions made
- [LOW] `sdkconfig`、`build/`、`managed_components/`、`dependencies.lock` 是本任务明确允许的 gitignored 编译产物；不会修改 submodule 跟踪源码。
- [LOW] 只做 build 验证，不 flash、不 monitor、不连接设备。
- [MED] 如果 `idf.py menuconfig` 的 TUI 无法在当前非交互工具环境稳定操作，我会使用等价的 sdkconfig/Kconfig 配置方式把 `CONFIG_BOARD_TYPE_OTTO_ROBOT=y` 落到 `sdkconfig`，再用 grep 和 build 结果验证；这不改变上游源码。

## What I Did
- 已确认 `source ~/esp-idf-5.5.2/export.sh && idf.py --version` 可运行，输出 `ESP-IDF v5.5.2-dirty`。
- 已确认 `esp/xiaozhi-esp32/` HEAD 为 `b392c630aa74bc9bb0ff5791bb89b1d8c96b3181`，运行前无 submodule 跟踪源码改动。
- 执行 `source ~/esp-idf-5.5.2/export.sh && idf.py set-target esp32s3`，在 CMake configure / component dependency solving 阶段失败，退出码 2。
- 阻塞原因：当前宿主环境无法连接 Espressif component registry 拉取 `78/esp-ml307` 组件元数据；这是 substantive CMake error，不是 cosmetic 命令错误。
- 失败后未继续 `menuconfig` / `build` / `partition-table`，未 flash、未 monitor。
- 完整 stderr：

```text
Command: cmake -G Ninja -DPYTHON_DEPS_CHECKED=1 -DPYTHON=/home/kk/.espressif/python_env/idf5.5_py3.13_env/bin/python -DESP_PLATFORM=1 -DIDF_TARGET=esp32s3 -DCCACHE_ENABLE=0 /home/kk/code/robot_class/final_pro_xiaozhi_robot/esp/xiaozhi-esp32
CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/bt/controller/lib_esp32c5/esp32c5-bt-lib is out of
  date.  Run the following command to fix: git submodule update --init
  --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/bt/controller/lib_esp32c6/esp32c6-bt-lib is out of
  date.  Run the following command to fix: git submodule update --init
  --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/bt/controller/lib_esp32h2/esp32h2-bt-lib is out of
  date.  Run the following command to fix: git submodule update --init
  --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/bt/esp_ble_mesh/lib/lib is out of date.  Run the
  following command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/bt/host/nimble/nimble is out of date.  Run the
  following command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/cmock/CMock is out of date.  Run the following
  command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/esp_coex/lib is out of date.  Run the following
  command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/esp_phy/lib is out of date.  Run the following
  command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/esp_wifi/lib is out of date.  Run the following
  command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/heap/tlsf is out of date.  Run the following
  command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/json/cJSON is out of date.  Run the following
  command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/lwip/lwip is out of date.  Run the following
  command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/mbedtls/mbedtls is out of date.  Run the following
  command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/mqtt/esp-mqtt is out of date.  Run the following
  command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/openthread/lib is out of date.  Run the following
  command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/openthread/openthread is out of date.  Run the
  following command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/protobuf-c/protobuf-c is out of date.  Run the
  following command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/spiffs/spiffs is out of date.  Run the following
  command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Warning at /home/kk/esp-idf-5.5.2/tools/cmake/git_submodules.cmake:52 (message):
  Git submodule components/unity/unity is out of date.  Run the following
  command to fix: git submodule update --init --recursive
Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:109 (git_submodule_check)
  /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:282 (__build_get_idf_git_revision)
  /home/kk/esp-idf-5.5.2/tools/cmake/idf.cmake:55 (__build_init)
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:29 (include)
  CMakeLists.txt:8 (include)


CMake Error at /home/kk/esp-idf-5.5.2/tools/cmake/build.cmake:629 (message):
  ERROR: Cannot establish a connection to the component registry.  Are you
  connected to the internet?

  URL: https://components-file.espressif.com/components/78/esp-ml307.json

Call Stack (most recent call first):
  /home/kk/esp-idf-5.5.2/tools/cmake/project.cmake:740 (idf_build_process)
  CMakeLists.txt:13 (project)
```

## Open Questions for Auditor
- 无；本 handoff 写明不发 auditor。原 blocked 状态记录在上方"完整 stderr"段（codex sandbox 无 proxy → registry 不通），由 planner main-loop 接管并 unblock 跑通，详见下方 §"Unblock + Build SUCCESS (planner main-loop, 2026-06-19)"。

---

## Unblock + Build SUCCESS (planner main-loop, 2026-06-19)

> ADR-0003 类型 II 代跑：codex sandbox 无 proxy + IDF submodules 未初始化，
> planner 主会话有 `https_proxy=127.0.0.1:7897`、有 docker、有 IDF env，
> 接管 H012 全程跑通。

### Unblock 路径（按发现顺序）

1. **真因 1 — codex sandbox 缺 proxy env**：原 stderr 说 "Cannot establish
   a connection to ... `components-file.espressif.com`"。planner 本会话
   `curl -x http://127.0.0.1:7897 https://components-file.espressif.com/components/78/esp-ml307.json`
   立刻 HTTP 200；直裸连 TLS unexpected eof。codex 进程没继承 shell 的
   `https_proxy`/`http_proxy`/`HTTPS_PROXY`/`HTTP_PROXY`。
2. **真因 2 — `~/esp-idf-5.5.2/` 自身的 git submodule 未初始化**：用户
   昨天装 IDF 时漏跑 `git submodule update --init --recursive`。第一次
   set-target 报 "Missing esp-mqtt submodule. Please run `git submodule
   update --init --recursive` in ESP-IDF directory to fix this"。
3. **真因 2 修复中坑**：`git submodule update --init --recursive --depth=1`
   会在 `lib_esp32c3_family` 处中断（fetch shallow + commit pin 非 branch
   tip）→ 残留 `refs/heads/.invalid` ref + 临时 pack → 后续 init 全卡。
   修复：手工 `rm -rf .git/modules/components/bt/controller/lib_esp32c3_family`
   + `rm -rf components/bt/controller/lib_esp32c3_family` + 重 init 不带
   `--depth=1`。最终全部 submodule 收回到 0 个 uninit。
4. **真因 3 — OTTO_ROBOT 板必须 append 3 个 CONFIG**：第一次 build 跑到
   2206/2212 个 obj 后 fail，`websocket_control_server.cc` 报 `httpd_ws_*`
   API 未声明。`main/boards/otto-robot/config.json` 已写明
   `sdkconfig_append: [CONFIG_HTTPD_WS_SUPPORT=y, CONFIG_CAMERA_OV2640=y,
   CONFIG_CAMERA_OV3660=y]`，但 `idf.py menuconfig` 流程不自动应用——
   这是 78/xiaozhi-esp32 上游 README 漏说的项目 fact。修复：手工 append
   到 sdkconfig 末尾。

### 流程实际跑（按 AC 顺序贴）

```bash
# IDF 5.5.2 submodules
cd ~/esp-idf-5.5.2 && git submodule update --init --recursive  # ~15 min
# 验：git submodule status | grep -c '^-'  →  0

# 本仓库
cd ~/code/robot_class/final_pro_xiaozhi_robot/esp/xiaozhi-esp32
rm -rf build managed_components dependencies.lock sdkconfig sdkconfig.old
source ~/esp-idf-5.5.2/export.sh

idf.py set-target esp32s3      # 50s  (configure 47s, managed_components 全 pull)

# 板子从默认 BREAD_COMPACT_WIFI 切到 OTTO_ROBOT（绕 menuconfig TUI；非交互）
sed -i 's|^CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI=y|# CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI is not set|' sdkconfig
sed -i 's|^# CONFIG_BOARD_TYPE_OTTO_ROBOT is not set|CONFIG_BOARD_TYPE_OTTO_ROBOT=y|' sdkconfig
idf.py reconfigure             # 35s

# 第一次 build → fail @ 2206/2212 (httpd_ws_*)
time idf.py build              # 3m30s, exit 2

# Append OTTO_ROBOT 必需 CONFIG (来自 main/boards/otto-robot/config.json)
cat >> sdkconfig <<'EOF'

# OTTO_ROBOT 板要求 (from main/boards/otto-robot/config.json sdkconfig_append)
CONFIG_HTTPD_WS_SUPPORT=y
CONFIG_CAMERA_OV2640=y
CONFIG_CAMERA_OV3660=y
EOF

time idf.py build              # 3m32s, exit 0 ✅
```

### AC 验证

| # | AC | 实测 |
|---|---|---|
| 1 | `idf.py --version` = `ESP-IDF v5.5.2` | ✅ `ESP-IDF v5.5.2` (set-target 后 dirty 标记消失) |
| 2 | `idf.py set-target esp32s3` 成功 | ✅ Configuring done (47.0s) / Generating done (1.7s) |
| 3 | `CONFIG_BOARD_TYPE_OTTO_ROBOT=y` 在 sdkconfig | ✅ |
| 4 | `idf.py build` 跑完无 error，末尾 `Project build complete.` | ✅ EXIT=0；末尾 `Project build complete. To flash, run: idf.py flash` |
| 5 | `build/*.bin` ≥1 个 ≥1 MB | ✅ `build/xiaozhi.bin` 3,688,320 B (3.5 MiB) |
| 6 | ≤15 行 memo | ↓ 见下 |

### Memo (AC #6)

- **build 耗时**：第一次 3m30s (fail @ 2206/2212) + 第二次 3m32s (success)。
  全冷 build 约 7 min wall-clock (有 `https_proxy=127.0.0.1:7897` 加速，
  managed_components 一次拉齐 ~150 个组件)
- **xiaozhi.bin**：3,688,320 B / app partition 4,128,768 B → free 11%
  (`0x6b880` bytes)。OTA 双分区每个 4032 KB，spiffs assets 8 MB
- **partition layout**：nvs 24K / otadata 8K / phy_init 4K /
  **ota_0 app 4032K @ 0x20000** / **ota_1 app 4032K @ 0x410000** /
  **assets spiffs 8M @ 0x800000**。flash 总占用 16 MB
- **warning 数**：13 (主要 lwip `_IOR/_IOW` 跟 esp_video 重定义；driver/adc.h
  legacy deprecated；txp666 emoji gif `int → unsigned` 转换)；全是
  上游 warning，本任务不动
- **sdkconfig 关键行**（grep `CONFIG_(BOARD_TYPE_OTTO_ROBOT|IDF_TARGET|
  HTTPD_WS_SUPPORT|CAMERA_OV)`）：
  ```
  CONFIG_IDF_TARGET="esp32s3"
  CONFIG_BOARD_TYPE_OTTO_ROBOT=y
  CONFIG_HTTPD_WS_SUPPORT=y
  CONFIG_CAMERA_OV2640=y
  CONFIG_CAMERA_OV3660=y
  ```

### 给 planner 的 follow-up（必读，回灌 fact）

1. **shared/global-commands.md §ESP32 段** 必须加：
   - `cd ~/esp-idf-5.5.2 && git submodule update --init --recursive`
     一次性 (~15 min)，新装 IDF 必跑
   - OTTO_ROBOT 板 `idf.py menuconfig` 选完之后，**必须**手工
     append 3 个 CONFIG (从 `main/boards/otto-robot/config.json` 的
     `sdkconfig_append`)，否则 build 在 2206/2212 处崩
2. **CLAUDE.md / ADR-0001 §pitfall #1** 要补一条："板子型号选对 ≠ build
   能过 —— OTTO_ROBOT 板 menuconfig 之外还需 3 个 CONFIG"
3. **README clone 步骤** 已经写了 `--recurse-submodules`（本仓的
   submodule），但**没说 IDF 自己也要 init submodule**，是新装者会卡的坑
4. **xiaozhi.bin 11% free** 是 baseline，给 M4 留 ~440 KB 加 MCP tool
   代码的预算上限。M4 设计时要盯这个

### 不动的边界

- ESP32 实物未连，未 flash，未 monitor（H1b 任务，等 USB 线 + H011 server
  联调）
- 未 commit（gitignored：`build/`、`managed_components/`、`sdkconfig`、
  `sdkconfig.old`、`dependencies.lock`）
- 未改 `main/` 任何源码（包括 boards/otto-robot/ 反豁免区）
- 未修改任何 ADR、handoff（除本 handoff 自身 done 收尾）
