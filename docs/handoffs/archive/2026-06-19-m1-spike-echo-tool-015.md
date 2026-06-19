---
id: 2026-06-19-m1-spike-echo-tool-015
from: planner
to: executor
parent: 2026-06-19-flash-baseline-to-local-server-h1b-013
supersedes:
status: done
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

## Executor's Reading
### What I'll do
- 新建 `xiaozhi-mcp-adapter/` Python 包，写一个只从 `MCP_ENDPOINT` 拨 WS 的 pipe、一个 stdio MCP echo server，并用 mock WS server 覆盖 initialize → tools/list → tools/call 的 round-trip。

### Assumptions made
- [LOW] 当前仓库没有既有 `xiaozhi-mcp-adapter/` 包；我会新建 handoff 指定的单一目录，不改 ESP32、ADR、contract、research notes 或 `.claude/`。
- [LOW] `pipe.py` 只支持默认 echo tool 子进程，不提供可配置子命令；这是 H015 明确要求保 spike 干净。
- [LOW] 测试里的 mock WS server 复用 xinnan-tech 研究笔记中的 MCP endpoint 序列：WS 连接后由 mock 端发 `initialize`、`notifications/initialized`、`tools/list`、`tools/call`，pipe 只透明转发 JSON-RPC。
- [MED] 当前 Python 环境缺 `mcp`、`websockets`、`pytest`、`pytest-asyncio`；我会按 `pyproject.toml` 安装项目测试依赖。如果 sandbox 网络或包索引不可用导致安装失败，会按 substantive error 阻塞并贴完整 stderr。
- [MED] 上游 `mcp-pipe.py` 只作为行为参考；实现会按本 handoff 和 xinnan-tech 本地源码重写，不复制上游模板代码。

## What I Did
- 新建 H015 指定的单一目录 `xiaozhi-mcp-adapter/`，包含：
  - `pyproject.toml`
  - `src/xiaozhi_mcp_adapter/__init__.py`
  - `src/xiaozhi_mcp_adapter/pipe.py`
  - `src/xiaozhi_mcp_adapter/echo_tool.py`
  - `tests/test_pipe_e2e.py`
  - `README.md`
- `pipe.py` 已按 spike 范围实现：从 `MCP_ENDPOINT` 读取 WS URL、`websockets.connect()` 拨号、`subprocess.Popen` 启默认 echo child、三路协程转发/日志、SIGINT/SIGTERM 退出、1s→2s→4s...最多 600s 的 ±10% jitter 重连退避。
- `echo_tool.py` 已按 stdio MCP server 形态实现单个 `echo(text: str)` tool，返回 `echoed: ` + text。
- `tests/test_pipe_e2e.py` 已写 mock WS server，覆盖 initialize → notifications/initialized → tools/list → tools/call("echo", {"text":"hi"}) 的 round-trip 期望。
- 发现 `asyncio.to_thread` 不兼容 `requires-python >=3.8`，已改为 `loop.run_in_executor`；语法检查通过：
  `python3 -m py_compile src/xiaozhi_mcp_adapter/__init__.py src/xiaozhi_mcp_adapter/pipe.py src/xiaozhi_mcp_adapter/echo_tool.py tests/test_pipe_e2e.py`
- `README.md` 行数：`58 README.md`，满足 ≤60 行约束。
- 阻塞点：当前 sandbox 没有 `mcp`、`websockets`、`pytest`、`pytest-asyncio`，且 PyPI 访问被网络/权限拦截；无法安装依赖，也就无法运行 `python -m xiaozhi_mcp_adapter.echo_tool` 或 `pytest -xvs tests/` 做 AC 验证。
- 未修改 ESP32、ADR、contracts、research notes 或 `.claude/`；未 commit。
- `git status --short`：

```text
 M docs/handoffs/active/2026-06-19-m1-spike-echo-tool-015.md
 ? esp/xiaozhi-esp32
?? xiaozhi-mcp-adapter/
```

- 完整 stderr / command output：

```text
$ uv pip install --system -e '.[test]'
error: Could not acquire lock
  Caused by: Could not create temporary file
  Caused by: Read-only file system (os error 30) at path "/home/kk/.cache/uv/.tmpXe1uMj"
```

