---
id: 2026-06-19-m1-spike-echo-tool-015
from: planner
to: executor
parent: 2026-06-19-flash-baseline-to-local-server-h1b-013
supersedes:
status: pending
created: 2026-06-19
artifacts:
  - xiaozhi-mcp-adapter/ (new Python package, repo root)
  - xiaozhi-mcp-adapter/pyproject.toml or setup.cfg
  - xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/{__init__,pipe,echo_tool}.py
  - xiaozhi-mcp-adapter/tests/test_pipe_e2e.py
  - xiaozhi-mcp-adapter/README.md
---

## Why first M1 spike

[ADR-0005](../adr/0005-openai-compat-transcript-egress.md) 把 M3 从 5-6 → 1-2
天，**腾出 M1 的工期裕度**，可以用一份 spike 先确认两件事：

1. **xiaozhi MCP 接入点协议形态实测**：上游 `mcp-pipe.py` 把 stdio MCP
   server 通过 WS 暴露给 xinnan-tech server（拨入式）。我们能否 1:1 复刻
   出来，且替换成自己的 echo tool 也能跑通？
2. **Python 包骨架定型**：M1 后续要长成 Hermes 的工具壳；先把 pyproject、
   日志、配置、测试 4 件骨架搭好，省得 M2 / M3 时再返工。

**spike 的范围严格**：不集成 Hermes、不实现真业务工具、不动 ESP32。
只验证 `wscat → mcp_endpoint → our pipe → echo tool → 回包` 这条 round-trip。

## Objective

在仓库根目录建 `xiaozhi-mcp-adapter/` Python 包，跑通**最小 round-trip**：

```
xinnan-tech server (MCP client, 拨过来)
        │  ws://<host>:8004/mcp_endpoint/mcp/?token=<...>
        ▼
xiaozhi-mcp-adapter pipe (我们写的，模仿 mcp-pipe.py)
        │  stdio JSON-RPC
        ▼
echo_tool.py (stdio MCP server, 一个 tool: echo(text) → 回 "echoed: " + text)
```

测法：

- **不需要真启动 8004 子服务**（H016 才做）
- 用 `pytest` + `websockets` 起一个 mock WS server 充当 xinnan-tech 端，
  发 MCP `initialize` / `tools/list` / `tools/call("echo", {text:"hi"})`，
  期望收到 `{"content":[{"type":"text","text":"echoed: hi"}]}`

## Constraints

- **不**改 `esp/xiaozhi-esp32/` 任何文件（含 boards/otto-robot/）
- **不**改 `docs/contracts/`、`docs/adr/`、`docs/handoffs/`、`.claude/` 任何
  既有文件（除本 handoff 自身追加段）
- **不**集成 Hermes（H015 之后单独发 handoff）
- **不**起真 8004 docker 子服务（这是 H016 user-led 的活）
- **不**在仓库根之外创建文件（除非 gitignored）
- Python ≥ 3.8，依赖只允许：`websockets`, `mcp` (Anthropic 官方 Python SDK), `pytest`, `pytest-asyncio`
  - 如果上游 mcp-pipe 用了别的库，**先确认是否必要**——能用标准库 + 上面 4 个就别加
- 错误处理纪律按 [H010 §Error-handling discipline](archive/2026-06-19-mcp-transcript-egress-spike-010.md)
- **Sandbox-friendly**：本 handoff 设计为 codex / claude agent 在 sandbox 内
  能完整跑（无 docker、无 USB、无 wifi、无外部 LLM key）

## Acceptance Criteria

- [ ] 包结构：`xiaozhi-mcp-adapter/` 在仓库根，含 `pyproject.toml`、`src/xiaozhi_mcp_adapter/__init__.py`、
      `src/xiaozhi_mcp_adapter/pipe.py`、`src/xiaozhi_mcp_adapter/echo_tool.py`、
      `tests/test_pipe_e2e.py`、`README.md`
- [ ] `pyproject.toml` 用 PEP 621 元数据格式；`name="xiaozhi-mcp-adapter"`
      `python_requires=">=3.8"`；optional-dependencies 段含 `test = ["pytest>=7", "pytest-asyncio"]`
- [ ] `pipe.py` 复刻 mcp-pipe.py 行为：
      - 从 env `MCP_ENDPOINT` 读 WS URL
      - 用 `websockets.connect(uri)` 拨号
      - 用 `subprocess.Popen` 起子进程（echo_tool 默认）
      - 三协程 (ws→child, child→ws, child stderr→log) `asyncio.gather`
      - 重连退避：1s → 2s → 4s ... 最多 600s，**带 jitter** (±10%)
      - SIGINT/SIGTERM 干净退出
- [ ] `echo_tool.py` 是合法 MCP stdio server（用 `mcp.server.stdio` SDK）：
      - 声明工具 `echo(text: str) -> str`，实现返回 `"echoed: " + text`
      - 单跑 `python -m xiaozhi_mcp_adapter.echo_tool` 不报错且不退出
        （stdio server 默认 stdin 阻塞）
- [ ] `tests/test_pipe_e2e.py` 至少 1 个测试：
      ```python
      async def test_pipe_echo_roundtrip():
          # 起 mock WS server (port 0)
          # 起 pipe (MCP_ENDPOINT=ws://localhost:<port>)
          # mock 端发 initialize → 收 result
          # mock 端发 tools/list → 收 result 含 "echo"
          # mock 端发 tools/call("echo", {"text":"hi"}) → 收 "echoed: hi"
          # 清理 pipe
      ```
- [ ] `pytest -xvs tests/` 通过；输出贴回 What I Did（≤30 行）
- [ ] `README.md` ≤ 60 行，含：架构图（ascii）、装法（pip install -e .[test]）、
      `MCP_ENDPOINT` env 用法、跑测的命令、和 H016 的关系
