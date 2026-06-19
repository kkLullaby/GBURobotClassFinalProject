---
id: 2026-06-19-m2-deepseek-backend-021
from: planner
to: executor
parent: 2026-06-19-m2-hermes-fork-transcript-019
supersedes:
status: done
created: 2026-06-19
artifacts:
  - openai-shim/src/openai_shim/deepseek_backend.py (new)
  - openai-shim/src/openai_shim/app.py (改：backend 选择策略)
  - openai-shim/tests/test_deepseek_backend.py (new)
  - openai-shim/tests/test_chat_completions.py (无改动；H018 行为零回退)
  - openai-shim/tests/test_hermes_fork.py (无改动；H019 行为零回退)
  - openai-shim/README.md (改：H021 段)
---

## Why now

ADR-0005 主线已通：M2 OpenAI-compat SSE 出口 (H018) + Hermes transcript
fork (H019) + 真 Hermes 验证 (H020, 同时进行)。**剩下最后一块**：M2 后端
回的是"echoed: hi" — 没真智能。本 spike 加一个 **DeepSeekBackend**：包
`openai.AsyncOpenAI(base_url='https://api.deepseek.com')`，把 messages
原样转给 DeepSeek，把 DeepSeek 流式回的内容**逐 chunk** yield 出去——这样
M2 既是 OpenAI-compat 端、又是真正的 LLM proxy；同时复用 H019 的
HermesBackend wrapping，把 transcript fork 给 Hermes。

跟 H015 / H018 / H019 同模式：sandbox-friendly Python spike，可交 codex /
claude agent；scope 严格不外溢。**H020 user-led 跟本 handoff 互不阻塞**：
H020 不需要真 LLM，本 handoff 不需要真 Hermes。

## Objective

在 `openai-shim/` 内加一个 **DeepSeekBackend**，使得 `POST /v1/chat/completions`
处理流程中 backend 从 echo 升级到真 LLM：

```
xiaozhi-server → M2 openai-shim
                   ├── HermesBackend wraps ──→ DeepSeekBackend
                   │                                ↓
                   │                         openai.AsyncOpenAI(base_url=api.deepseek.com)
                   │                                ↓
                   │                         真 DeepSeek stream chunks ──→ yield text deltas
                   │                                                       ↓
                   └── HermesBackend 累 assistant_text → fire-forget POST /webhooks/...
                                                        ↓
                                                   SSE 流回 server
```

backend selection 策略（**显式 env**）：

```
OPENAI_SHIM_BACKEND=echo                  (default; H018 behaviour)
OPENAI_SHIM_BACKEND=deepseek + DEEPSEEK_API_KEY=...
HERMES_TRANSCRIPT_URL=...                 (orthogonal: 任一 backend 都可被 wrap)
```

测法：

- **不需要真 DeepSeek key**——pytest 起 fake-deepseek ASGI app (同 H019
  fake-hermes 模式)，处理 `/chat/completions` 返回 SSE 假流；用 `httpx.ASGITransport`
  注入到 AsyncOpenAI client；断言 DeepSeekBackend yield 出来的 deltas 等于
  fake-deepseek 喂的内容
- **HermesBackend 仍 wrap DeepSeekBackend**：组合测一次（HermesBackend
  在 DeepSeekBackend 上层，fork transcript 给 fake-hermes 不变）
- 一发"backend 选择"测：app.py 的 `_build_backend()` 在不同 env 下返回
  正确的 backend 组合

## Constraints

- **不**改 `xiaozhi-mcp-adapter/`、`esp/`、`docs/contracts/`、`docs/adr/`、
  `docs/handoffs/` 任何既有文件（除本 handoff 自身追加段）
- **不**改 `openai_shim.echo_backend.EchoBackend` 一行
- **不**改 `openai_shim.hermes_backend.HermesBackend` 一行
- **不**改 `openai_shim.sse.chat_completion_sse` 一行
- **不**实现 OpenAI / Anthropic / Ollama backend (DeepSeek 一个够 H020-22 demo;
  其它 H024+)
- **不**实现 function-calling pass-through（tool_calls delta）— H023+ 才上
- **不**实现 multi-tenant / per-session model 选择（仅看 `request.model` 字段
  决定 backend 已够；本 handoff 不到这层）
- **不**实现 retry / rate-limit / token quota
- **不**真调 `https://api.deepseek.com`（**没有 API key 不会跑**；如果 sandbox
  里有 `DEEPSEEK_API_KEY` 也**禁止**做 outbound call——只跑 fake-deepseek）
- Python ≥ 3.8；不增新依赖（`openai`/`httpx` 已装；pytest fixture 用
  monkeypatch + ASGITransport）
