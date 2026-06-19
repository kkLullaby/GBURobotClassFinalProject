---
id: 2026-06-19-m3-hermes-plugin-spike-028
from: planner
to: executor
parent: 2026-06-19-m2-hermes-hmac-sign-025
supersedes:
status: pending
created: 2026-06-19
artifacts:
  - hermes-xiaozhi-plugin/pyproject.toml (新)
  - hermes-xiaozhi-plugin/src/hermes_xiaozhi/__init__.py (新)
  - hermes-xiaozhi-plugin/src/hermes_xiaozhi/adapter.py (新)
  - hermes-xiaozhi-plugin/src/hermes_xiaozhi/plugin.yaml (新)
  - hermes-xiaozhi-plugin/README.md (新)
  - hermes-xiaozhi-plugin/tests/test_register.py (新)
  - hermes-xiaozhi-plugin/tests/test_adapter_send.py (新)
---

## Why now

Week 0 已闭环。M2 transcript egress (H018-H022) + M4 ESP32 tools (H024)
+ M2 HMAC (H025) 全 done；剩 Hermes 端"第一具物理化身"——M3 plugin。

按 [ADR-0005](../adr/0005-openai-compat-transcript-egress.md) M3 工作量
**从 5-6 → 1-2 天**，因为不再需要任何 callback hook 机制；transcript
经 M2 webhook 已经流进 Hermes。

按 [m3-hermes-plugin-architecture.md](../designs/active/m3-hermes-plugin-architecture.md)
设计，H028 是 Stage A（sandbox 内）：写 plugin 骨架 + mock test PASS。
Stage B (真装 + Hermes 启动验) + Stage C (M1 proxy + 真 send) 走后续
H028.bis / H029。

跟 H018 同模式：**codex sandbox 写 Python + pytest 验**。Hermes 包已经
装在 `~/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages/`
sandbox 可达 → import `gateway.platforms.base` 应该不阻塞。

## Objective

按 [m3-hermes-plugin-architecture §5-§6](../designs/active/m3-hermes-plugin-architecture.md)
新建 `hermes-xiaozhi-plugin/` package：

1. `XiaozhiAdapter(BasePlatformAdapter)` 实现 4 个 abstract method:
   `connect / disconnect / send / get_chat_info`
2. `register(ctx)` 用 `ctx.register_platform(name="xiaozhi", ...)`
3. plugin.yaml (`kind: platform`)
4. 2 pytest case (register + send mock)
5. README 装法 + env vars

**不**真装到 `~/.hermes/plugins/`；**不**真跑 hermes gateway；**不**改
M1/M2/M4/ESP32 任何文件。

## Constraints

- 新建 `hermes-xiaozhi-plugin/` 顶层目录在仓库根 (跟 `openai-shim/`/
  `xiaozhi-mcp-adapter/` 同级)
- 不改 `openai-shim/` 任何文件 (M2 已 done)
- 不改 `xiaozhi-mcp-adapter/` 任何文件 (M1 H015 echo)
- 不改 `esp/xiaozhi-esp32/` (M4 H024 done, submodule pin bumped)
- 不真装 plugin 到 ~/.hermes/，不跑 `hermes gateway run` (留 H028.bis)
- 不动 docs (除本 handoff 自身追加段)
- Python ≥ 3.8；依赖只 httpx + pytest + pytest-asyncio (Hermes 自带)
- 测试用 mock，不真起 aiohttp server (复杂度高，留 H028.bis)
- **Sandbox-friendly**：codex 必能装 deps + 跑 pytest
- 错误纪律：Hermes ABC 变了 → blocked + 完整 stderr，不要乱猜签名

## Acceptance Criteria

