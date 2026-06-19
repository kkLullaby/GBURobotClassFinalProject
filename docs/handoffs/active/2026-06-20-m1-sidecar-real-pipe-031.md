---
id: 2026-06-20-m1-sidecar-real-pipe-031
from: planner
to: executor
parent: 2026-06-20-m3-end-to-end-demo-030
supersedes:
status: pending
created: 2026-06-20
artifacts:
  - xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/proxy_http.py (改：加 startup hook 接真 pipe)
  - xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/pipe.py (微改: 暴露 `connect()` api 若现有不够)
  - xiaozhi-mcp-adapter/tests/test_proxy_http_pipe.py (新, 1-2 case)
---

## Why now

H030 7/7 机器侧已通 (curl HMAC → listener → Hermes session → DeepSeek →
adapter.send → sidecar 都跑通)。**唯一缺**: M1 sidecar 启动时 `_PIPE = None`,
sidecar 收到 POST `/tools/show_text` 后 `call_show_text(pipe=None, ...)`
抛 `RuntimeError("xiaozhi MCP pipe is not configured")`。

H029v2 §Out of Scope 明写 "真接 ESP32 ws 留 H030 物理实测" — 现在该实测了。

本 handoff 让 sidecar 启动时真连 xiaozhi mcp_endpoint pipe, sidecar 就能
真发 jsonrpc 到 ESP32 屏幕。Codex sandbox 友好: 用 mock pipe + httpx
ASGITransport 验 startup hook 行为, 不真起 ws。

## Objective

让 `xiaozhi-mcp-adapter` 的 sidecar 启动时:

1. 读 env `MCP_ENDPOINT` (ws URL)
2. 起 ws connect coroutine → 完成 xiaozhi mcp endpoint hello/initialize
3. 把 pipe 实例塞进 `show_text_proxy._PIPE` (或 module 级 state)
4. shutdown 时 close 干净

POST `/tools/show_text` 路径不变 (H029v2 已 done), 只是 `_PIPE` 启动后不再 None。

## Constraints

- 只改 `xiaozhi-mcp-adapter/` (不改 M2/M3/M4/esp/docs)
- 不真起 ws server / 不真连 ESP32 (本 handoff 是 mock)
- 不引新依赖 (websockets 已在 M1 pyproject)
- Python ≥ 3.8
- **Sandbox-friendly**: mock ws via monkeypatch
- 错误纪律: blocked → 完整 stderr + 已试 2-3 修; 不 `rm -rf`
- **INDEX 不存在 = 正常**, 按 Context Pointers path 读
- **socket bind 失败 = sandbox 限制**, planner main-loop 跑真 env unblock (H028.ter + H029v2 同 pattern)

## Acceptance Criteria

- [ ] `xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/proxy_http.py` 改:
      - `@app.on_event("startup")` async 函数:
        - 读 `os.environ.get("MCP_ENDPOINT")`; 缺则 log warning + 跳过
          (允许 sidecar 单跑 mock test)
        - 调 `pipe = await pipe_module.connect(mcp_endpoint_url)`
        - `show_text_proxy._PIPE = pipe`
      - `@app.on_event("shutdown")` async:
        - 若 `_PIPE` 非 None: `await _PIPE.close()`
        - `show_text_proxy._PIPE = None`

- [ ] `xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/pipe.py`:
      - 若现有已有 `connect(url) -> Pipe` 接口 (返 a `Pipe` 实例含 `.stdin/.stdout/.close()`)
        → 不改
      - 若现有只暴露 main entry → 微改加 `async def connect(url) -> Pipe`
        wrapper（不破坏 main 入口）

- [ ] `xiaozhi-mcp-adapter/tests/test_proxy_http_pipe.py` 新 2 case:
      1. `test_startup_hook_skips_when_no_env`: 不 set `MCP_ENDPOINT`,
         monkeypatch `pipe_module.connect` 抛 (不该被调), 起 TestClient/lifespan,
         验 `show_text_proxy._PIPE is None`
      2. `test_startup_hook_assigns_pipe_when_env`: set `MCP_ENDPOINT=ws://fake`,
         monkeypatch `pipe_module.connect` 返 fake Pipe object,
         起 lifespan, 验 `show_text_proxy._PIPE is fake_pipe`;
         shutdown 验 `_PIPE is None`

- [ ] 原 H015 / H029v2 测全不 regress
      - M1 total: `pytest -xvs tests/` 6/6 PASS (原 4 + 本 2)