- 错误处理纪律按 H010 §Error-handling discipline
- transcript fork 行为 (HermesBackend wrap) **保持 H019 不变**：fire-and-forget
- **Sandbox-friendly**：本 handoff 设计为 codex / claude agent 在 sandbox 内
  能完整跑（无 docker、无 USB、无外部网络、无 DeepSeek key）
- 一切用 [`pyx`](../../.claude/memory/shared/global-commands.md)
  (`/home/kk/miniconda3/bin/python`) 跑

## Acceptance Criteria

- [ ] 新建 `openai-shim/src/openai_shim/deepseek_backend.py`：
      - `class DeepSeekBackend`：
        - `__init__(self, api_key: str, base_url: str = 'https://api.deepseek.com',
          model_override: Optional[str] = None, http_client: Optional[httpx.AsyncClient] = None)`
        - 内部用 `openai.AsyncOpenAI(api_key=api_key, base_url=base_url,
          http_client=http_client)` 建 client（**注入** http_client 是为
          ASGITransport 测试用）
        - `async def stream_response(messages, model) -> AsyncIterator[str]`：
          - 把 messages 转成 dict list（用 `_message_role/_message_content`
            helper 或 pydantic dump）
          - 把 model = `model_override or model`
          - 调 `client.chat.completions.create(..., stream=True)`
          - `async for chunk in stream: if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content`
        - 任何 `openai.APIError`/`httpx.HTTPError` 上抛（**不**吞）——M2 主路径
          应该 fail-fast，HermesBackend 包它时也只 fork 不 try (fork 是
          fire-and-forget, 但 inner backend 异常该往外冒)
      - **不**导出 module-level state；测试用注入构造
- [ ] `openai-shim/src/openai_shim/app.py` 改：
      - 新 env 读取：`OPENAI_SHIM_BACKEND` (default `"echo"`),
        `DEEPSEEK_API_KEY` (no default), `DEEPSEEK_BASE_URL` (default
        `"https://api.deepseek.com"`)
      - `_build_backend()` 升级：
        ```python
        backend_kind = os.environ.get("OPENAI_SHIM_BACKEND", "echo").lower()
        if backend_kind == "deepseek":
            api_key = os.environ.get("DEEPSEEK_API_KEY")
            if not api_key:
                raise RuntimeError("DEEPSEEK_API_KEY required when OPENAI_SHIM_BACKEND=deepseek")
            inner = DeepSeekBackend(
                api_key=api_key,
                base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            )
        else:
            inner = EchoBackend()

        transcript_url = os.environ.get("HERMES_TRANSCRIPT_URL")
        if transcript_url:
            return HermesBackend(inner, transcript_url)
        return inner
        ```
      - **保持** H018/H019 行为：env 都不设 → EchoBackend；只设
        `HERMES_TRANSCRIPT_URL` → HermesBackend(EchoBackend, ...) (H019 重测)
- [ ] **不**改 echo_backend / hermes_backend / sse 一行
- [ ] `tests/test_chat_completions.py` 原 2 测 + `test_hermes_fork.py` 原 3 测
      **保持 PASS**（H018/H019 行为零回退）
- [ ] 新建 `openai-shim/tests/test_deepseek_backend.py`，至少 4 个测试：
      1. `test_deepseek_backend_yields_real_stream_chunks`：起 fake-deepseek
         FastAPI app（接 `POST /chat/completions`），返回手拼好的 SSE 流
         (3-4 个 `data: {"choices":[{"delta":{"content":"X"}}]}\n\n` chunk +
         `data: [DONE]\n\n`)；通过 `httpx.AsyncClient(transport=ASGITransport(app=fake_deepseek))`
         注入 DeepSeekBackend；call `stream_response([{"role":"user","content":"hello"}], "deepseek-chat")`；
         断言 yield 出来的 list join 起来等于 fake 那串
      2. `test_hermes_wraps_deepseek_forks_real_assistant_text`：DeepSeekBackend
         同上 fake-deepseek 注入；HermesBackend wrap 它，transcript_url 指
         fake-hermes（同 H019 mock）；跑一遍；断言 fake-hermes 收到 POST，
         `assistant` 字段 = fake-deepseek 喂的全文（**不是** "echoed:"）
      3. `test_build_backend_with_env_matrix`：用 monkeypatch 设/清不同
         env 组合，断言 `_build_backend()` 返回正确类型：
         - 全无 → EchoBackend
         - 只 OPENAI_SHIM_BACKEND=deepseek + DEEPSEEK_API_KEY=fake → DeepSeekBackend
         - 同上 + HERMES_TRANSCRIPT_URL → HermesBackend(DeepSeekBackend(...), ...)
         - OPENAI_SHIM_BACKEND=deepseek 但缺 KEY → RuntimeError
      4. `test_deepseek_api_error_propagates`：fake-deepseek 返回 500；
         调用 `stream_response` 应抛 `openai.APIError`（或 subclass）；
         不应被 swallow
