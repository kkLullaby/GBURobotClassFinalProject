# Global Commands

> 所有角色都必须知道的命令。这是"事实"。
> Agent 跑命令前先查这里，**不要凭"印象"或"经验"**敲 `npm test`/`make` 之类——本项目不一定用那个。

## ESP32 编译 / 烧录 / 监视

```bash
# ──────────────────────────────────────────────────────────────
# 一次性：装完 IDF 必须立刻 init 其自身的 submodules（H012 教训）
# ──────────────────────────────────────────────────────────────
# 若漏跑这一步，set-target/build 在 __component_get_requirements 阶段
# 就崩，报 "Missing esp-mqtt submodule"
cd ~/esp-idf-5.5.2 && git submodule update --init --recursive  # ~15 min
# 验：git submodule status | grep -c '^-'   →   0
# 不要带 --depth=1，会在 lib_esp32c3_family 处中断 (pin 非 branch tip)

# ──────────────────────────────────────────────────────────────
# 每次新开终端必须 source（建议在 .bashrc 加 alias）
# alias get_idf552='source ~/esp-idf-5.5.2/export.sh'
# ──────────────────────────────────────────────────────────────
source ~/esp-idf-5.5.2/export.sh
idf.py --version   # 期望 ESP-IDF v5.5.2

cd esp/xiaozhi-esp32

# 首次配置
idf.py set-target esp32s3
idf.py menuconfig          # Xiaozhi Assistant → Board Type → ottoRobot
                           # 注意：Kconfig prompt 实际是 "ottoRobot" (小写 o 驼峰)
                           # 保存 S→Enter→Q

# ──────────────────────────────────────────────────────────────
# OTTO_ROBOT 板专属：menuconfig 之后必须 append 3 个 CONFIG
# 来源：main/boards/otto-robot/config.json 的 sdkconfig_append 字段
# 上游 README 漏说；若不 append，build 在 2206/2212 处崩
# (websocket_control_server.cc 报 httpd_ws_* 未定义)
# ──────────────────────────────────────────────────────────────
cat >> sdkconfig <<'EOF'

# OTTO_ROBOT 板要求 (from main/boards/otto-robot/config.json sdkconfig_append)
CONFIG_HTTPD_WS_SUPPORT=y
CONFIG_CAMERA_OV2640=y
CONFIG_CAMERA_OV3660=y
EOF

# 日常
idf.py build               # 全冷 ~7 min；含 ~150 个 managed_components pull
idf.py -p /dev/ttyACM0 flash monitor   # OttoRobot 是 ttyACM0 (USB-OTG)，不是 ttyUSB0

# ──────────────────────────────────────────────────────────────
# 串口 / 烧录踩过的坑（H1b 实测 2026-06-19）：
# ──────────────────────────────────────────────────────────────
# 1. ESP32-S3 OttoRobot 用内置 USB-OTG → 串口是 /dev/ttyACM0
#    不是 /dev/ttyUSB0（那是 CH340/CP210x 外挂芯片用的）
#    先 `ls /dev/ttyACM* /dev/ttyUSB*` 看你到底是哪个
# 2. flash 完后 ESP32 会卡在
#       rst:0x15 (USB_UART_CHIP_RESET),boot:0x0 (DOWNLOAD)
#       waiting for download
#    这不是错，是 boot 没切回 normal mode。**按板上 RST 键**让它重启进 boot
#    （不要 Ctrl+] 退 monitor，保持 monitor 开着按 RST 看 boot 日志最快）
# 3. 首次 boot 没配过 wifi → 卡 BluFi/SoftAP 配网
#    用手机 ESP-Touch / BluFi app（小米/小度类似）连蓝牙，传 SSID + 密码
#    上游流程见 esp/xiaozhi-esp32/docs/blufi_zh.md
# 4. monitor 退出：Ctrl + ]（不是 Ctrl + C；后者会发 SIGINT 给 idf.py）

# 出错时彻底清干净再重来（保留 sdkconfig 不删，会重新触发 OTTO 段补加）
rm -rf build managed_components dependencies.lock
idf.py reconfigure
```

**Build baseline（H012 实测 2026-06-19）**：

- `xiaozhi.bin` = 3.5 MiB，app partition 4 MiB，**剩 ~440 KB (11%) 给 M4 加 MCP tools**
- 全冷 wall-clock 7 min（含 managed_components 下载）
- 13 warnings 全是上游 (lwip / esp_video `_IOR/_IOW` 重定义；driver/adc.h legacy)

## xinnan-tech xiaozhi-esp32-server（Docker minimal）

> repo clone 在仓库外：`~/code/xinnan-tech/xiaozhi-esp32-server/`
> compose 文件路径：`main/xiaozhi-server/docker-compose.yml`
> 容器名：`xiaozhi-esp32-server`（**注意不是 xiaozhi-server**）