- [ ] `hermes-xiaozhi-plugin/pyproject.toml`：
      ```toml
      [project]
      name = "hermes-xiaozhi-plugin"
      version = "0.1.0"
      requires-python = ">=3.8"
      dependencies = ["httpx>=0.27"]

      [project.optional-dependencies]
      test = ["pytest>=8", "pytest-asyncio>=0.23"]

      [build-system]
      requires = ["hatchling"]
      build-backend = "hatchling.build"
      ```

- [ ] `src/hermes_xiaozhi/plugin.yaml`：
      ```yaml
      name: xiaozhi-platform
      label: XiaoZhi
      kind: platform
      version: 0.1.0
      description: >
        XiaoZhi (ESP32-S3 OttoRobot) platform adapter for Hermes Agent.
        Receives transcripts from M2 openai-shim via signed webhook,
        sends responses back through M1 mcp-adapter -> ESP32 show_text.
      author: kkLullaby
      requires_env:
        - name: XIAOZHI_WEBHOOK_PORT
          description: "Port for the adapter's incoming webhook (default 8645)"
          prompt: "Webhook port"
          password: false
        - name: XIAOZHI_WEBHOOK_SECRET
          description: "HMAC secret shared with the openai-shim (X-Hub-Signature-256)"
          prompt: "Webhook secret"
          password: true
      optional_env:
        - name: XIAOZHI_DEVICE_ID
          description: "Default ESP32 device MAC (e.g. ac:a7:04:30:91:78)"
          prompt: "Default device id"
          password: false
        - name: XIAOZHI_MCP_ADAPTER_URL
          description: "M1 adapter endpoint for reverse send() (default disabled)"
          prompt: "M1 adapter URL"
          password: false
      ```

- [ ] `src/hermes_xiaozhi/__init__.py`：
      ```python
      from .adapter import register
      __all__ = ["register"]
      ```

- [ ] `src/hermes_xiaozhi/adapter.py` 满足：
      - import `from gateway.platforms.base import BasePlatformAdapter, MessageEvent, SendResult, MessageType`
      - import `from gateway.config import Platform, PlatformConfig`
      - 类 `XiaozhiAdapter(BasePlatformAdapter)`：
        - `__init__(self, config: PlatformConfig)`: `super().__init__(config, Platform("xiaozhi"))`
          + 读 env XIAOZHI_WEBHOOK_PORT / SECRET / DEVICE_ID / MCP_ADAPTER_URL
        - `async def connect(self) -> bool`: 桩 return True；TODO 注释指向 H028.bis
        - `async def disconnect(self) -> None`: 桩 pass
        - `async def send(self, chat_id, content, reply_to=None, metadata=None) -> SendResult`:
          - 当前打 log "TODO M1 proxy not wired"，return SendResult(success=True,
            message_id=f"stub-{chat_id}")
          - 如果设了 `XIAOZHI_MCP_ADAPTER_URL` env：用 httpx POST
            `{adapter_url}/tools/show_text` body `{"device_id": chat_id,
            "text": content, "kind": "chat"}` (即使 endpoint 不存在也只 log，
            不 raise)
        - `async def get_chat_info(self, chat_id) -> Dict[str, Any]`:
          return `{"name": f"XiaoZhi-{chat_id}", "type": "dm"}`
      - 函数 `register(ctx) -> None`：
        - `ctx.register_platform(name="xiaozhi", label="XiaoZhi", adapter_factory=lambda cfg: XiaozhiAdapter(cfg), check_fn=lambda: True, required_env=["XIAOZHI_WEBHOOK_PORT", "XIAOZHI_WEBHOOK_SECRET"], install_hint="装 httpx (Hermes 自带)", emoji="🤖", max_message_length=4096, platform_hint="You are speaking through a physical desktop robot with a 240x240 LCD screen. Reply concisely (≤30 Chinese chars per chunk).")`

