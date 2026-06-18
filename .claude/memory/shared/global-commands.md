# Global Commands

> 所有角色都必须知道的命令。这是"事实"。
> Agent 跑命令前先查这里，**不要凭"印象"或"经验"**敲 `npm test`/`make` 之类——本项目不一定用那个。

## ESP32 编译 / 烧录 / 监视

```bash
# 每次新开终端必须 source（建议在 .bashrc 加 alias: get_idf552='source ~/esp-idf-5.5.2/export.sh'）
source ~/esp-idf-5.5.2/export.sh

cd esp/xiaozhi-esp32

# 首次配置（板子选错就是黑屏 + 无声 → 重选）
idf.py set-target esp32s3
idf.py menuconfig          # Xiaozhi Assistant → Board Type → Otto Robot；保存 S→Enter→Q

# 日常
idf.py build flash monitor # Ctrl+] 退出 monitor

# 出错时彻底清干净再重来
rm -rf build managed_components dependencies.lock
idf.py reconfigure
```

## xinnan-tech xiaozhi-esp32-server（Docker minimal）

```bash
# 启动 / 状态 / 日志（具体命令在 Week 0 实际跑通后回填）
docker logs xiaozhi-server 2>&1 | tail -50
# 端口：8000 / 8003 / 8004 监听确认
```

## Python 桥接服务

```bash
# M1/M2/M3 Python 项目（待 Week 1+ 创建后回填具体路径）
# pytest <path>     # 单测
# python -m <pkg>   # 启动
```

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
