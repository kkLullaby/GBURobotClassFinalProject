---
id: 2026-06-20-m3-m1-proxy-and-real-send-029v2
from: planner
to: executor
parent: 2026-06-20-m3-xiaozhi-adapter-listener-028ter
supersedes: 2026-06-19-m3-m1-proxy-and-real-send-029
status: done
created: 2026-06-20
artifacts:
  - xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/show_text_proxy.py (新)
  - xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/proxy_http.py (新, sidecar)
  - xiaozhi-mcp-adapter/tests/test_show_text_proxy.py (新)
  - xiaozhi-mcp-adapter/pyproject.toml (改：加 fastapi 依赖)
  - hermes-xiaozhi-plugin/src/hermes_xiaozhi/adapter.py (微改: send() try/except 加 degraded fallback)
  - hermes-xiaozhi-plugin/tests/test_adapter_send.py (改: 加 1 e2e mock case)
---

## Why now

H029 v1 codex 两轮全 blocked，**都不是代码原因**，都是 cosmetic：

- 第 1 轮：cosmetic-error "no such file `tests/test_echo_tool.py`"（其实文件叫
  `test_pipe_e2e.py`，codex 自己加猜的名字）
- 第 2 轮：cosmetic-error "no such file `docs/designs/INDEX.md`" + 同步报
  `docs/contracts/INDEX.md` 不存在 → 这就是 [Week 0 retro #14
  bitter lesson](../../retros/week0.md) 的重演

v1 状态 `blocked`，本 v2 显式 supersede，**Constraints 内显写 "INDEX
不存在直接按 path 写即可"** 让 codex 不再卡。其余 AC 与 v1 完全一样
（M1 proxy + sidecar + adapter.send 真接）。

H028.ter listener 已 done (4/4 PASS)，adapter.send() stub 留的 `XIAOZHI_MCP_ADAPTER_URL`
env 桩可直接生产化——本 handoff 让它真生效。

跟 H018/H019/H021/H025 同模式：codex sandbox 自闭环；纯 Python + httpx
mock；无新依赖（fastapi conda env 已装）。

## Objective

End-to-end mock：在 sandbox 里跑 `pytest -xvs tests/` 验证：

1. M1 `show_text_proxy` 模块正确组装 ESP32 MCP JSON-RPC + 截断 30 汉字
2. M1 sidecar HTTP `POST /tools/show_text` 转发 → fake-impl 收到
3. adapter.send() 在 `XIAOZHI_MCP_ADAPTER_URL` 设了时真 POST sidecar
4. sidecar 不 reachable → adapter.send 返 degraded SendResult（不抛）

**不**真起 ESP32；**不**真起 sidecar long-running；**不**真起 Hermes —
全 fake-ASGI mock。

## Constraints

- 改 `xiaozhi-mcp-adapter/` (M1) 和 `hermes-xiaozhi-plugin/` (M3) 两个包
- 不改 `openai-shim/` (M2)
- 不改 `esp/xiaozhi-esp32/` (M4)
- 不动 `~/.hermes/plugins/` (real install 是 H028.bis 已 done 的事)
- 不真起 long-running sidecar；test 用 in-memory ASGI
- Python ≥ 3.8；新增依赖 `fastapi>=0.110` 加进 M1 pyproject（conda env 已有）
- **Sandbox-friendly**：H028 教训 — 若 PyPI DNS 失败用
  `PYTHONPATH=src:$HOME/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages`
  跑现成 env (openai-shim 装时 fastapi+httpx+pytest-asyncio 全在 conda)