- [ ] `pyx -m pytest -xvs tests/` 通过；输出贴 What I Did（≤40 行）
      （H018 2 + H019 3 + H021 4 = **9 个全 PASS**）
- [ ] `README.md` 加 1 段 "H021 DeepSeek Backend" (≤25 行)：
      - env 矩阵：`OPENAI_SHIM_BACKEND=deepseek` / `DEEPSEEK_API_KEY=...` /
        组合 `HERMES_TRANSCRIPT_URL=...`
      - 一行 curl 示例（**伪 key**，不真跑）：
        ```bash
        OPENAI_SHIM_BACKEND=deepseek DEEPSEEK_API_KEY=sk-... \
          /home/kk/miniconda3/bin/python -m uvicorn openai_shim.app:app --port 8089
        curl -N -X POST http://localhost:8089/v1/chat/completions \
          -H "Authorization: Bearer fake" -H "Content-Type: application/json" \
          -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"用一句话介绍你自己"}],"stream":true}'
        ```
      - 引一句指向 H022 end-to-end
- [ ] `git status` 输出贴 What I Did，预期：
      ```
      M openai-shim/src/openai_shim/app.py
      M openai-shim/README.md
      ?? openai-shim/src/openai_shim/deepseek_backend.py
      ?? openai-shim/tests/test_deepseek_backend.py
      ```
- [ ] **不**真调 DeepSeek API；**不**改 `~/.hermes/`；**不**碰 H016 docker
- [ ] **不**写 OpenAI/Anthropic backend；**不**写 function-calling；**不**
      写 ESP32 / 真 Hermes 集成

## Context Pointers

- @docs/adr/0005-openai-compat-transcript-egress.md (M2 责任分层)
- @docs/handoffs/archive/2026-06-19-m2-spike-openai-shim-018.md (H018 echo
  shim 基线)
- @docs/handoffs/archive/2026-06-19-m2-hermes-fork-transcript-019.md (H019
  HermesBackend wrap 模式 — DeepSeekBackend 直接复用 wrap)
- @openai-shim/src/openai_shim/echo_backend.py (`TextBackend` Protocol —
  DeepSeekBackend 实现它，**不**继承)
- @openai-shim/src/openai_shim/hermes_backend.py (wrap 实现参考 +
  `_message_role/_message_content` helper 复用)
- @openai-shim/src/openai_shim/app.py (`_build_backend()` 改这里)
- @openai-shim/tests/test_hermes_fork.py (fake server ASGITransport 套路 +
  `_openai_client()` helper 应继续用)
- @.claude/memory/shared/global-commands.md §Python (pyx 别名)
- @docs/adr/0003-executor-runs-in-main-loop.md (sandbox-friendly 设计)
- OpenAI SDK AsyncOpenAI streaming 文档：
  `/home/kk/miniconda3/lib/python3.13/site-packages/openai/_streaming.py`
- DeepSeek base_url：`https://api.deepseek.com` (xinnan-tech config 实测)

## Out of Scope

- 不实现 OpenAI / Anthropic / Ollama backend — H023+ 单独 spike
- 不实现 function-calling (tool_calls delta) — H023+
- 不实现 vision / image content pass-through
- 不实现 reasoning chunks (DeepSeek-R1 "thinking" delta) — 单独 spike
- 不实现 backend 自动 failover / retry
- 不实现 per-request backend 选择（同进程多 backend 路由）
- 不实现 ESP32 / mcp-endpoint / 真 Hermes 集成
- 不改 H016 / H020 的运行环境

## Candidate Root Causes（跑不通时先查）

1. **AsyncOpenAI 不接受 ASGITransport** — 较新版 `openai` SDK 允许 `http_client`
   传 `httpx.AsyncClient` 实例；老版本可能要 `_client=...`。锁
   `openai>=1.30`（H018 已锁）
2. **fake-deepseek 没 chunked content-type** — `text/event-stream` 必须带；
   `StreamingResponse(media_type="text/event-stream")` 即可
3. **AsyncOpenAI base_url 拼路径** — `base_url="http://testserver"` 会变成
   `http://testserver/chat/completions`（没 `/v1`）；要么 fake-deepseek mount
   在 `/chat/completions` 直挂、要么 base_url 带 `/v1` 然后 fake 也挂 `/v1`
