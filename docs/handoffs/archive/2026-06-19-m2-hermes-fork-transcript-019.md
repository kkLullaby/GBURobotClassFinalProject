---
id: 2026-06-19-m2-hermes-fork-transcript-019
from: planner
to: executor
parent: 2026-06-19-m2-spike-openai-shim-018
supersedes:
status: done
created: 2026-06-19
artifacts:
  - openai-shim/src/openai_shim/hermes_backend.py (new)
  - openai-shim/src/openai_shim/app.py (改：backend wiring + transcript fork hook)
  - openai-shim/tests/test_hermes_fork.py (new)
  - openai-shim/tests/test_chat_completions.py (改：原 echo 测仍 pass)
  - openai-shim/README.md (改：H019 段)
---

## Why now

H018 把 M2 [ADR-0005](../adr/0005-openai-compat-transcript-egress.md) 的 SSE
出口骨架打通。**ADR-0005 主线还差一公里**：M2 不仅要回 SSE，还得在 handler
里 **fork 出一份 transcript 给 Hermes**，让 Hermes session 拿到 user 的语音
转写 + assistant 的回复，于是 Hermes 在对话流里能"看"到 ESP32 用户说什么、
机器人答了什么——这是 Hermes "第一具物理化身" 的关键交付。

H016 (mcp-endpoint server bringup) 还在 user 端跑 Stage D；H019 跟 H016
**互不阻塞**——本 spike 只需 M2 + Hermes（都在主机本地），不需要 ESP32、不需要
mcp-endpoint-server、不需要真 LLM key。

跟 H015 / H018 同模式：sandbox-friendly Python spike，可交 codex / claude
agent；scope 严格不外溢。

## Objective

在 `openai-shim/` 内加一个 **HermesBackend**，使得 `POST /v1/chat/completions`
处理流程中：

```
xiaozhi-server (用 openai SDK)             M2 openai-shim
  ↓ POST /v1/chat/completions                ↓ FastAPI handler
  ↓ stream=true                              ├── backend.stream_response()  ──→ SSE 流 (LLM 出口)
  ↓ messages=[{user: "我想看天气"}]          │
                                            └── backend.on_transcript()    ──→ HTTP POST
                                                                                http://localhost:8088/webhooks/xiaozhi-transcript
                                                                                {"user":"我想看天气","assistant":"<最终拼回的内容>","session":"<id>"}
                                                                                Hermes webhook → spawn session per ADR-0005
```

**双输出**：SSE 给 server (LLM)、HTTP POST 给 Hermes (transcript)；**主路径
不被 fork 失败拖累**。

测法：

- **不需要真 Hermes**——pytest 起一个 mock HTTP server (httpx.ASGITransport 包
  小 FastAPI / starlette `/webhooks/...`) 当 fake-hermes
- **真 openai SDK 客户端**仍用 H018 路径触发 SSE，断言 fork 的 HTTP POST 真送
  到 fake-hermes 且 payload 字段正确
- 加 1 个测：fake-hermes 故意返回 500，断言 SSE 仍正常返回（fire-and-forget
  纪律）

## Constraints

- **不**改 `xiaozhi-mcp-adapter/`、`esp/`、`docs/contracts/`、`docs/adr/`、
  `docs/handoffs/` 任何既有文件（除本 handoff 自身追加段）
- **不**调真 LLM provider（DeepSeek / OpenAI）——backend 继续 echo（H020 才
  接真 LLM）
- **不**实现真 Hermes adapter（`gateway/platforms/xiaozhi.py`）——只走 Hermes
  自带的 `hermes webhook` HTTP 入口，那是 ADR-0005 §M3 "薄壳" 的具体载体
- **不**实现 ESP32 端 / mcp-endpoint-server / 真链路（H016/H020 才做）
- **不**改 `openai_shim.echo_backend.EchoBackend`——加新 `HermesBackend`
  组合 echo backend（**复用**，不重写）
