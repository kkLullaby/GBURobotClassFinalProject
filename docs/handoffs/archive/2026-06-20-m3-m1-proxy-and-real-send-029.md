---
id: 2026-06-20-m3-m1-proxy-and-real-send-029
from: planner
to: executor
parent: 2026-06-19-m3-hermes-plugin-spike-028
supersedes:
status: blocked
superseded-by: 2026-06-20-m3-m1-proxy-and-real-send-029v2
created: 2026-06-20
artifacts:
  - xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/show_text_proxy.py (新)
  - xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/proxy_http.py (新, sidecar)
  - xiaozhi-mcp-adapter/tests/test_show_text_proxy.py (新)
  - hermes-xiaozhi-plugin/src/hermes_xiaozhi/adapter.py (改: send() 真走 M1)
  - hermes-xiaozhi-plugin/tests/test_adapter_send.py (改: 加 e2e mock case)
---

## Why now

H028 (Stage A plugin 骨架) + H028.bis (装 + hermes 启验) 完后，xiaozhi
作为 Hermes platform 已能**收** transcript。本 handoff 实现 **send()
反向真路径**——M3 三件套最后一块。

按 [m3-hermes-plugin-architecture §3](../designs/active/m3-hermes-plugin-architecture.md)
选 (b) 方案：Hermes → adapter.send → M1 → ESP32 `self.otto.show_text(
  kind="chat")`。

子任务：
1. M1 加 stdio MCP tool `show_text_proxy(device_id, text, kind)`
2. 起个 sidecar HTTP 接 M1 stdio：因 adapter (in-process w/ Hermes)
   不方便跑 stdio subprocess；HTTP `POST /tools/show_text` 更干净
3. adapter.send 真走 httpx POST sidecar (H028 桩已铺好 env XIAOZHI_MCP_ADAPTER_URL)

跟 H018/H019/H021/H025 同模式：codex sandbox 自闭环；纯 Python + httpx
mock；无新依赖。

## Objective

End-to-end mock：在 sandbox 里跑 `pytest -xvs tests/` 验证：

1. M1 `show_text_proxy` stdio tool 被调时正确组装 ESP32 MCP JSON-RPC
2. M1 sidecar HTTP `POST /tools/show_text` 转发 → fake-stdio 收到
3. adapter.send 调 sidecar HTTP → fake-sidecar 收到 device_id+text+kind

**不**真起 ESP32；**不**真起 sidecar；**不**真起 Hermes — 全 fake-ASGI mock。

## Constraints

- 改 `xiaozhi-mcp-adapter/` (M1) 和 `hermes-xiaozhi-plugin/` (M3) 两个包
- 不改 `openai-shim/` (M2)
- 不改 `esp/xiaozhi-esp32/` (M4 H024 done)
- 不动 `~/.hermes/plugins/` (real install 是 H028.bis 的事；这里只改源)
- 不真起 long-running sidecar；test 用 in-memory ASGI
- Python ≥ 3.8；新增依赖：`fastapi`（M1 sidecar 用）+ 已有 httpx + pytest
- **Sandbox-friendly**：H028 教训 — 若 PyPI DNS 失败用
  `PYTHONPATH=src:$HOME/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages`
  跑现成 env (openai-shim 已装齐 fastapi+httpx+pytest-asyncio)