- [ ] **不**写 Hermes 集成代码、**不**写真业务 tool、**不**改 `pipe.py` 接受
      非 echo_tool 子进程的代码路径（保 H015 spike 干净，泛化留给后续）
- [ ] `git status` 输出贴回 What I Did，预期：
      ```
      ?? xiaozhi-mcp-adapter/
      ```
      （单一新目录 untracked，不动既有文件）；planner 审过再 commit

## Context Pointers

- @docs/contracts/api/v1/esp32-to-server-handshake.md §4.3 (xinnan-tech MCP 接入点协议路径定义)
- @docs/contracts/api/v1/esp32-to-server-handshake.md §4.2.bis (上游 server 发的 MCP initialize 形态 = 反向 mock 时要复用)
- @docs/research-notes/xinnan-tech-openai-and-mcp.md §2 (握手序列、token、cursor 分页这些细节)
- @docs/adr/0005-openai-compat-transcript-egress.md (M1 工作范围缩窄到"暴露工具"，本 spike 是 M1 第一步)
- @docs/adr/0003-executor-runs-in-main-loop.md (sandbox 能做啥；本 handoff 设计成纯软件 spike → claude/codex agent 都能接)
- @docs/handoffs/archive/2026-06-19-mcp-transcript-egress-spike-010.md (上一次 M1/M3 spike，沿用 error discipline)
- 上游模板：https://github.com/78/mcp-calculator/blob/main/mcp_pipe.py
  （**只**读，不抄 license-protected 代码；理解流程后自己重写）
- MCP Python SDK 文档：https://modelcontextprotocol.io/quickstart/server

## Out of Scope

- 不实现"Hermes 工具暴露"——那是 H017+ 的活
- 不起 docker 子服务（H016 user-led）
- 不动 ESP32 / 不连真 server
- 不上 CI / 不写 Dockerfile（M1 完整阶段才考虑）
- 不实现配置文件加载（`MCP_ENDPOINT` env 一个变量够）
- 不实现 sse / http / streamablehttp 协议——只支持 WS（上游模板的 sse 支持本 spike 不要）

## Candidate Root Causes（如果 round-trip 跑不通时先查的）

1. **MCP SDK 版本 API drift** — `mcp` 包的 API 迭代频繁，stdio server
   注册 tool 的 decorator 可能换了；先 `python -c "import mcp; help(mcp.server.stdio)"` 看实际接口
2. **JSON-RPC notification vs request** — `notifications/initialized` 没 id，
   pipe 不能错给它发 response；上游 mcp-pipe 直接 stdio 透传所以不关心，
   我们的 mock server 要正确处理
3. **subprocess buffering** — stdio MCP server stdout 不 line-buffer 会卡死；
   `subprocess.Popen(... bufsize=1, text=True)` 或显式 `flush()`
4. **websockets API drift** — `websockets.connect()` 在不同版本上下文管理器
   语义略不同；锁版本 `websockets>=12`

## Suggested Steps

```bash
# 0. 切到仓库根，确认环境
cd ~/code/robot_class/final_pro_xiaozhi_robot
git status --short    # 期望干净
python3 --version     # ≥ 3.8
which uv || pip install --user uv   # 用 uv 装 deps 最快

# 1. 包骨架
mkdir -p xiaozhi-mcp-adapter/{src/xiaozhi_mcp_adapter,tests}
cd xiaozhi-mcp-adapter
# 写 pyproject.toml、src/.../{__init__,pipe,echo_tool}.py、tests/test_pipe_e2e.py、README.md

# 2. 装本地开发 mode
uv pip install --system -e .[test]    # 或 pip install -e .[test]

# 3. 单跑 echo_tool 烟测（应该 hang 等 stdin，Ctrl+C 退）
timeout 2 python -m xiaozhi_mcp_adapter.echo_tool < /dev/null
# 期望：起来 → stdin 收 EOF → 干净退；不报错

# 4. 跑测试
pytest -xvs tests/
# 期望：1 个 test_pipe_echo_roundtrip PASS

# 5. 跑完贴 git status + pytest 输出回 What I Did
git status --short
```

## Error-handling discipline

- **Cosmetic 错**（typo / 拼错 import / 漏装 deps）→ 自己改、自己重跑、What I Did 提一句
- **Substantive 错**（mcp SDK 用法不会、上游协议字段没对齐、async 死锁）→
  status: blocked + 完整 stderr + 已尝试的 2-3 种修法
- **不要因为"完美主义"超 scope**——echo round-trip 通了就完工，**不要**
  顺手做 retry policy / metrics / Hermes 集成

## Recovery

- pyproject 写错：删 `.egg-info` 重 `pip install -e .`
- mcp SDK 版本不对：先 `pip show mcp`，对照官方文档版本
- async test 卡住：`pytest --timeout=10` 强 fail；用 `pytest-asyncio` 的
  `loop_scope="function"` 防泄漏

## For Auditor

不发 auditor。这是 spike，planner 自审。
M1 正式落地（H017+）累计 3-4 个 handoff done 之后一起 batch audit。

## Open Questions for Planner (后续手势)

- H015 完成后立刻起 **H016 user-led**：在本机起 xinnan-tech 8004
  mcp-endpoint 子服务，拿真 token，跑 `MCP_ENDPOINT=ws://<host>:8004/...
  python -m xiaozhi_mcp_adapter.pipe`，**让 server 真的拨过来调 echo**
- H016 done = M1 真正能跟 xinnan-tech 互通，再开 H017（Hermes 工具适配）