```bash
COMPOSE_DIR=~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server

# 启 / 停 / 重启
cd $COMPOSE_DIR && docker compose up -d
cd $COMPOSE_DIR && docker compose restart      # 改 config 后必须，等 ~8s

# 状态 / 日志
docker ps --filter name=xiaozhi-esp32-server --format '{{.Names}} {{.Status}} {{.Ports}}'
docker logs xiaozhi-esp32-server 2>&1 | tail -50
docker logs xiaozhi-esp32-server 2>&1 | grep -E 'STT|LLM|TTS|connected|session'

# 端口（minimal 模式，**没有 8004 mcp-endpoint 子服务**）
ss -tln | grep -E ':(8000|8003)'   # 期望都 LISTEN

# 验 OTA endpoint（返回内容含 server.websocket 字段值）
curl -sS http://localhost:8003/xiaozhi/ota/

# config 文件（**含 LLM API key，gitignored，在仓库外**）
ls $COMPOSE_DIR/data/.config.yaml
grep -E 'websocket:|LLM' $COMPOSE_DIR/data/.config.yaml   # 看 ws URL + LLM 配置

# ⚠️ FunASR 模型必须先下（H011 教训）：
#   models/SenseVoiceSmall/model.pt (893 MB)
#   缺 → EOFError → restart:always 崩溃循环
# 见 H011 What I Did。
```

**M1 后续要用的 8004 mcp-endpoint** 是独立子服务，minimal compose 不带；
M1 开工时单独起，见 xinnan-tech `docs/mcp-endpoint-enable.md`。

## Python 桥接服务（M1 / M2 / M3）

> ⚠️ **Python 解释器选择**（H015 unblock 踩坑, 2026-06-19）
>
> 用户默认 `python3` → `/home/kk/.platformio/penv/bin/python3` (PlatformIO venv，**没装项目 deps**)
> `uv pip install --system` 默认装到 → `/home/kk/miniconda3/lib/python3.13/...`
>
> **本项目所有 Python 包（M1/M2/M3）一律用 conda 这个 python 跑**：
> ```bash
> alias pyx='/home/kk/miniconda3/bin/python'   # 建议加到 ~/.bashrc
> ```

```bash
# 装包 / 跑包模板
cd <package-dir>                                              # e.g. xiaozhi-mcp-adapter
UV_CACHE_DIR=/tmp/uv-cache uv pip install --system -e '.[test]'
pyx -m pytest -xvs tests/                                     # 跑测
pyx -m <pkg.entrypoint>                                       # 启动
```

### M1: xiaozhi-mcp-adapter（已有，H015 落地）

```bash
cd xiaozhi-mcp-adapter
# 装 (一次性)
UV_CACHE_DIR=/tmp/uv-cache uv pip install --system -e '.[test]'

# 跑 spike 测试
pyx -m pytest -xvs tests/                       # 1.17s 通过

# 单跑 echo_tool (本地 stdio MCP server smoke)
timeout 2 pyx -m xiaozhi_mcp_adapter.echo_tool < /dev/null

# 真连 xinnan-tech 8004 mcp_endpoint（H016 done 后）
MCP_ENDPOINT='ws://<host-ip>:8004/mcp_endpoint/mcp/?token=<...>' \
  pyx -m xiaozhi_mcp_adapter.pipe
```

### M2 / M3 (待 H018+ 创建)

骨架同 M1：`pyproject.toml` + `src/<pkg>/...` + `tests/` + 用 `pyx` 跑。

## Hermes（Week 0 实测后回填，2026-06-19）

```bash
# 装（已通过 PyPI）
uv tool install hermes-agent          # 装 → ~/.local/bin/hermes (v0.16.0)

# 配 provider：本项目用 DeepSeek 官方 (api.deepseek.com)；key 由 Hermes auth 写入 ~/.hermes/state.db
hermes auth add deepseek --api-key '<your-deepseek-key>'
hermes config set model '{"default":"deepseek-v4-pro","provider":"deepseek"}'

# 验
hermes -z "1+1=?"   # one-shot 测，应返回 "2"
hermes              # 进 TUI

# 状态 / 调试
hermes config show  # 配置 + key 名清单（**会显示 key 后缀**，注意环境）
hermes auth list    # 列所有 provider 凭据
hermes config path  # → ~/.hermes/config.yaml
hermes config env-path  # → ~/.hermes/.env（本项目当前未使用；key 在 state.db）
```

注意：
- `OPENAI_API_KEY` env 即使存在也不影响，因为 model 字符串已锁 provider=deepseek
- key 在 `~/.hermes/state.db` 明文存（hermes 设计如此），不要把 `~/.hermes/`
  整目录 commit 进 git
- MCP server 模式（M1 adapter 通过它注册）：M1 开工时再补

## Git 工作流（项目特化）

```bash
# 克隆后拉子模块
git submodule update --init --recursive

# 更新 xiaozhi-esp32 submodule 到上游 main
cd esp/xiaozhi-esp32 && git fetch origin && git checkout main && git pull origin main
cd ../.. && git add esp/xiaozhi-esp32 && git commit -m "chore: bump xiaozhi-esp32 to upstream main"

# memory 自动提交前缀（spec 约定）
# [memory] update planner/MEMORY.md
# 主项目 PR 时 squash 掉 [memory] commits
```

## Note

- **不要凭印象敲** `make test` / `npm test` —— 本项目还没写过那种文件，先查这里
- ESP32 编译产物 `build/` 体量巨大（GB 级），**别把它误纳入 worktree 复制范围**