- 错误纪律：blocked → 完整 stderr + 已试 2-3 修；**不要**尝试 `rm -rf`
  (H028 教训 #17)；pytest 缓存交给 planner main-loop 清

## Acceptance Criteria

### M1 side

- [ ] `xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/show_text_proxy.py` 新：
      - 函数 `build_show_text_jsonrpc(device_id: str, text: str, kind: str
        = "notification") -> dict`：返 `{"jsonrpc":"2.0","method":"tools/call",
        "params":{"name":"self.otto.show_text","arguments":{"text":text,
        "kind":kind}},"id":<uuid>}`
      - 函数 `async def call_show_text(pipe, device_id, text, kind) -> dict`：
        把 jsonrpc dump 进 pipe.stdin + 读 pipe.stdout 一行 + JSON parse
        return
      - 容错：text 超 30 汉字截断 + 加 "..."；kind 不在 {notification, chat}
        → 默认 notification

- [ ] `xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/proxy_http.py` 新：
      - FastAPI app `app = FastAPI(title="xiaozhi-mcp-adapter sidecar")`
      - POST `/tools/show_text`：body `{device_id, text, kind}` →
        调 call_show_text → return `{"ok": true, "echo": <result>}`
      - 端口默认 8650 (env `XIAOZHI_MCP_PROXY_PORT`)
      - 桩 pipe (test 时 monkeypatch 替成 fake)；**生产时**接真 xiaozhi
        mcp_endpoint pipe (留 H030 ESP32 物理实测)

- [ ] `xiaozhi-mcp-adapter/tests/test_show_text_proxy.py` 新 3 case：
      1. `test_build_show_text_jsonrpc_basic`: 验 jsonrpc 字段齐 + arguments
         含 text+kind
      2. `test_build_show_text_jsonrpc_truncates_long_text`: 50 字 text →
         output 含 "..." 且总长 ≤ 30 字
      3. `test_proxy_http_post_show_text`：httpx AsyncClient + ASGITransport
         打 fake app，monkeypatch `call_show_text` 返 `{"ok":true}`；
         验 POST `/tools/show_text` 200 + body `{"ok":true,"echo":{"ok":true}}`

- [ ] `xiaozhi-mcp-adapter/pyproject.toml`：dependencies 加 `fastapi>=0.110`

### M3 side

- [ ] `hermes-xiaozhi-plugin/src/hermes_xiaozhi/adapter.py` 改：
      - `send()` 在 `XIAOZHI_MCP_ADAPTER_URL` 设了时，POST
        `{url}/tools/show_text` body `{device_id, text, kind="chat"}`
        (H028 桩已铺，本 handoff 让它真生效)
      - 加 try/except：sidecar 不 reachable → log warning + return
        SendResult(success=True, message_id=f"degraded-{chat_id}")
        (不阻塞 Hermes session)

- [ ] `hermes-xiaozhi-plugin/tests/test_adapter_send.py` 改 → 加 e2e mock:
      4. `test_adapter_send_e2e_via_fake_sidecar`：
         - 起 fake-sidecar ASGI (mini FastAPI 1 endpoint 接 POST 验 body)
         - httpx MockTransport mount fake-sidecar to URL
         - set XIAOZHI_MCP_ADAPTER_URL
         - 调 adapter.send("ac:a7:04:30:91:78", "测试一下")
         - 验 fake-sidecar 收到 POST body 含 device_id+text+kind="chat"
         - 验 result.success is True + message_id startswith "stub-" or "sent-"

### Tests + integration

- [ ] M1 pytest 3 new case PASS
- [ ] M3 pytest 4 case (3 old + 1 new) PASS
- [ ] **不**真起 sidecar long-running
- [ ] **不**改 ~/.hermes/ / 不真跑 hermes / 不改 ESP32
- [ ] `git status --short` 输出贴 What I Did
- [ ] 不留 `__pycache__` / `.pytest_cache` 进 git (gitignore 已盖)

## Context Pointers

- @docs/handoffs/archive/2026-06-19-m3-hermes-plugin-spike-028.md (Stage A done)
- @docs/handoffs/active/2026-06-20-m3-plugin-install-and-hermes-verify-028bis.md
  (Stage B user-led, 不阻塞本 handoff)
- @docs/designs/active/m3-hermes-plugin-architecture.md §3 + §5
- @docs/contracts/api/v1/esp32-mcp-tools.md (show_text schema)
- @hermes-xiaozhi-plugin/src/hermes_xiaozhi/adapter.py (现状 stub send)
- @xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/echo_tool.py (M1 echo
  pattern 参考；本 handoff 模仿其结构写 show_text_proxy)
- @xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/pipe.py (M1 pipe 接 xiaozhi
  mcp_endpoint 的 ws 客户端；本 handoff sidecar 跟它解耦, **不**碰它)
- @openai-shim/src/openai_shim/app.py (FastAPI pattern 参考)
- @.claude/memory/shared/global-commands.md §Python (pyx alias)

## Out of Scope

- 真接 ESP32 ws (留 H030 物理实测)
- send retry / queue / ack
- 多 device routing
- TTS 让机器人**说话**而非显示
- Hermes 自带 cron job 触发 send (留 Week 3 §3.5)
- 改 M2 shim
- 改 ADR

## Candidate Root Causes (pytest fail 时先查)

1. **fastapi missing in conda env** — `pyx -c 'import fastapi'` 验；
   缺则 PyPI 装；DNS 失败 → 用 openai-shim 已有的 env (它装过 fastapi)
2. **httpx ASGITransport 0.27+** — `httpx.AsyncClient(transport=
   httpx.ASGITransport(app=fake_app))`
3. **pytest-asyncio mode** — `asyncio_mode = "auto"` 在两个包 pyproject 内
   (M1 已有 / M3 H028 已加)
4. **PYTHONPATH 不含 Hermes site-packages** — H028 教训：
   `PYTHONPATH="src:$HOME/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages"
   pyx -m pytest -xvs tests/`
5. **call_show_text monkeypatch 范围** — 用 `monkeypatch.setattr(
   "xiaozhi_mcp_adapter.proxy_http.call_show_text", fake_impl)` 不是
   `setattr(show_text_proxy, ...)`，因为 import 时复制了引用
6. **truncate 算汉字 vs 字符** — len() 算 Unicode codepoint 即"字"；
   不要折腾 utf-8 byte count

## Suggested Steps

```bash
cd ~/code/robot_class/final_pro_xiaozhi_robot
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

# 1. M1 改
cd xiaozhi-mcp-adapter
# 写 show_text_proxy.py + proxy_http.py + test_show_text_proxy.py
# 改 pyproject.toml 加 fastapi 依赖

# 2. 跑 M1 测 (跳过装包用 existing env)
PYTHONPATH="src:$HOME/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages" \
  /home/kk/miniconda3/bin/python -m pytest -xvs tests/
# 期望: 原 H015 echo 测 + 本 handoff 3 new = 全 PASS

# 3. M3 改
cd ../hermes-xiaozhi-plugin
# 改 adapter.py::send 真接 sidecar URL
# 加 test_adapter_send_e2e_via_fake_sidecar

PYTHONPATH="src:$HOME/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages" \
  /home/kk/miniconda3/bin/python -m pytest -xvs tests/
# 期望: 3 H028 + 1 new = 4 PASS

# 4. git status
cd ..
git status --short

# 5. **不**做 cleanup (gitignore 已盖 __pycache__ + .pytest_cache)
```

## Error-handling discipline

- **Cosmetic** → 自己改
- **Substantive** (FastAPI / httpx / pytest 配置错) → blocked + stderr
- **PyPI 装不上** → blocked + stderr + 已试 PYTHONPATH inject
- **不要超 scope**：M1 3 测 + M3 1 测 + send hookup 就停；**不**顺手
  起真 sidecar / 真接 ws
- **不**`rm -rf` 任何东西 (H028 教训 #17)；缓存交给 planner main-loop

## For Auditor

不发 auditor。M3 三件套 (H028+H028.bis+H029) 全 done + Stage D demo
(Hermes 让机器人显示文字) 后 batch review。

## Open Questions for Planner

- M1 sidecar 是否要走 systemd 自启？(留 Week 4 polish)
- send 失败时是否 retry？当前 fire-and-forget (跟 M2 HermesBackend 一致)
  够 demo；production polish 时考虑
- ESP32 端 show_text("chat", text) 真显示的字数限制？文档说 ≤30 汉字，
  实测可能不同；H030 验

## Executor's Reading
### What I'll do
- Stop immediately under the handoff error discipline because a context-read command failed before implementation.

### Assumptions made
- [LOW] The previous executor checkpoint's reported stderr is the exact failure output to preserve in this handoff.
- [LOW] `xiaozhi-mcp-adapter/tests/test_echo_tool.py` was intended as a context probe for existing M1 tests, not as an acceptance-criteria artifact.

## What I Did
- Read the required executor startup files:
  - `.claude/agents/executor.md`
  - `CLAUDE.md`
  - `.claude/rules/handoff-protocol.md`
  - `docs/adr/0003-executor-runs-in-main-loop.md`
- Read `docs/handoffs/INDEX.md` and this handoff's current state.
- Did not modify source files and did not run tests.
- Per the handoff discipline, blocked after the earlier context-read command failed:

```text
sed: can't read xiaozhi-mcp-adapter/tests/test_echo_tool.py: No such file or directory
```

## Open Questions for Auditor
- None; this handoff is blocked before implementation.

## Executor's Reading (reopened 2026-06-20)
### What I'll do
- Implement only the H029 M1 show_text proxy/sidecar and M3 adapter send sidecar path, then run the scoped pytest commands.

### Assumptions made
- [LOW] The user's "重新打开029" authorizes resuming this handoff from blocked to claimed.
- [LOW] The missing `test_echo_tool.py` context probe can be replaced by reading the existing `tests/test_pipe_e2e.py` and M1 source files.

## What I Did (reopened 2026-06-20)
- Reopened the handoff by moving frontmatter `status` from `blocked` to `claimed`.
- Confirmed `git status --short` showed only this handoff modified before source edits.
- Read current M1 and M3 files:
  - `xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/echo_tool.py`
  - `xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/pipe.py`
  - `xiaozhi-mcp-adapter/tests/test_pipe_e2e.py`
  - `xiaozhi-mcp-adapter/pyproject.toml`
  - `hermes-xiaozhi-plugin/src/hermes_xiaozhi/adapter.py`
  - `hermes-xiaozhi-plugin/tests/test_adapter_send.py`
  - `hermes-xiaozhi-plugin/tests/test_register.py`
  - `hermes-xiaozhi-plugin/pyproject.toml`
- Did not modify source files and did not run tests.
- Blocked again because context-read commands failed while probing for directory INDEX files:

```text
sed: can't read docs/designs/INDEX.md: No such file or directory
```

```text
sed: can't read docs/contracts/INDEX.md: No such file or directory
```