- **不**改 SSE 帧结构 / app.py 的请求体 schema (`ChatCompletionRequest`)
- Python ≥ 3.8；新增依赖只允许：`httpx`（H018 已装的 test extras）
- 错误处理纪律按 H010 §Error-handling discipline
- transcript fork **不能阻塞** SSE：fork 用 `asyncio.create_task` 并 fire-and-forget；
  fork 失败只 log warning，**不** raise
- **Sandbox-friendly**：本 handoff 设计为 codex / claude agent 在 sandbox 内
  能完整跑（无 docker、无 USB、无外部网络、无真 Hermes）
- 一切用 [`pyx`](../../.claude/memory/shared/global-commands.md)
  (`/home/kk/miniconda3/bin/python`) 跑

## Acceptance Criteria

- [ ] 新建 `openai-shim/src/openai_shim/hermes_backend.py`：
      - `class HermesBackend`：组合一个 inner `TextBackend`（默认 EchoBackend）
        + 一个 `transcript_url: str` + `httpx.AsyncClient`（注入或自建）
      - `async def stream_response(messages, model)`: yield inner backend 的
        deltas，**同时**累积所有 delta 拼成 `assistant_text`，**结束**后用
        `asyncio.create_task(self._post_transcript(...))` fire-and-forget
        发 HTTP POST
      - payload schema 固定：
        ```json
        {
          "user": "<最后一个 user message 的 content>",
          "assistant": "<所有 delta 拼接>",
          "model": "<request.model>",
          "session": "<chatcmpl-...>",
          "timestamp_unix": <int>
        }
        ```
      - 任何 fork 异常 (`httpx.HTTPError`, `asyncio.CancelledError`,
        `Exception`) **只 log.warning**，不 raise，不影响 SSE
- [ ] `openai-shim/src/openai_shim/app.py` 改：
      - 顶部新增环境变量读取：`HERMES_TRANSCRIPT_URL`（缺省 `None`）
      - 启动期：如果环境变量 set，则 `_backend = HermesBackend(EchoBackend(), url)`；
        否则保持 `_backend = EchoBackend()`（H018 行为不变，原测仍 pass）
      - 不再改 endpoint handler 行为
- [ ] **不**改 `openai_shim.echo_backend.EchoBackend` 一行代码
- [ ] **不**改 `openai_shim.sse.chat_completion_sse` 一行代码
- [ ] `openai-shim/tests/test_chat_completions.py` 原 2 个测仍 PASS
      （证明 H018 行为零回退）
- [ ] 新建 `openai-shim/tests/test_hermes_fork.py`，至少 3 个测试：
      1. `test_transcript_posted_when_hermes_url_set`：起 fake-hermes ASGI
         app 接 `POST /webhooks/xiaozhi-transcript`；用 monkeypatch 设
         `HERMES_TRANSCRIPT_URL=http://fake-hermes/webhooks/xiaozhi-transcript`
         （或直接构造 HermesBackend instance 注入 mock httpx client）；
         真 openai SDK 客户端发 `chat.completions.create(stream=True)`；收齐
         SSE；**断言**：fake-hermes 收到 POST，body JSON 含 `user="hi"` /
         `assistant="echoed: hi"` / `session` 是 chatcmpl- / `timestamp_unix`
         是 int
      2. `test_sse_still_works_when_hermes_returns_500`：fake-hermes handler
         强制 return 500；SSE 客户端**仍**能收到 `echoed: hi` + `[DONE]`；
         不 raise
      3. `test_no_fork_when_hermes_url_unset`：env 不设；EchoBackend 单独
         work（这其实是 H018 行为重测，但用 `monkeypatch.delenv` 显式确认）
- [ ] `pyx -m pytest -xvs tests/` 通过；输出贴 What I Did（≤40 行）
- [ ] `README.md` 加 1 段 "H019 Hermes Fork" (≤20 行)：
      - env 变量名 + 示例值（指向 `hermes webhook` 默认 port，参考 H016 模式）
      - 一行 `hermes webhook subscribe` 示例命令（**不**真跑）
      - 解释 fork 是 fire-and-forget，Hermes down 不影响 SSE