- [ ] `tests/test_register.py` (1 case):
      ```python
      from unittest.mock import MagicMock
      from hermes_xiaozhi import register

      def test_register_calls_ctx_register_platform():
          ctx = MagicMock()
          register(ctx)
          ctx.register_platform.assert_called_once()
          kw = ctx.register_platform.call_args.kwargs
          assert kw["name"] == "xiaozhi"
          assert kw["label"] == "XiaoZhi"
          assert callable(kw["adapter_factory"])
          assert kw["check_fn"]() is True
          assert "XIAOZHI_WEBHOOK_PORT" in kw["required_env"]
          assert "XIAOZHI_WEBHOOK_SECRET" in kw["required_env"]
      ```

- [ ] `tests/test_adapter_send.py` (2 case)：
      1. `test_adapter_send_returns_success_without_mcp_url`：
         - 不 set XIAOZHI_MCP_ADAPTER_URL；构造 adapter；await send
         - 验：result.success is True；message_id startswith "stub-"
      2. `test_adapter_send_posts_to_mcp_url_when_set`：
         - 用 httpx MockTransport 拦 POST；set XIAOZHI_MCP_ADAPTER_URL
         - 验：MockTransport 收到 POST，body 含 device_id+text+kind="chat"

- [ ] `README.md` (≤80 行)：
      - 概述 (M3 plugin per ADR-0005)
      - 装法 (`ln -s` 到 ~/.hermes/plugins/xiaozhi)
      - env vars 表
      - 当前限制 (Stage A 只有桩 send)
      - 后续 Stage B/C TODO

- [ ] **不**真装 plugin 到 `~/.hermes/plugins/`
- [ ] **不**改 hermes-agent 本体 (`~/.local/share/uv/tools/...`)
- [ ] **不**改 openai-shim / xiaozhi-mcp-adapter / esp/
- [ ] **不**起 aiohttp / 不真听 webhook (留 H028.bis)
- [ ] `pyx -m pytest -xvs tests/` 3/3 PASS
- [ ] `git status --short` 输出贴 What I Did

## Context Pointers

- @docs/designs/active/m3-hermes-plugin-architecture.md (**主参考**)
- @docs/adr/0005-openai-compat-transcript-egress.md (主线 ADR)
- @docs/handoffs/archive/2026-06-19-real-hermes-transcript-handshake-020.md
  (webhook ingress 实测的 HMAC + session spawn 行为)
- @docs/handoffs/archive/2026-06-19-m2-hermes-hmac-sign-025.md (HMAC 实现)
- @docs/handoffs/archive/2026-06-19-m4-implement-show-emoji-and-text-024.md
  (M4 show_text MCP tool, Stage C 时调它)
- Hermes 自带 plugin 参考 (read-only):
  - `~/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages/plugins/platforms/ntfy/` (最简 593 LOC)
  - `~/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages/plugins/platforms/irc/`
- Hermes ABC + registry (read-only):
  - `~/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages/gateway/platforms/base.py` (BasePlatformAdapter, 4 abstract methods at lines 2208/2217/2222/4661)
  - `~/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages/gateway/platform_registry.py` (PlatformEntry schema)
  - `~/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages/gateway/config.py:100` (Platform enum + `_missing_` 接 plugin name)
- @.claude/memory/shared/global-commands.md §Python (pyx alias)
- @openai-shim/src/openai_shim/hermes_backend.py (HMAC sign pattern 参考)

## Out of Scope

- 不写 M1 `show_text_proxy` tool (留 H029)
- 不真起 aiohttp 监听 webhook (留 H028.bis)
- 不真装 plugin 到 ~/.hermes/plugins/ (留 H028.bis)
- 不真跑 `hermes gateway run` (留 H028.bis)
- 不写真 TTS 路径 (out-of-scope per design §7)
- 不写 retry / queue / ack
- 不实现多 robot 支持 (单 device_id)
- 不动 M2 shim env (env URL 切换在 H028.bis)
- 不写 ADR (本 spike 是设计已成型的实现，无新决策)

## Candidate Root Causes (test fail 时先查)