4. **chunk 字段** — fake 必须给 `id/object/created/model/choices[0].index`
   都填，否则 SDK ValidationError（H018 候选 #1 同问题）
5. **测试间 env 污染** — monkeypatch 用 `setenv/delenv`，**不**直接改
   `os.environ`；`_build_backend` 每次重新读 env (它已经是这样写的，但
   `_backend` 是 module-level 单例，**测试要 import 后手动调 `_build_backend()`
   验返回值**，**不**依赖 app 启动期那次 build)

## Suggested Steps

```bash
# 0. cwd + python + proxy
cd ~/code/robot_class/final_pro_xiaozhi_robot
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
alias pyx='/home/kk/miniconda3/bin/python'
git status --short    # 期望干净 (?? esp/xiaozhi-esp32 是 submodule placeholder 忽略)

# 1. 写新文件
cd openai-shim
# 写 src/openai_shim/deepseek_backend.py
# 改 src/openai_shim/app.py （_build_backend）
# 写 tests/test_deepseek_backend.py
# 改 README.md（加 H021 段）

# 2. 跑测试
pyx -m pytest -xvs tests/   # H018(2) + H019(3) + H021(4) = 9 全 PASS

# 3. 手测（可选; 你**不要**真用 key 跑）
# 仅 import smoke:
pyx -c "from openai_shim.deepseek_backend import DeepSeekBackend; print(DeepSeekBackend)"

# 4. git status + 贴回 What I Did
git status --short
```

## Error-handling discipline

- **Cosmetic** (typo / 漏 import / pip 包名拼错) → 自己改、What I Did 提一句
- **Substantive** (AsyncOpenAI 不接 transport / fake-deepseek SSE 客户端不
  parse / monkeypatch 没生效) → status: blocked + 完整 stderr + 已试 2-3 修法
- **不要超 scope**：4 个新测过就停，**不**顺手加 OpenAI/Anthropic backend
  或真 LLM 联调
- **PyPI 装不上 (sandbox)**：H018 已装齐，本 handoff 无新依赖
- **不要真调 DeepSeek**：sandbox 环境如果有 key 也不允许 outbound；如果检测到
  会触发 outbound 的 import path（比如 `openai._client._make_request`）
  必须由 ASGITransport 兜底

## Recovery

| 症状 | 可能原因 | 修 |
|---|---|---|
| `openai.AsyncOpenAI(http_client=...)` 报 unknown kwarg | SDK 版本旧 | `openai>=1.30` 已锁；`uv pip install --upgrade openai` |
| fake-deepseek 返 SSE 但 SDK 报 `ValidationError: object` 字段 | chunk 字段不全 | 拷 H018 sse.py 的 `_chat_chunk` 字段当模板 |
| `test_hermes_wraps_deepseek` 收到 assistant="" | DeepSeek delta 拼接漏 None 检查 | `if chunk.choices and chunk.choices[0].delta.content:` |
| build_backend env matrix 测试相互污染 | 用 `monkeypatch.delenv(..., raising=False)` 不是直接 `os.environ.pop` |
| `_backend` 单例：测试改 env 但 `app._backend` 没变 | 单例已固化 | 测试直接调 `_build_backend()` 验返回；**不要**依赖 `app._backend` |

## For Auditor

不发 auditor。M2 完整集成 (H018+H019+H020+H021) 后批 review 时一起看。

## Open Questions for Planner

- H021 完 → **H022 end-to-end**：DeepSeek backend + Hermes fork + 真 ESP32
  voice 全链路一次 demo（user-led，~1 小时手测；可挂答辩前一晚跑）
- DeepSeek reasoning chunks (R1 `<think>` 段) 也走 delta.content 吗？还是
  在 `delta.reasoning_content`？写 H023.bis 单独 spike
- DeepSeek function-calling delta：H023 跟 M4 (ESP32 tools) 联调时一起做
- session id 还在 hermes_backend 内生成 chatcmpl-<uuid>：H021 不解决；
  Week 1.5 "session 复用 ESP32 device_id" 任务时一起改

## Executor's Reading
### What I'll do
- 在 H019 的 `openai-shim/` 基线上新增 `DeepSeekBackend`，用显式 env 扩展 `_build_backend()`，只用 fake-DeepSeek/fake-Hermes ASGITransport 测试 DeepSeek streaming、Hermes wrap、env matrix 和 API error propagation，同时保持 H018/H019 既有测试通过。