- [ ] `git status` 输出贴 What I Did，预期：
      ```
      M openai-shim/src/openai_shim/app.py
      M openai-shim/README.md
      ?? openai-shim/src/openai_shim/hermes_backend.py
      ?? openai-shim/tests/test_hermes_fork.py
      ```
- [ ] **不**真跑 `hermes` CLI；**不**改 `~/.hermes/`；**不**碰 H016 的 docker
- [ ] **不**写 ESP32 / mcp-endpoint-server / 真 LLM provider 集成

## Context Pointers

- @docs/adr/0005-openai-compat-transcript-egress.md (**先读**——M2 transcript
  fork 的 motivation；本 spike 是它"主线"段的具体实现)
- @docs/handoffs/archive/2026-06-19-m2-spike-openai-shim-018.md (**关键**——
  H018 已建的 openai-shim 包；本 spike 在它上面**追加**，scope 不外溢)
- @openai-shim/src/openai_shim/app.py (H018 已写的 FastAPI app，本 handoff
  会改 backend wiring 段)
- @openai-shim/src/openai_shim/echo_backend.py (`TextBackend` Protocol；
  HermesBackend 实现这个 Protocol，**复用** EchoBackend 当 inner)
- @openai-shim/src/openai_shim/sse.py (SSE 不动；HermesBackend 在 backend 层
  fork，不在 SSE 层)
- @.claude/memory/shared/global-commands.md §Python (pyx 别名 / pytest 命令)
- @docs/adr/0003-executor-runs-in-main-loop.md (sandbox-friendly 设计)
- Hermes webhook CLI 参考（**只读不跑**）：
  ```bash
  hermes webhook subscribe xiaozhi-transcript \
    --prompt 'User said: {user}. Assistant replied: {assistant}.' \
    --description 'XiaoZhi robot transcript ingress (H019)' \
    --deliver-only
  ```
  → Hermes 在本地起 `http://localhost:8088/webhooks/xiaozhi-transcript`
  （port 由 `hermes gateway` 决定，默认 8088）
- httpx mock 示例：`tests/conftest.py` 用
  `httpx.AsyncClient(transport=httpx.ASGITransport(app=fake_hermes_app))`

## Out of Scope

- 不实现真 Hermes adapter (`gateway/platforms/xiaozhi.py`) — H020 / 单独 spike
- 不实现真 LLM provider routing — H020+
- 不实现 ESP32 端到 Hermes 的反向通道（Hermes 决定让机器人说什么 → ESP32）— H021+
- 不改 Hermes 自身代码 / 不 fork upstream
- 不实现 transcript 持久化（每次 fork 就完事，Hermes 自己管 session 持久化）
- 不实现 multi-tenant transcript 路由 (一个 ESP32 = 一个 Hermes session)
- 不实现 retry / backoff（fork 失败就丢，由 Hermes webhook reliability 决定）
- 不实现 HMAC 签名（Hermes webhook 支持但 H019 不上）

## Candidate Root Causes（跑不通时先查）

1. **fork race condition**：用 `asyncio.create_task` 后**没**保持引用，task
   可能被 GC 提前杀。修：把 task 挂到 self._inflight_tasks set 上 + done
   callback 移除
2. **httpx.AsyncClient 生命周期**：`__init__` 里建的 client 不能直接 await
   in `__aexit__`；要么注入要么 lazy-create 每个 request 自己的
3. **测试时 server-side asyncio loop 不在用户 loop 里**：fake-hermes 用
   `ASGITransport` 即可（同 H018 的 openai SDK 测试模式）
4. **fork **不**能等待 server 收到** — `create_task` 后函数立刻 return，**测试**
   要先 `await asyncio.sleep(0.1)` 或 `await asyncio.gather(*backend._inflight_tasks)`
   再断言 fake-hermes 收到
5. **assistant_text 拼接错**：echo backend 每 chunk ≤20 char，要把所有 yield
   值 join 起来；不要把 SSE 帧的 `data: ...\n\n` 当 assistant_text 拼

