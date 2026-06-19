---
id: 2026-06-19-m2-spike-openai-shim-018
from: planner
to: executor
parent: 2026-06-19-m1-spike-echo-tool-015
supersedes:
status: pending
created: 2026-06-19
artifacts:
  - openai-shim/ (new Python package, repo root)
  - openai-shim/pyproject.toml
  - openai-shim/src/openai_shim/{__init__,app,sse,echo_backend}.py
  - openai-shim/tests/test_chat_completions.py
  - openai-shim/README.md
---

## Why M2 spike now

[ADR-0005](../adr/0005-openai-compat-transcript-egress.md) 把 M2 升级为
**transcript 入口**：M2 不再只是"中转 LLM 调用"，它在 `/v1/chat/completions`
handler 里要 fork 出一份 transcript 给 Hermes。

但 fork-to-Hermes 之前，先得把**最小可被 xinnan-tech server 替换的 OpenAI 兼容
shim** 写出来——HTTP/SSE 字段完全对齐，跑通 round-trip。这就是 H018 的范围。

跟 [H015](archive/2026-06-19-m1-spike-echo-tool-015.md) 同模式：sandbox-friendly
spike，可交 codex / claude agent；不连 ESP32、不需要真 LLM key。

## Objective

在仓库根目录建 `openai-shim/` Python 包，跑通**最小 OpenAI-compatible
streaming round-trip**：

```
xinnan-tech server (用 openai SDK 客户端)         M2 openai-shim (我们写)
  ↓ POST /v1/chat/completions                       ↑
  ↓ Authorization: Bearer <fake>                    │ FastAPI handler
  ↓ {"model":"echo","messages":[{"role":"user",     │
  ↓   "content":"hi"}], "stream": true}             │
  ↓                                                 ↓
  ↑ event-stream: text/event-stream                 │ chunked SSE
  ↑ data: {"id":"...","choices":[{"delta":{"content│   每个 chunk 用 openai
  ↑     ":"echoed: hi"}}]}\n\n                     │   SDK 的数据类 dump
  ↑ ...                                             │   (不手拼 JSON)
  ↑ data: [DONE]\n\n                                ↓
```

测法：

- **不需要真 xinnan-tech server**——pytest 起 FastAPI TestClient，**用真
  openai SDK 客户端** (`openai.OpenAI(base_url=app_url)`) 发请求，
  断言收到的 ChatCompletionChunk 流符合预期
- Backend 是 echo（把 user message 反射回去），不调真 LLM key

## Constraints

- **不**改 `xiaozhi-mcp-adapter/`、`esp/`、`docs/contracts/`、`docs/adr/`、
  `docs/handoffs/`、`.claude/` 任何既有文件（除本 handoff 自身追加段）
- **不**实现 Hermes 集成（fork transcript 也不做）—— H019+ 才动
- **不**实现真 LLM provider 路由（H020+ 才做）
- **不**实现 non-streaming (`stream=False`) 分支——只 `stream=True`
  （ADR-0005 说 xinnan-tech 用 SDK 强制开 stream，non-stream 永远走不到）
- **不**实现 function-calling chunks（tool_calls delta），但要**留可扩展位**
- Python ≥ 3.8，依赖只允许：`fastapi`, `uvicorn`, `openai>=1.30`, `pytest`,
  `pytest-asyncio`, `httpx` (TestClient 用)
- 错误处理纪律按 [H010 §Error-handling discipline](archive/2026-06-19-mcp-transcript-egress-spike-010.md)
- **Sandbox-friendly**：本 handoff 设计为 codex / claude agent 在 sandbox 内
  能完整跑（无 docker、无 USB、无外部网络）
- 一切用 [`pyx`](../../.claude/memory/shared/global-commands.md) (`/home/kk/miniconda3/bin/python`) 跑

## Acceptance Criteria

- [ ] 包结构：`openai-shim/` 在仓库根，含 `pyproject.toml`、`src/openai_shim/{__init__,app,sse,echo_backend}.py`、
      `tests/test_chat_completions.py`、`README.md`