### Assumptions made
- [LOW] 当前 H018/H019 已归档且 `openai-shim/` 是 H021 的直接基线；工作树除 `? esp/xiaozhi-esp32` 外干净。
- [LOW] fake-DeepSeek route 使用 `/chat/completions`，因为 `DeepSeekBackend(base_url="http://fake-deepseek")` 交给 OpenAI SDK 后会拼该路径。
- [LOW] fake-DeepSeek SSE chunk 会填 `id/object/created/model/choices[0].index/delta`，复用 H018 的 OpenAI SDK 严格解析要求。
- [LOW] DeepSeekBackend 内部 client 保存为 instance 属性，测试可以在注入 ASGITransport 时设置 `_platform = "Linux"`，沿用 H019 为避免 sandbox 线程池平台探测卡住的处理方式。
- [LOW] `OPENAI_SHIM_BACKEND` 除 `deepseek` 外均按默认 echo 处理；H021 未要求 unknown backend 报错。
- [MED] `DeepSeekBackend` 对 `openai.APIError` / `httpx.HTTPError` 不做捕获即可满足“上抛”：OpenAI SDK 会把 fake 500 转成 `openai.APIStatusError`，它是 `openai.APIError` 子类。

## What I Did
- Created `openai-shim/src/openai_shim/deepseek_backend.py` with `DeepSeekBackend(api_key, base_url, model_override, http_client)`, OpenAI SDK streaming, message dict conversion, and delta-content yielding. It does not catch `openai.APIError` or `httpx.HTTPError`, so main-path LLM errors propagate.
- Updated `openai-shim/src/openai_shim/app.py` backend selection with `OPENAI_SHIM_BACKEND`, `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and orthogonal `HERMES_TRANSCRIPT_URL` wrapping. Default env remains `EchoBackend`; `HERMES_TRANSCRIPT_URL` alone still wraps echo.
- Added `openai-shim/tests/test_deepseek_backend.py` covering fake-DeepSeek SSE chunk yield, HermesBackend wrapping DeepSeek and forking the real assistant text, `_build_backend()` env matrix, and fake-DeepSeek 500 propagating as `openai.APIError`.
- Updated `openai-shim/README.md` with a 23-line `H021 DeepSeek Backend` section: env matrix, placeholder-key uvicorn command, curl example, and H022 end-to-end note.
- Confirmed no diff in `openai-shim/src/openai_shim/echo_backend.py`, `openai-shim/src/openai_shim/hermes_backend.py`, `openai-shim/src/openai_shim/sse.py`, `openai-shim/tests/test_chat_completions.py`, or `openai-shim/tests/test_hermes_fork.py`.
- Did not call the real DeepSeek API, did not run Hermes CLI, did not touch `~/.hermes/`, H016 docker, ESP32, mcp-endpoint-server, OpenAI/Anthropic/Ollama backend, or function-calling code.

Smoke command:

```bash
/home/kk/miniconda3/bin/python -c "from openai_shim.deepseek_backend import DeepSeekBackend; print(DeepSeekBackend)"
```

Smoke output:

```text
<class 'openai_shim.deepseek_backend.DeepSeekBackend'>
```

Test command:

```bash
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
unset HERMES_TRANSCRIPT_URL OPENAI_SHIM_BACKEND DEEPSEEK_API_KEY DEEPSEEK_BASE_URL
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
collecting ... collected 9 items
tests/test_chat_completions.py::test_streaming_echo_roundtrip PASSED
tests/test_chat_completions.py::test_non_streaming_returns_503 PASSED
tests/test_deepseek_backend.py::test_deepseek_backend_yields_real_stream_chunks PASSED
tests/test_deepseek_backend.py::test_hermes_wraps_deepseek_forks_real_assistant_text PASSED
tests/test_deepseek_backend.py::test_build_backend_with_env_matrix PASSED
tests/test_deepseek_backend.py::test_deepseek_api_error_propagates PASSED
tests/test_hermes_fork.py::test_transcript_posted_when_hermes_url_set PASSED
tests/test_hermes_fork.py::test_sse_still_works_when_hermes_returns_500 PASSED
tests/test_hermes_fork.py::test_no_fork_when_hermes_url_unset PASSED
============================== 9 passed in 3.27s ===============================
```

`git status --short`:

```text
 M docs/handoffs/active/2026-06-19-m2-deepseek-backend-021.md
 ? esp/xiaozhi-esp32
 M openai-shim/README.md
 M openai-shim/src/openai_shim/app.py
?? openai-shim/src/openai_shim/deepseek_backend.py
?? openai-shim/tests/test_deepseek_backend.py
```

## Open Questions for Auditor
- None. H021 explicitly says no auditor handoff; M2 batch review is deferred.