- [ ] **不**真起 ws connect / 不真连 ESP32
- [ ] **不**改 M2/M3/M4/esp/docs
- [ ] `git status --short` 输出贴 What I Did

## Context Pointers (按 path 直接读, 不要先读 INDEX)

- @docs/handoffs/active/2026-06-20-m3-end-to-end-demo-030.md (机器侧 7/7
  ✅ + sidecar 500 root cause 在最后段)
- @docs/handoffs/active/2026-06-20-m3-physical-esp32-loop-030bis.md (本 handoff done 后续接)
- @docs/handoffs/archive/2026-06-20-m3-m1-proxy-and-real-send-029v2.md
  (H029v2: sidecar Skeleton + adapter.send 真接)
- @docs/handoffs/archive/2026-06-19-mcp-endpoint-server-bringup-016.md
  (mcp_endpoint 8004 + token 拿法)
- @xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/pipe.py (现有 pipe 看是否
  已有 `connect()` 接口; 没就微改)
- @xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/show_text_proxy.py
  (`_PIPE` 全局; `call_show_text(pipe, ...)`)
- @xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/proxy_http.py
  (现有 sidecar, 加 startup/shutdown hook)
- @xiaozhi-mcp-adapter/tests/test_show_text_proxy.py (H029v2 测 pattern 参考)
- @xiaozhi-mcp-adapter/tests/test_pipe_e2e.py (M1 echo 测; **不**碰)
- @openai-shim/src/openai_shim/app.py (FastAPI 模式参考)
- @.claude/memory/shared/global-commands.md §Python (pyx)

## Out of Scope

- 真接 ws ESP32 (留 H030.bis user 物理)
- pipe reconnect / retry (留 production polish)
- 多 device support
- 改 M3 adapter (H029v2 try/except 已够)
- 改 ADR

## Candidate Root Causes (test fail 时)

1. **FastAPI lifespan vs on_event** — FastAPI 0.110+ on_event 仍可用但
   推荐 lifespan context manager. Stage A 用 `@app.on_event("startup")`
   兼容好; v2 改 lifespan 不在 scope
2. **TestClient lifespan trigger** — `httpx.AsyncClient(transport=
   httpx.ASGITransport(app=app))` 不触发 lifespan. 用 `from
   starlette.testclient import TestClient` (sync) 或 `from asgi_lifespan
   import LifespanManager` (async, 不在 conda env 可能要装)
3. **module 全局变量替换 patch 时机** — `from .show_text_proxy import _PIPE`
   会复制引用; 必须 `from . import show_text_proxy` 然后 `show_text_proxy._PIPE = ...`
4. **monkeypatch async** — `monkeypatch.setattr("xiaozhi_mcp_adapter.pipe.connect",
   AsyncMock(return_value=fake_pipe))`

## Suggested Steps

```bash
cd /home/kk/code/robot_class/final_pro_xiaozhi_robot/xiaozhi-mcp-adapter
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

# 1. 看 pipe.py 是否已有 connect() api
grep -n 'def connect\|async def main\|async def run' src/xiaozhi_mcp_adapter/pipe.py | head

# 2. 改 proxy_http.py 加 startup/shutdown hook (~15 LOC)

# 3. (如必要) 微改 pipe.py 加 connect wrapper (≤ 10 LOC)

# 4. 写 tests/test_proxy_http_pipe.py 2 case

# 5. 跑测
PYTHONPATH="src:$HOME/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages" \
  /home/kk/miniconda3/bin/python -m pytest -xvs tests/
# 期望: 6/6 PASS

# 6. git status
git status --short
```

## Error-handling discipline

- Cosmetic (typo / 缩进) → 自改
- Substantive (FastAPI lifespan / monkeypatch 不生效) → blocked + stderr
- INDEX 不存在 → **正常**, 按 path 读
- socket bind 失败 = sandbox 限制, blocked + 完整 stderr (planner unblock)
- 不超 scope: 2 hook + 1-2 测就停
- 不 `rm -rf`

## For Auditor

不发. M3 三件套 (H028 + H028.bis + H028.ter + H029v2) + 物理 (H030 +
H030.bis + H031) 全 done 后 batch review (留 H032).

## Open Questions

- 本机已实测 `_PIPE = None` 让 sidecar 抛 RuntimeError, adapter.send try/except
  接住; 本 handoff done 后 _PIPE 有真 pipe 但 ws connect 失败时行为? (留
  H030.bis user 物理验)
- pipe.close() 上游 78/mcp-calculator 是否支持优雅关? (sandbox 测 mock 就行)