- [ ] `pyproject.toml` PEP 621；`name="openai-shim"`，`python_requires=">=3.8"`，
      `optional-dependencies.test = ["pytest>=7", "pytest-asyncio", "httpx"]`
- [ ] `app.py` 是 FastAPI app：
      - `POST /v1/chat/completions` handler
      - 接 OpenAI 标准请求体 (Pydantic model — 可手写 schema 或用 openai SDK 的 types)
      - 接 `Authorization: Bearer <anything>` (不校验，但要 accept)
      - `stream=True` 走 SSE 路径；`stream=False` 直接返回 503 + body
        `{"error":"non-streaming unsupported in spike"}`
- [ ] `sse.py` 是 SSE 流生成器：
      - 用 `openai.types.chat.ChatCompletionChunk` 数据类构造每个 chunk
      - `.model_dump_json()` 序列化（**不**手拼 JSON）
      - chunk 之间 `data: <json>\n\n`，结束 `data: [DONE]\n\n`
      - 最后实际 content chunk 的 `choices[0].finish_reason = "stop"`
      - 含 `id` (`chatcmpl-<random>`), `object="chat.completion.chunk"`,
        `created=<epoch>`, `model=<request.model>`
- [ ] `echo_backend.py` 是 backend 接口：
      - 抽象层：`async def stream_response(messages, model) -> AsyncIterator[str]`
        — 输出一段段 text delta（每段 ≤ 20 chars 模拟 token 流）
      - echo 实现：取最后一个 user message 的 content，前面加 `"echoed: "`，
        切成 N 段 yield 出去
      - 留扩展位：`app.py` 通过依赖注入用 backend；后续 H019 接 Hermes
        只需替换 backend 不改 app/sse
- [ ] `tests/test_chat_completions.py` 至少 2 个测试：
      1. `test_streaming_echo_roundtrip`：用 `openai.OpenAI(base_url=test_url, api_key="sk-fake")`
         的客户端发 `chat.completions.create(model="echo", messages=[{"role":"user","content":"hi"}], stream=True)`，
         收齐所有 chunk 后拼接 content，断言 `== "echoed: hi"`，且最后 chunk
         `finish_reason == "stop"`
      2. `test_non_streaming_returns_503`：发 `stream=False`，期望 HTTPError 503
- [ ] `pytest -xvs tests/` 通过；输出贴回 What I Did（≤30 行）
- [ ] `README.md` ≤ 60 行，含：架构图 (ascii)、装法、`uvicorn` 启动命令、
      curl 手测命令、和 H019 / ADR-0005 的关系
- [ ] **不**写 Hermes / fork transcript / 真 LLM 路由
- [ ] `git status` 输出贴回 What I Did，预期：单一新目录 `?? openai-shim/`

## Context Pointers

- @docs/adr/0005-openai-compat-transcript-egress.md (**先读这个**——M2 是
  transcript 入口的设计动机和后续 fork 的位置)
- @docs/research-notes/xinnan-tech-openai-and-mcp.md §1 + §3 (**关键** —
  必看 §3 的 "M2 shim 必输 vs 可选" SSE 字段对照表)
- @docs/contracts/api/v1/esp32-to-server-handshake.md (M2 不在这个 contract
  范围内，是 server-internal 配置；但握手协议要了解上下文)
- @docs/handoffs/archive/2026-06-19-m1-spike-echo-tool-015.md (sibling
  spike，照同样模式：pyproject + tests + README，scope 严格保 spike 干净)
- @.claude/memory/shared/global-commands.md §Python (pyx 别名 / 装包套路)
- @docs/adr/0003-executor-runs-in-main-loop.md (sandbox-friendly 设计)
- OpenAI SDK 数据类参考：`/home/kk/miniconda3/lib/python3.13/site-packages/openai/types/chat/chat_completion_chunk.py`
- FastAPI SSE 示例：https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse

## Out of Scope

- 不实现 Hermes session 注入（H019 才做）
- 不实现真 LLM provider（OpenAI / Anthropic / DeepSeek）— 都是 backend
  接口的实现，本 spike echo 一个足够