1. **Hermes import path 错** — `gateway.platforms.base` 必须能 import；
   如 `ModuleNotFoundError` → sys.path 没含 Hermes 的 site-packages →
   `PYTHONPATH=~/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages pyx -m pytest ...`
2. **`Platform("xiaozhi")` 抛** — `_missing_` 应该接受任意非空 string；
   若抛 → 看 `gateway/config.py:130-140` 的实际逻辑，可能要先调
   `Platform._missing_` 让它 cache
3. **`super().__init__(config, Platform(...))` 参数不对** — 看
   `BasePlatformAdapter.__init__` 的真实签名；可能不是 `(config, platform)`
   而是 `(config, platform_kind)` 或仅 `(config,)`
4. **`SendResult` import** — 在 `gateway.platforms.base` 里 export 名字
   是 `SendResult`；如果它要的是 kwarg 不对 → 看 dataclass 字段
5. **httpx MockTransport** — 0.27+ 用 `httpx.MockTransport(handler)`
   传给 `httpx.AsyncClient(transport=...)`
6. **pytest-asyncio mode** — pyproject 加 `[tool.pytest.ini_options]`
   `asyncio_mode = "auto"` 或测试函数用 `@pytest.mark.asyncio`

## Suggested Steps

```bash
cd ~/code/robot_class/final_pro_xiaozhi_robot
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

# 1. 包骨架
mkdir -p hermes-xiaozhi-plugin/src/hermes_xiaozhi hermes-xiaozhi-plugin/tests

# 2. 写 pyproject.toml + plugin.yaml + __init__.py + adapter.py + README

# 3. 装 (sandbox 内)
cd hermes-xiaozhi-plugin
UV_CACHE_DIR=/tmp/uv-cache uv pip install --system -e '.[test]'

# 4. 跑测 (注意 PYTHONPATH 让 import gateway.* 找到)
PYTHONPATH=~/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages \
  pyx -m pytest -xvs tests/

# 5. git status
cd ..
git status --short
```

## Error-handling discipline

- **Cosmetic** → 自己改
- **Substantive** (Hermes ABC 不认 / register 签名错) → blocked +
  完整 stderr + 已试 2-3 修法
- **不要超 scope**：4 method + 1 register + 3 测就停；**不**顺手起
  aiohttp / 写 send() 真实现
- **PyPI 装不上**：blocked + 完整 stderr，planner main-loop 接力
- **不**真装 plugin / **不**跑 hermes

## Recovery

| 症状 | 修 |
|---|---|
| `ModuleNotFoundError: gateway` | PYTHONPATH=~/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages |
| `Platform("xiaozhi")` ValueError | `gateway/config.py:130 _missing_` 接受任意 str；若抛说明 enum 严格，先 `Platform._missing_(cls, "xiaozhi")` 手 cache |
| `BasePlatformAdapter.__init__` signature mismatch | 看 base.py:103 super().__init__ 真签名 |
| `SendResult` dataclass 字段错 | 看 base.py 定义 (line 1700 之前) |
| pytest-asyncio not configured | pyproject 加 asyncio_mode="auto" |
| httpx MockTransport 不工作 | 升级 httpx>=0.27 或换 respx |

## For Auditor

不发 auditor。M3 三件套 (H028 + H028.bis + H029) 全 done 后 batch review。

## Open Questions for Planner

- Stage B 用 symlink 装 plugin 跟 cp 装哪个 Hermes 更稳？默认走 cp（
  symlink Hermes loader 可能 strict）
- Stage C 的 M1 proxy 用 stdio MCP 还是 HTTP MCP？stdio 上游已经 echo 验过
  最稳；但 stdio adapter ↔ Hermes plugin 跨进程通信怎么走？(可能要 unix
  socket 或起 sidecar HTTP)
- 我们做的 plugin 进上游 Hermes PR 时 license 怎么处理？(`hermes-xiaozhi-plugin`
  独立 LICENSE, MIT)