## Suggested Steps

```bash
# 0. 切到仓库根 + 用 conda python + 关 proxy（H016 教训）
cd ~/code/robot_class/final_pro_xiaozhi_robot
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
alias pyx='/home/kk/miniconda3/bin/python'
git status --short    # 期望干净（openai-shim/ 已 committed）

# 1. 写新文件
cd openai-shim
# 写 src/openai_shim/hermes_backend.py
# 改 src/openai_shim/app.py（加 env 读取 + backend 装配）
# 写 tests/test_hermes_fork.py
# 改 README.md（加 H019 段）

# 2. 跑测试
pyx -m pytest -xvs tests/   # 期望：H018 原 2 个 + H019 新 3 个 = 5 个全 PASS

# 3. 手测（可选）：起 fake-hermes 在 :9999 + 起 shim 在 :8089 + curl
# （省略；测试已覆盖）

# 4. git status + 贴回 What I Did
git status --short
```

## Error-handling discipline

- **Cosmetic** (typo / 漏 import / pip 包名拼错) → 自己改、What I Did 提一句
- **Substantive** (asyncio task 提前 GC / fork 阻塞 SSE / httpx mock 不通) →
  status: blocked + 完整 stderr + 已试 2-3 种修法
- **不要超 scope**：跑通 3 个新测就停，**不要**顺手写真 Hermes adapter / 真 LLM
  backend / ESP32 集成
- **PyPI 装不上 (sandbox)**：blocked + 完整 stderr，由 planner main-loop unblock
  （H015/H018 同模式）
- **proxy 杀本地连接 (H016 教训)**：跑测前先 `unset *PROXY`；如果 fake-hermes
  ASGI mock 不出网就无所谓，但 spike 启动 banner 里把 proxy 状态 echo 一下

## Recovery

| 症状 | 可能原因 | 修 |
|---|---|---|
| `RuntimeWarning: coroutine was never awaited` | fork task ref 丢了 | 把 task append 到 instance set |
| fake-hermes 测试断言 `not_called` | task 还没跑完 server 就检查 | 在断言前 `await asyncio.sleep(0.05)` 或 await inflight set |
| SSE 测试时 `httpx.RemoteProtocolError` | 测试 client 提前关 connection | 用 `async with` 包 stream 全收完再退 |
| `HermesBackend` 替换后 H018 原测炸 | env 漏 setattr / app instance 复用错 | 用 `monkeypatch.delenv("HERMES_TRANSCRIPT_URL", raising=False)` |

## For Auditor

不发 auditor。M2 完整集成 (H016 done + H018 done + H019 done + H020 真 LLM)
累计后一起 batch review。

## Open Questions for Planner

- H019 完 → **H020 真 LLM backend**：把 `EchoBackend` 替成 `DeepSeekBackend` /
  `OpenAIBackend`（包 `openai.AsyncOpenAI`），仍走 SSE。这是 ADR-0005 真正
  上 demo 的最后一步
- H019 完 → 可以**真接 Hermes**做一次手测：起 `hermes webhook subscribe
  xiaozhi-transcript ...` + 起 shim + curl 触发 → 看 Hermes session 收到。
  这是 user-led，写成 H019.bis（小 handoff）
- backend 抽象层成形：H020 + H019 后，加新 LLM provider = 新 file + 一行
  app.py wiring，零侵入式
- demo §1 答辩可演 = **H016 done + H018 done + H019 done**（Hermes 在
  对话流里"看见" ESP32 user 说了什么 + 机器人答了什么）；H020 真 LLM 是
  可选 polish

## Executor's Reading
### What I'll do
- 在 H018 的 `openai-shim/` 上追加 `HermesBackend`，用 env 控制 app backend 装配，保持 Echo/SSE 既有行为不回退，并用 fake-Hermes ASGI app + 真 OpenAI SDK client 覆盖成功 fork、Hermes 500 不影响 SSE、env 未设不 fork 三条路径。