- 不实现 function-calling (tool_calls) 流
- 不实现 vision / image content
- 不实现 multi-turn 历史持久化（每次请求独立）
- 不上 Docker / 不写 systemd / 不上 CI
- 不实现 rate limit / quota / auth (Authorization header 接受任意值)
- 不实现 stream=False（明示 503）

## Candidate Root Causes（round-trip 跑不通时先查）

1. **openai SDK 在 client 侧对 chunk 严格校验** — 缺 `id` / `object` /
   `created` / `model` 会 ValidationError；缺 `choices[0].index` 也会
2. **SSE 帧格式** — `data: ` 后面必须有空格；行尾必须 `\n\n` (两个换行)；
   `[DONE]` 不带引号，是字面量
3. **finish_reason 时机** — 不要在第一个 content chunk 就发 `finish_reason`，
   要在最后一个 content chunk（或单独一个空 delta chunk）发
4. **TestClient SSE 支持** — `fastapi.testclient.TestClient` 同步，可能
   读不出流；用 `httpx.AsyncClient(transport=ASGITransport(app=app))` 异步
   测更稳
5. **openai SDK 版本** — 1.30 以下数据类字段名不一样；锁 `openai>=1.30`

## Suggested Steps

```bash
# 0. 切到仓库根 + 用 conda python
cd ~/code/robot_class/final_pro_xiaozhi_robot
git status --short    # 期望干净
alias pyx='/home/kk/miniconda3/bin/python'

# 1. 包骨架
mkdir -p openai-shim/{src/openai_shim,tests}
cd openai-shim
# 写 pyproject.toml、src/.../{__init__,app,sse,echo_backend}.py、
# tests/test_chat_completions.py、README.md

# 2. 装本地开发 mode
UV_CACHE_DIR=/tmp/uv-cache uv pip install --system -e '.[test]'

# 3. 跑 FastAPI 烟测（手动 curl）
pyx -m uvicorn openai_shim.app:app --port 8089 &
sleep 1
curl -N -X POST http://localhost:8089/v1/chat/completions \
  -H "Authorization: Bearer fake" \
  -H "Content-Type: application/json" \
  -d '{"model":"echo","messages":[{"role":"user","content":"hi"}],"stream":true}'
# 期望：data: {...delta:{content:"echoed:"}}...  最后 data: [DONE]
kill %1

# 4. 跑测试
pyx -m pytest -xvs tests/
# 期望：2 个 test PASS

# 5. 跑完贴 git status + pytest 输出 + 一个手测 curl 输出回 What I Did
git status --short
```

## Error-handling discipline

- **Cosmetic** (typo / 漏 import / pip 包名拼错) → 自己改、What I Did 提一句
- **Substantive** (openai SDK API 不会用 / SSE 帧客户端识别不出 / async
  死锁) → status: blocked + 完整 stderr + 已试 2-3 种修法
- **不要超 scope**：echo SSE 通了就停，**不要**顺手写 backend 真 LLM 路由
  或 Hermes fork
- **PyPI 装不上 (sandbox)**：blocked + 完整 stderr，由 planner main-loop unblock
  （H015 同模式）

## Recovery

- FastAPI app 起不来：`pyx -c "from openai_shim.app import app; print(app)"` 单独 import 试
- chunk 序列化拒收：`python -c "from openai.types.chat import ChatCompletionChunk; print(ChatCompletionChunk.model_json_schema())"` 看必填字段
- pytest 卡住：加 `pytest --timeout=10`；`pytest-asyncio` 模式选 `auto`

## For Auditor

不发 auditor。M2 真业务集成（H019+ Hermes fork）累计 3-4 个 handoff done
后一起 batch review。

## Open Questions for Planner

- H018 完 → **H019 Hermes fork 接入**：app handler 在生成 SSE 流的同时，
  把 user message + assistant 最终拼回的 content 发给 Hermes (走 Hermes 的
  message-send API 或 MCP server)，让 transcript 进入 Hermes session。
  这是 ADR-0005 §2 的主线，要单独发 handoff
- H016 done + H018 done + H019 done = **demo §1 答辩可演**（roadmap §Week 1.4）
- backend 接口抽象出来之后，H020 加真 LLM provider (DeepSeek / OpenAI /
  Anthropic) 只是写多一个 backend