```text
$ UV_CACHE_DIR=/tmp/uv-cache uv pip install --system -e '.[test]'
Using Python 3.13.9 environment at: /home/kk/miniconda3
error: Request failed after 3 retries in 8.1s
  Caused by: Failed to fetch: `https://pypi.org/simple/pytest-asyncio/`
  Caused by: error sending request for url (https://pypi.org/simple/pytest-asyncio/)
  Caused by: client error (Connect)
  Caused by: tunnel error: failed to create underlying connection
  Caused by: tcp open error
  Caused by: Operation not permitted (os error 1)
```

## Open Questions for Planner/User
- 请在有 PyPI/proxy 权限的用户主终端续跑：
  `cd xiaozhi-mcp-adapter && UV_CACHE_DIR=/tmp/uv-cache uv pip install --system -e '.[test]' && pytest -xvs tests/`。
  → **2026-06-19 已解决**：planner main-loop 接 unblock。下方 §"Unblock + PASS"。

---

## Unblock + PASS (planner main-loop, 2026-06-19)

> 跟 H012 / H013 同一类 ADR-0003 II 代跑模式：codex sandbox 无 PyPI / 网络
> proxy 不可达；planner 本会话有 proxy → 装 deps + 跑 pytest。

### 装依赖

```bash
cd ~/code/robot_class/final_pro_xiaozhi_robot/xiaozhi-mcp-adapter
UV_CACHE_DIR=/tmp/uv-cache uv pip install --system -e '.[test]'
# uv 默认绑定 /home/kk/miniconda3 的 Python 3.13.9
# 装了：mcp==1.28.0, websockets, pytest==9.1.0, pytest-asyncio==1.4.0,
#       httpx-sse, starlette, sse-starlette, uvicorn, anyio (mcp 间接依赖)
```

⚠️ **环境坑（不属 H015 scope，仅记录）**：用户默认 shell 的 `python3` 指向
`/home/kk/.platformio/penv/bin/python3` （PlatformIO penv），uv 装到的
是 `/home/kk/miniconda3/lib/python3.13/site-packages/`。后续跑测/手动
demo 必须明示用 `/home/kk/miniconda3/bin/python`，或 user 改 default
python 指向。回灌点：[shared/global-commands.md §Python 桥接服务](../../../.claude/memory/shared/global-commands.md)
要补一段"M1+ Python 包都用 conda Python 跑"。

### 烟测 echo_tool

```bash
timeout 2 /home/kk/miniconda3/bin/python -m xiaozhi_mcp_adapter.echo_tool < /dev/null
# EXIT=0 ✅（stdin EOF → 干净退）
```

### pytest e2e PASS

```text
$ /home/kk/miniconda3/bin/python -m pytest -xvs tests/
============================= test session starts ==============================
platform linux -- Python 3.13.9, pytest-9.1.0, pluggy-1.5.0
configfile: pyproject.toml
plugins: asyncio-1.4.0, anyio-4.12.1
asyncio: mode=Mode.AUTO

tests/test_pipe_e2e.py::test_pipe_echo_roundtrip PASSED

============================== 1 passed in 1.17s ===============================
```

### AC 验证

| # | AC | 结果 |
|---|---|---|
| 1 | 包结构齐全 | ✅ 6 文件 (`pyproject.toml`, `__init__.py`, `pipe.py`, `echo_tool.py`, `tests/test_pipe_e2e.py`, `README.md`) |
| 2 | pyproject PEP 621 + name + python>=3.8 + test extras | ✅ |
| 3 | `pipe.py` 行为齐全（env + WS + Popen + 三协程 + jitter retry + signal） | ✅ 176 行 |
| 4 | `echo_tool.py` 合法 MCP stdio server | ✅ 71 行；用 `mcp.server.lowlevel.Server` + `mcp.server.stdio.stdio_server` |
| 5 | pytest e2e PASS | ✅ 1.17s |
| 6 | pytest 输出 ≤30 行 | ✅ 上面贴的 9 行 |
| 7 | README ≤60 行 | ✅ 58 行 |
| 8 | 不写 Hermes / 不改 pipe 接受其它子进程 | ✅ |
| 9 | git status 仅一目录 untracked | ✅ `xiaozhi-mcp-adapter/` |

### git status (commit 前)

```text
 M docs/handoffs/active/2026-06-19-m1-spike-echo-tool-015.md
 ? esp/xiaozhi-esp32
?? xiaozhi-mcp-adapter/
```

### Bonus observations（给 H017 用）

- `pipe.py` 用 `asyncio.wait(... FIRST_COMPLETED)` + 异常重抛—— round-trip
  通过后会立刻退出（因为 mock 端关 WS 触发 `_ws_to_child` 退），不会泄漏。
  生产场景下要换 `FIRST_EXCEPTION`/`ALL_COMPLETED` 重新考虑
- `echo_tool` 用的是 `Server` lowlevel API，不是 `FastMCP` 高级 API；M1
  真业务 tool 多了后切 FastMCP 可能减一半代码
- mock test 没单独测断线重连 jitter 退避；H017+ 加更全的测试套时补
- MCP SDK 装下来一堆 starlette / uvicorn / sse_starlette 是因为 `mcp` 含
  SSE/HTTP server 支持，我们用不到但去不掉。**约 30 MB 装机体积**，
  不影响功能

### Follow-up handoffs (planner 自承)

- **H016 user-led**：本机起 xinnan-tech 8004 mcp-endpoint 子服务，拿真
  token，跑 `MCP_ENDPOINT=ws://<host>:8004/mcp_endpoint/mcp/?token=<...>
  /home/kk/miniconda3/bin/python -m xiaozhi_mcp_adapter.pipe`；让 server
  真的拨过来调 echo。AC：在 ESP32 端语音说"调 echo 工具 hi"，server logs
  含 `tools/call echo` 调 result `echoed: hi`，DeepSeek 把这话回给用户
- **shared/global-commands.md 回灌**：M1+ Python 包要用
  `/home/kk/miniconda3/bin/python`（而不是默认 PlatformIO penv）。这是
  H015 unblock 时踩的次坑，要把命令写明，避免后续每个 Python handoff 都
  重复发现