### Assumptions made
- [LOW] H018 已由 planner main-loop unblock 并归档为 done；当前 `openai-shim/` 是 H019 的直接修改基线。
- [LOW] `session` 字段只要求形如 `chatcmpl-...`；由于 H018 的 SSE `chatcmpl` id 在 `sse.py` 内生成且本 handoff 明确不改 `sse.py`，HermesBackend 会为 transcript fork 生成独立 `chatcmpl-...` session id。
- [LOW] fake-Hermes 测试会通过依赖注入 backend + `httpx.AsyncClient(ASGITransport(...))`，不依赖真实 Hermes CLI、网络或端口。
- [MED] `asyncio.CancelledError` 在当前 Python 可能继承 `BaseException`，不能被普通 `Exception` 捕获；`_post_transcript` 会显式捕获并只 log warning，以满足“不影响 SSE”约束。
- [LOW] 不修改 `openai_shim.echo_backend.EchoBackend` 和 `openai_shim.sse.chat_completion_sse`。

## What I Did
- Created `openai-shim/src/openai_shim/hermes_backend.py` with `HermesBackend`, inner `TextBackend` composition, assistant delta accumulation, `chatcmpl-...` transcript session id, fire-and-forget `asyncio.create_task`, in-flight task retention, injected/default `httpx.AsyncClient`, and warning-only fork error handling.
- Updated `openai-shim/src/openai_shim/app.py` to read `HERMES_TRANSCRIPT_URL` at startup and wire either `HermesBackend(EchoBackend(), url)` or plain `EchoBackend`. `get_backend` is async so FastAPI does not route dependency resolution through the sandbox-sensitive sync threadpool.
- Added `openai-shim/tests/test_hermes_fork.py` for successful fake-Hermes POST, fake-Hermes 500 while SSE still succeeds, and env-unset no-fork behavior. Updated `openai-shim/tests/test_chat_completions.py` only to keep the original OpenAI SDK tests stable in this sandbox by pre-setting the SDK platform probe value.
- Updated `openai-shim/README.md` with a 13-line `H019 Hermes Fork` section containing `HERMES_TRANSCRIPT_URL`, the `hermes webhook subscribe` example, and fire-and-forget behavior.
- Confirmed `openai-shim/src/openai_shim/echo_backend.py` and `openai-shim/src/openai_shim/sse.py` have no diff.
- Did not run `hermes` CLI, did not touch `~/.hermes/`, did not touch H016 docker, ESP32, mcp-endpoint-server, or any true LLM provider integration.

Test command:

```bash
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
unset HERMES_TRANSCRIPT_URL
/home/kk/miniconda3/bin/python -m pytest -xvs tests/
```

Output:

```text
============================= test session starts ==============================
platform linux -- Python 3.13.9, pytest-9.1.0, pluggy-1.5.0 -- /home/kk/miniconda3/bin/python
cachedir: .pytest_cache
rootdir: /home/kk/code/robot_class/final_pro_xiaozhi_robot/openai-shim
configfile: pyproject.toml
plugins: asyncio-1.4.0, anyio-4.12.1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 5 items
tests/test_chat_completions.py::test_streaming_echo_roundtrip PASSED
tests/test_chat_completions.py::test_non_streaming_returns_503 PASSED
tests/test_hermes_fork.py::test_transcript_posted_when_hermes_url_set PASSED
tests/test_hermes_fork.py::test_sse_still_works_when_hermes_returns_500 PASSED
tests/test_hermes_fork.py::test_no_fork_when_hermes_url_unset PASSED
============================== 5 passed in 2.96s ===============================
```

`git status --short`:

```text
 M docs/handoffs/active/2026-06-19-m2-hermes-fork-transcript-019.md
 ? esp/xiaozhi-esp32
 M openai-shim/README.md
 M openai-shim/src/openai_shim/app.py
 M openai-shim/tests/test_chat_completions.py
?? openai-shim/src/openai_shim/hermes_backend.py
?? openai-shim/tests/test_hermes_fork.py
```

## Open Questions for Auditor
- None. H019 explicitly says no auditor handoff; M2 batch review is deferred.