- 错误纪律：blocked → 完整 stderr + 已试 2-3 修；**不要**尝试 `rm -rf`
  (H028 教训 #17)；pytest 缓存交给 planner main-loop 清

### ★ INDEX 处理纪律（v1 卡这条 2 次, 本 v2 显写）

- `docs/designs/INDEX.md` / `docs/contracts/INDEX.md` 不存在 = 正常
- CLAUDE.md §三角色共同纪律 #2 "读目录前先读 INDEX.md" 的实操：
  **INDEX 不存在 → 直接按 handoff Context Pointers 列出的具体 path 读**，
  不要尝试读 INDEX → 不要因为读不到就 blocked
- 本 handoff Context Pointers 已逐条列了所有要读的具体 .py / .md 路径

### ★ 测试文件命名纪律（v1 第 1 轮卡这条）

- 现有 M1 测试文件名是 **`xiaozhi-mcp-adapter/tests/test_pipe_e2e.py`**
  （不叫 `test_echo_tool.py`）
- 你新建的测试文件叫 **`xiaozhi-mcp-adapter/tests/test_show_text_proxy.py`**
  （AC 明写）
- 不要尝试读 v1 想象的旧文件名

## Acceptance Criteria

### M1 side

- [ ] `xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/show_text_proxy.py` 新：
      - 函数 `build_show_text_jsonrpc(device_id: str, text: str, kind: str
        = "notification") -> dict`：返 `{"jsonrpc":"2.0","method":"tools/call",
        "params":{"name":"self.otto.show_text","arguments":{"text":text,
        "kind":kind}},"id":<uuid>}` (uuid.uuid4().hex)
      - 函数 `async def call_show_text(pipe, device_id, text, kind) -> dict`：
        把 jsonrpc dump 进 pipe.stdin + 读 pipe.stdout 一行 + JSON parse return
      - 容错：`len(text) > 30` → `text = text[:27] + "..."`（按 codepoint 算）；
        kind 不在 {"notification", "chat"} → 改 "notification"

- [ ] `xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/proxy_http.py` 新：
      - `from fastapi import FastAPI; from pydantic import BaseModel`
      - `app = FastAPI(title="xiaozhi-mcp-adapter sidecar")`
      - `class ShowTextRequest(BaseModel)`: device_id: str, text: str, kind: str = "notification"
      - `@app.post("/tools/show_text")`：调 `call_show_text(...)` →
        return `{"ok": True, "echo": <result>}`
      - 桩 pipe 用 module 级单例 `_PIPE` (test 用 monkeypatch 替换)；
        生产时接真 xiaozhi mcp_endpoint pipe 留 H030

- [ ] `xiaozhi-mcp-adapter/tests/test_show_text_proxy.py` 新 3 case：
      1. `test_build_show_text_jsonrpc_basic`: 验 jsonrpc 字段齐 + arguments
         含 text+kind+name="self.otto.show_text"
      2. `test_build_show_text_jsonrpc_truncates_long_text`: 50 汉字 text →
         result["params"]["arguments"]["text"] 长度 ≤ 30 且结尾是 "..."
      3. `test_proxy_http_post_show_text`：httpx AsyncClient + ASGITransport
         打 fake app，monkeypatch `proxy_http.call_show_text` (注意是
         `proxy_http.call_show_text`，不是 `show_text_proxy.call_show_text`,
         import 时复制了引用) 返 coroutine `{"ok":True}`；验 POST
         `/tools/show_text` 200 + body `{"ok":true,"echo":{"ok":true}}`

- [ ] `xiaozhi-mcp-adapter/pyproject.toml`：dependencies 加 `fastapi>=0.110`

### M3 side

- [ ] `hermes-xiaozhi-plugin/src/hermes_xiaozhi/adapter.py::send()` 改：
      - 当前 H028 桩已有 "if mcp_adapter_url: httpx.post(...)" 分支，本
        handoff 让它**真生效** + 加 try/except
      - `try: ... except (httpx.HTTPError, asyncio.TimeoutError) as e:
         LOG.warning("xiaozhi M1 sidecar unreachable: %s", e);
         return SendResult(success=True, message_id=f"degraded-{chat_id}")`
      - 成功 case：`return SendResult(success=True, message_id=f"sent-{chat_id}")`
      - 5s timeout 别留默认无穷

- [ ] `hermes-xiaozhi-plugin/tests/test_adapter_send.py` 改 → 加 1 case:
      4. `test_adapter_send_e2e_via_fake_sidecar`：
         - 用 `httpx.MockTransport` 拦 POST `{url}/tools/show_text`
         - set XIAOZHI_MCP_ADAPTER_URL="http://fake-sidecar:8650"
         - 调 `await adapter.send("ac:a7:04:30:91:78", "测试一下")`
         - 验 MockTransport 收到的 request.read() body JSON 含
           `device_id="ac:a7:04:30:91:78"` + `text="测试一下"` + `kind="chat"`
         - 验 result.success is True + message_id startswith "sent-" or "stub-"

### Tests + integration

- [ ] M1 pytest 3 new case PASS（不 regress 原 H015 pipe_e2e 测）
- [ ] M3 pytest 5 case PASS = 1 register + 3 send (含 2 旧 + 1 new) + 1 H028.ter listener
- [ ] **不**真起 sidecar long-running
- [ ] **不**改 ~/.hermes/ / 不真跑 hermes / 不改 ESP32
- [ ] `git status --short` 输出贴 What I Did
- [ ] 不留 `__pycache__` / `.pytest_cache` 进 git (gitignore 已盖)

## Context Pointers (按 path 直接读，不要先读 INDEX)

- @docs/handoffs/archive/2026-06-19-m3-hermes-plugin-spike-028.md (H028 Stage A done)
- @docs/handoffs/active/2026-06-20-m3-xiaozhi-adapter-listener-028ter.md
  (H028.ter listener done; send() 桩仍在)
- @docs/handoffs/active/2026-06-20-m3-m1-proxy-and-real-send-029.md
  (v1, 本 v2 supersede；可读但不要按 v1 走)
- @docs/designs/active/m3-hermes-plugin-architecture.md §3 + §5
- @docs/contracts/api/v1/esp32-mcp-tools.md (show_text schema 出处)
- @hermes-xiaozhi-plugin/src/hermes_xiaozhi/adapter.py
  (现状: H028.ter listener + H028 send 桩)
- @hermes-xiaozhi-plugin/tests/test_adapter_send.py (改这里加 case 4)
- @xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/echo_tool.py (M1 echo
  pattern 参考；本 handoff 模仿其结构写 show_text_proxy)
- @xiaozhi-mcp-adapter/src/xiaozhi_mcp_adapter/pipe.py (M1 pipe 接 xiaozhi
  mcp_endpoint 的 ws 客户端；**不**碰它)
- @xiaozhi-mcp-adapter/tests/test_pipe_e2e.py (现有 M1 测；**不**碰它，
  只跑确保不 regress)
- @xiaozhi-mcp-adapter/pyproject.toml (改这里加 fastapi 依赖)
- @openai-shim/src/openai_shim/app.py (FastAPI pattern 参考)
- @.claude/memory/shared/global-commands.md §Python

## Out of Scope

- 真接 ESP32 ws (留 H030 物理实测)
- send retry / queue / ack 之外的复杂度
- 多 device routing
- TTS 让机器人**说话**而非显示
- cron job 触发 send (Week 3 §3.5)
- 改 M2 shim
- 改 ADR / 任何 docs (除本 handoff 自身追加段)

## Candidate Root Causes (pytest fail 时先查)

1. **fastapi missing** — `pyx -c 'import fastapi'`；conda env 已有 (openai-shim
   装时拉的)；缺则 PyPI 装；DNS 失败 → PYTHONPATH 注入
2. **httpx ASGITransport 0.27+** — `httpx.AsyncClient(transport=
   httpx.ASGITransport(app=fake_app))`
3. **pytest-asyncio mode** — M1 pyproject `asyncio_mode = "auto"` (已有)；
   M3 同 (H028 已加)
4. **call_show_text monkeypatch 范围** — 用 `monkeypatch.setattr(
   "xiaozhi_mcp_adapter.proxy_http.call_show_text", fake_impl)` 而不是
   `setattr(show_text_proxy, ...)`，因为 import 时复制了引用
5. **truncate 算汉字 vs 字符** — Python `len("你好")==2`，按 codepoint 算
   就是"字"；不要折腾 utf-8 byte count
6. **MockTransport request.read() vs request.content** — httpx 0.27+ 用
   `request.content` 是 bytes；如要 json 解 `json.loads(request.content)`

## Suggested Steps

```bash
cd ~/code/robot_class/final_pro_xiaozhi_robot
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

# 1. M1 改
#    - 写 src/xiaozhi_mcp_adapter/show_text_proxy.py
#    - 写 src/xiaozhi_mcp_adapter/proxy_http.py
#    - 改 pyproject.toml 加 fastapi
#    - 写 tests/test_show_text_proxy.py

# 2. 跑 M1 测（跳过装包用 existing env）
cd xiaozhi-mcp-adapter
PYTHONPATH="src:$HOME/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages" \
  /home/kk/miniconda3/bin/python -m pytest -xvs tests/
# 期望: 原 H015 pipe_e2e 测 + 本 handoff 3 new = 全 PASS

# 3. M3 改
cd ../hermes-xiaozhi-plugin
#    - adapter.py::send() 真接 + try/except
#    - tests/test_adapter_send.py 加 case 4

PYTHONPATH="src:$HOME/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages" \
  /home/kk/miniconda3/bin/python -m pytest -xvs tests/
# 期望: 1 register + 3 send (2 旧 + 1 new) + 1 listener = 5 PASS

# 4. git status
cd ..
git status --short

# 5. **不**做 cleanup (gitignore 已盖 __pycache__ + .pytest_cache)
#    若 codex sandbox 留 cache, planner main-loop 清
```

## Error-handling discipline

- **Cosmetic** (typo / 缩进 / import name) → 自己改
- **Substantive** (FastAPI / httpx / pytest 配置错) → blocked + stderr
- **PyPI 装不上** → 先 PYTHONPATH inject 跑 existing env
- **INDEX 不存在** → **正常**，按 Context Pointers 具体 path 读；**不要** blocked
- **猜不到的文件名** → 看 Context Pointers 里**写明的具体路径**；不在
  里面的文件不要主动找
- **不要超 scope**：M1 3 测 + M3 1 测 + send hookup 就停
- **不**`rm -rf` 任何东西 (H028 教训 #17)

## For Auditor

不发 auditor。M3 三件套 (H028 + H028.bis + H028.ter + H029v2) 全 done +
H030 物理 demo 后 batch review。

## Open Questions for Planner

- M1 sidecar 是否要走 systemd 自启？(留 Week 4 polish)
- send 失败时是否 retry？当前 fire-and-forget (跟 M2 HermesBackend 一致)
  够 demo；production polish 时考虑
- ESP32 端 show_text("chat", text) 真显示的字数限制？文档说 ≤30 汉字，
  实测可能不同；H030 验

## Executor's Reading
### What I'll do
- Implement the scoped M1 show_text proxy/sidecar and M3 adapter.send sidecar path, then run the M1 and M3 pytest suites specified by this handoff.

### Assumptions made
- [LOW] The parent/superseded context pointers for H028.ter and H029 v1 have moved from `active/` to `archive/`; using the INDEX locations preserves the intended history without changing implementation scope.
- [LOW] `proxy_http._PIPE` may remain a module-level placeholder in this handoff because production pipe wiring is explicitly left to H030 and tests monkeypatch `proxy_http.call_show_text`.
- [LOW] `build_show_text_jsonrpc(device_id, ...)` keeps the `device_id` parameter for the handoff API even though the current ESP32 `self.otto.show_text` contract has no `device_id` argument.

## What I Did
- Modified `xiaozhi-mcp-adapter/`:
  - added `src/xiaozhi_mcp_adapter/show_text_proxy.py`;
  - added `src/xiaozhi_mcp_adapter/proxy_http.py`;
  - added `tests/test_show_text_proxy.py`;
  - added `fastapi>=0.110` to `pyproject.toml`.
- Modified `hermes-xiaozhi-plugin/`:
  - updated `src/hermes_xiaozhi/adapter.py::send()` to return `sent-*` on sidecar success and `degraded-*` on `httpx.HTTPError` / `asyncio.TimeoutError`;
  - updated `tests/test_adapter_send.py` with success, degraded, and fake-sidecar send coverage.
- Did not modify M2, M4, `~/.hermes/`, or any Hermes install state.
- Ran the M1 scoped test command and blocked on failure before reaching M3 tests:

```bash
cd xiaozhi-mcp-adapter
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
PYTHONPATH="src:$HOME/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages" /home/kk/miniconda3/bin/python -m pytest -xvs tests/
```

Full output:

```text
============================= test session starts ==============================
platform linux -- Python 3.13.9, pytest-9.1.0, pluggy-1.5.0 -- /home/kk/miniconda3/bin/python
cachedir: .pytest_cache
rootdir: /home/kk/code/robot_class/final_pro_xiaozhi_robot/xiaozhi-mcp-adapter
configfile: pyproject.toml
plugins: anyio-4.14.0, asyncio-1.4.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 4 items

tests/test_pipe_e2e.py::test_pipe_echo_roundtrip FAILED

=================================== FAILURES ===================================
___________________________ test_pipe_echo_roundtrip ___________________________

    @pytest.mark.asyncio
    async def test_pipe_echo_roundtrip():
        done = asyncio.Event()
        errors = []
    
        async def handler(websocket, *_args):
            try:
                await _mock_mcp_endpoint(websocket)
            except Exception as exc:  # pragma: no cover - re-raised below
                errors.append(exc)
            finally:
                done.set()
    
>       async with websockets.serve(handler, "127.0.0.1", 0) as server:
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_pipe_e2e.py:90: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
/home/kk/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages/websockets/asyncio/server.py:829: in __aenter__
    return await self
           ^^^^^^^^^^
/home/kk/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages/websockets/asyncio/server.py:847: in __await_impl__
    server = await self.create_server
             ^^^^^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <_UnixSelectorEventLoop running=False closed=False debug=False>
protocol_factory = <function serve.__init__.<locals>.factory at 0x7562209a36a0>
host = '127.0.0.1', port = 0, family = <AddressFamily.AF_UNSPEC: 0>
flags = <AddressInfo.AI_PASSIVE: 1>, sock = None, backlog = 100, ssl = None
reuse_address = True, reuse_port = None, keep_alive = None
ssl_handshake_timeout = None, ssl_shutdown_timeout = None, start_serving = True

    async def create_server(
            self, protocol_factory, host=None, port=None,
            *,
            family=socket.AF_UNSPEC,
            flags=socket.AI_PASSIVE,
            sock=None,
            backlog=100,
            ssl=None,
            reuse_address=None,
            reuse_port=None,
            keep_alive=None,
            ssl_handshake_timeout=None,
            ssl_shutdown_timeout=None,
            start_serving=True):
        """Create a TCP server.
    
        The host parameter can be a string, in that case the TCP server is
        bound to host and port.
    
        The host parameter can also be a sequence of strings and in that case
        the TCP server is bound to all hosts of the sequence. If a host
        appears multiple times (possibly indirectly e.g. when hostnames
        resolve to the same IP address), the server is only bound once to
        that host.
    
        Return a Server object which can be used to stop the service.
    
        This method is a coroutine.
        """
        if isinstance(ssl, bool):
            raise TypeError('ssl argument must be an SSLContext or None')
    
        if ssl_handshake_timeout is not None and ssl is None:
            raise ValueError(
                'ssl_handshake_timeout is only meaningful with ssl')
    
        if ssl_shutdown_timeout is not None and ssl is None:
            raise ValueError(
                'ssl_shutdown_timeout is only meaningful with ssl')
    
        if sock is not None:
            _check_ssl_socket(sock)
    
        if host is not None or port is not None:
            if sock is not None:
                raise ValueError(
                    'host/port and sock can not be specified at the same time')
    
            if reuse_address is None:
                reuse_address = os.name == "posix" and sys.platform != "cygwin"
            sockets = []
            if host == '':
                hosts = [None]
            elif (isinstance(host, str) or
                  not isinstance(host, collections.abc.Iterable)):
                hosts = [host]
            else:
                hosts = host
    
            fs = [self._create_server_getaddrinfo(host, port, family=family,
                                                  flags=flags)
                  for host in hosts]
            infos = await tasks.gather(*fs)
            infos = set(itertools.chain.from_iterable(infos))
    
            completed = False
            try:
                for res in infos:
                    af, socktype, proto, canonname, sa = res
                    try:
                        sock = socket.socket(af, socktype, proto)
                    except socket.error:
                        # Assume it's a bad family/type/protocol combination.
                        if self._debug:
                            logger.warning('create_server() failed to create '
                                           'socket.socket(%r, %r, %r)',
                                           af, socktype, proto, exc_info=True)
                        continue
                    sockets.append(sock)
                    if reuse_address:
                        sock.setsockopt(
                            socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
                    # Since Linux 6.12.9, SO_REUSEPORT is not allowed
                    # on other address families than AF_INET/AF_INET6.
                    if reuse_port and af in (socket.AF_INET, socket.AF_INET6):
                        _set_reuseport(sock)
                    if keep_alive:
                        sock.setsockopt(
                            socket.SOL_SOCKET, socket.SO_KEEPALIVE, True)
                    # Disable IPv4/IPv6 dual stack support (enabled by
                    # default on Linux) which makes a single socket
                    # listen on both address families.
                    if (_HAS_IPv6 and
                            af == socket.AF_INET6 and
                            hasattr(socket, 'IPPROTO_IPV6')):
                        sock.setsockopt(socket.IPPROTO_IPV6,
                                        socket.IPV6_V6ONLY,
                                        True)
                    try:
                        sock.bind(sa)
                    except OSError as err:
                        msg = ('error while attempting '
                               'to bind on address %r: %s'
                               % (sa, str(err).lower()))
                        if err.errno == errno.EADDRNOTAVAIL:
                            # Assume the family is not enabled (bpo-30945)
                            sockets.pop()
                            sock.close()
                            if self._debug:
                                logger.warning(msg)
                            continue
                        raise OSError(err.errno, msg) from None
    
                if not sockets:
>                   raise OSError('could not bind on any address out of %r'
                                  % ([info[4] for info in infos],))
E                                 OSError: could not bind on any address out of [('127.0.0.1', 0)]

/home/kk/miniconda3/lib/python3.13/asyncio/base_events.py:1633: OSError
=========================== short test summary info ============================
FAILED tests/test_pipe_e2e.py::test_pipe_echo_roundtrip - OSError: could not ...
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
============================== 1 failed in 0.97s ===============================
```

## Open Questions for Auditor
- None; this handoff is blocked by the sandbox bind failure before M3 tests could be run.
