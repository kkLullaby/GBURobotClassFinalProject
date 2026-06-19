---
id: 2026-06-19-m2-hermes-hmac-sign-025
from: planner
to: executor
parent: 2026-06-19-real-hermes-transcript-handshake-020
supersedes:
status: done
created: 2026-06-19
artifacts:
  - openai-shim/src/openai_shim/hermes_backend.py (改：加 HMAC 签名)
  - openai-shim/src/openai_shim/app.py (改：加 HERMES_WEBHOOK_SECRET env)
  - openai-shim/tests/test_hermes_fork.py (改：加 2 个 HMAC case)
  - openai-shim/README.md (改：加 HMAC 段)
---

## Why now

[H020](archive/2026-06-19-real-hermes-transcript-handshake-020.md) 实测发现：
- Hermes webhook **强制 HMAC** (subscribe 时 `--secret` 不可空)
- Hermes 用 **GitHub 风格** header：`X-Hub-Signature-256: sha256=<hex>`
- shim 当前不签 → Hermes 401 拒，**fork transcript 永远不进 Hermes session**

H019 设计已 fire-and-forget 容错 (Hermes down 不阻塞 SSE)，但 401 太常见
（每个 demo 都 401）→ Hermes session 永远空 → ADR-0005 主线**实际没演成**。

补 HMAC 是 ADR-0005 真正 complete 的最后一步。~5 行代码 + 2 测。

跟 H015/H018/H019/H021 同模式：sandbox-friendly Python spike。

## Objective

在 `openai-shim/hermes_backend.py::_post_transcript()` 里，**POST body 拼好
后**：
1. 用 `hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()` 算签名
2. 加 header `X-Hub-Signature-256: sha256=<hex>`
3. Hermes 端验证通过 → 202 Accepted

env 新增：`HERMES_WEBHOOK_SECRET=<43-char from hermes webhook subscribe>`
（无此 env 时**仍**发，不签——保持向后兼容，让 H020 那种"webhook 不强制
HMAC"的 mock 测继续 PASS）

## Constraints

- 不改 `echo_backend.py` / `deepseek_backend.py` / `sse.py` / `app.py` 的
  endpoint handler 行为
- **不**改 `xiaozhi-mcp-adapter/` / `esp/` / `docs/contracts/` / `docs/adr/` /
  `docs/handoffs/` 任何既有文件（除本 handoff 自身追加段）
- 真 webhook secret **不**进 git
- HMAC 算法固定 sha256（Hermes 那边只接 sha256）
- 错误纪律：算签名失败 (secret empty + signing required?) → log warning +
  fork 该 try 但 Hermes 仍会 401，**不**raise（保持 fire-and-forget）
- 依赖只允许：`hmac` + `hashlib` (stdlib)，**不**加 third-party crypto
- Python ≥ 3.8 (用 hashlib.sha256)
- **Sandbox-friendly**：fake-hermes ASGI mock 可在 sandbox 内全跑

## Acceptance Criteria

- [ ] `openai-shim/src/openai_shim/hermes_backend.py` 改：
      - `__init__` 加 `webhook_secret: Optional[str] = None`
      - `_post_transcript()` 内：
        - JSON dump body 后转 bytes
        - 如 `webhook_secret` 非空：
          ```python
          sig = hmac.new(self.webhook_secret.encode(), body_bytes,
                         hashlib.sha256).hexdigest()
          headers = {"X-Hub-Signature-256": f"sha256={sig}"}
          ```
        - 否则 `headers = {}` (向后兼容)
        - `httpx.post(url, content=body_bytes, headers=headers)` (**用 content+
          headers, 不要 json=** —— 因为 httpx 的 json= 会重 serialize body
          → 签名 mismatch)
- [ ] `openai-shim/src/openai_shim/app.py` 改 `_build_backend()`:
      - 读 env `HERMES_WEBHOOK_SECRET`（可空）
      - `HermesBackend(inner, transcript_url, webhook_secret=secret)`
- [ ] `openai-shim/tests/test_hermes_fork.py` 加 2 测：
      1. `test_hmac_signature_added_when_secret_set`：fake-hermes 验签 endpoint
         (用同 secret 算 expected sig, 跟收到的 header 比对)；
         set `HERMES_WEBHOOK_SECRET="testsecret123"`；触发；断言收到的 POST
         header 含 `X-Hub-Signature-256: sha256=<correct hex>` + 验签通过
      2. `test_no_hmac_when_secret_unset`：不 set secret env；fake-hermes
         endpoint 检查 header **不**含 `X-Hub-Signature-256`；fork 仍发出 +
         fake-hermes 200 (向后兼容)
- [ ] 原 H018/H019/H021 测 (9 个) 仍 PASS
- [ ] `pytest -xvs tests/` 通过；新总数 11 个 PASS
- [ ] `README.md` 加 1 段 "H025 Webhook HMAC" (≤15 行):
      - env 变量名 + Hermes subscribe 拿 secret 的方式
      - 兼容性：secret 不设时不签 (mock 测仍 PASS)
      - **不**贴真 secret
- [ ] `git status` 输出贴 What I Did
- [ ] **不**改 `~/.hermes/` / **不**真跑 hermes CLI
- [ ] **不**实现 secret rotation / HMAC algorithm 选择 (固定 sha256)

## Context Pointers

- @docs/handoffs/archive/2026-06-19-real-hermes-transcript-handshake-020.md
  (**先读 §Stage D.bis** — Hermes header 名 `X-Hub-Signature-256` 来源)
- @openai-shim/src/openai_shim/hermes_backend.py (基线 H019 实现)
- @openai-shim/src/openai_shim/app.py (`_build_backend()` 改这里)
- @openai-shim/tests/test_hermes_fork.py (3 个现有测；本 handoff 加 2 个)
- @docs/adr/0005-openai-compat-transcript-egress.md (主线)
- HMAC 计算示例（Hermes 那侧 H020 实测 shell 命令）:
  ```bash
  SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -hex | awk '{print $2}')
  curl -X POST .../webhooks/xiaozhi-transcript \
       -H "X-Hub-Signature-256: sha256=$SIG" -d "$PAYLOAD"
  ```
- Python stdlib hmac docs: `hmac.new(key, msg, digestmod)`
- @.claude/memory/shared/global-commands.md (pyx 等)

## Out of Scope

- 不实现 secret rotation
- 不实现 timestamp 防 replay (Hermes 当前不需要)
- 不实现多 secret / per-route secret
- 不改 hermes CLI / config
- 不动 ESP32 / docker / mcp-endpoint
- 不实现 HMAC algo 选择 (固定 sha256)

## Candidate Root Causes（pytest fail 时先查）

1. **httpx.post(json=payload) 跟 (content=body_bytes) 行为不同** —
   httpx json= 会用它自己的 json.dumps，可能跟你算 sig 的 dumps 字节序不同
   (空格 / Unicode escape 不同) → mismatch；**必须先序列化成 bytes 一次,
   再两端用同一个 bytes**
2. **JSON 序列化 deterministic 不一致** — 用 `json.dumps(payload,
   separators=(',', ':'), ensure_ascii=False)` 保证两端一致
3. **bytes encoding** — secret + body 都用 `.encode()` (utf-8)，不要混 ascii
4. **fake-hermes 验签 endpoint** — 测试里要复刻同样的算法对收到的 body 重算
   sig 跟 header 比对；可以用 helper function 共享
5. **hmac.compare_digest vs == 比对** — secure compare 用 `hmac.compare_digest`
   (本 handoff 测可不强求, 但 production 标准化)

## Suggested Steps

```bash
cd ~/code/robot_class/final_pro_xiaozhi_robot/openai-shim
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

# 1. 改 hermes_backend.py:
#    - import hmac, hashlib
#    - __init__ 加 webhook_secret 参数
#    - _post_transcript 内拼 sig + header

# 2. 改 app.py _build_backend:
#    - 读 HERMES_WEBHOOK_SECRET env
#    - 传给 HermesBackend

# 3. 改 tests/test_hermes_fork.py:
#    - 加 2 新测 (with secret + without secret)
#    - 用 hmac.new 复算验签

# 4. 跑测
pyx -m pytest -xvs tests/
# 期望: H018 2 + H019 3 + H021 4 + H025 2 = 11 PASS

# 5. 改 README.md 加 §H025 Webhook HMAC

# 6. git status
git status --short
```

## Error-handling discipline

- **Cosmetic** → 自己改
- **Substantive** (httpx json= vs content= 字节序差 / 算签名跟 hermes 不一
  致) → status: blocked + 完整 stderr + bytes hexdump 对比已贴
- **不要超 scope**：HMAC 签 + 2 测就停，**不**顺手加 retry / rate limit /
  timestamp anti-replay
- **PyPI 装不上 (sandbox)**：H018 装齐, 本 handoff 无新依赖, 不会卡
- **不要真跑 hermes** (handoff 是 mock 测)

## Recovery

| 症状 | 修 |
|---|---|
| `httpx.post(json=...)` 后 hermes 仍 401 | 改用 `httpx.post(content=body_bytes, headers=...)` 配 `body_bytes = json.dumps(payload, separators=(',',':'), ensure_ascii=False).encode()` |
| fake-hermes 验签函数算出不一样的 sig | 两边用同一个 json.dumps 调用；或测试里把 body bytes 显式传出 |
| H019 原测炸 | webhook_secret default None 保持向后兼容；不设 secret 就不加 header |
| `test_hmac_signature_added` 收不到 header | fake-hermes 端 ASGI app 验签前先 print headers debug |

## For Auditor

不发 auditor。M2 集成 (H018+H019+H020+H021+H025) batch review 留 demo 答辩前。

## Open Questions for Planner

- 真 Hermes secret 怎么注入 demo？env file `~/.hermes/.env` 已经有；
  本 handoff 让用户启 shim 时 `HERMES_WEBHOOK_SECRET=$(hermes webhook list 抽)`
  即可；写一段 helper script
- 是否要把 secret 加密存到 ~/.openai-shim/state 之类避免每次 env 注入？
  v2 polish 再说
- demo 答辩用 deliver-only 模式（webhook 直接走 telegram channel,
  0 LLM cost + 视觉好）？— 可作为 H026 polish item

## Executor's Reading
### What I'll do
- 在 `openai-shim` 的 Hermes transcript fork 路径里加入可选 `HERMES_WEBHOOK_SECRET` HMAC 签名，保持无 secret 时不签的兼容行为，并用 fake-Hermes ASGI 测试覆盖签名存在和不存在两条路径。

### Assumptions made
- [LOW] 当前 `openai-shim/` 已包含 H019/H021 的实现，H025 在这些文件上增量修改，不回滚既有未提交变更。
- [LOW] H025 明确“不发 auditor”，因此完成后只在当前 handoff 追加 What I Did，不新建 auditor handoff。
- [LOW] README 在已有 H019/H021 段后追加 H025 HMAC 小节即可；不改 Hermes CLI 或真 secret 配置。
- [LOW] 测试中 fake-Hermes 会直接校验收到的 raw body bytes 和 header；生产代码和测试都使用同一套 HMAC 算法，但不共享实现函数，避免测试只复制 bug。

## What I Did
- Modified `openai-shim/src/openai_shim/hermes_backend.py`:
  - added stdlib `hmac`, `hashlib`, and deterministic `json.dumps(..., separators=(",", ":"), ensure_ascii=False)` body serialization.
  - added optional `webhook_secret`.
  - changed Hermes POST from `json=payload` to `content=body_bytes, headers=headers`.
  - adds `X-Hub-Signature-256: sha256=<hex>` only when `webhook_secret` is set; otherwise sends no HMAC header.
- Modified `openai-shim/src/openai_shim/app.py`:
  - reads `HERMES_WEBHOOK_SECRET`.
  - passes it to `HermesBackend(inner, transcript_url, webhook_secret=webhook_secret)`.
- Modified `openai-shim/tests/test_hermes_fork.py`:
  - added `test_hmac_signature_added_when_secret_set`.
  - added `test_no_hmac_when_secret_unset`.
  - both tests use fake-Hermes ASGI and trigger through the OpenAI SDK stream path.
- Modified `openai-shim/README.md`:
  - added `H025 Webhook HMAC` section with env var, subscribe-secret source, compatibility note, and no real secret.
- Did not run `hermes` CLI, did not touch `~/.hermes/`, did not touch ESP32/docker/mcp-endpoint, did not add dependencies, and did not implement secret rotation / timestamp replay prevention / HMAC algorithm selection.

Test command:

```bash
cd openai-shim
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy HERMES_TRANSCRIPT_URL HERMES_WEBHOOK_SECRET OPENAI_SHIM_BACKEND DEEPSEEK_API_KEY DEEPSEEK_BASE_URL
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
collecting ... collected 11 items

tests/test_chat_completions.py::test_streaming_echo_roundtrip PASSED
tests/test_chat_completions.py::test_non_streaming_returns_503 PASSED
tests/test_deepseek_backend.py::test_deepseek_backend_yields_real_stream_chunks PASSED
tests/test_deepseek_backend.py::test_hermes_wraps_deepseek_forks_real_assistant_text PASSED
tests/test_deepseek_backend.py::test_build_backend_with_env_matrix PASSED
tests/test_deepseek_backend.py::test_deepseek_api_error_propagates PASSED
tests/test_hermes_fork.py::test_transcript_posted_when_hermes_url_set PASSED
tests/test_hermes_fork.py::test_hmac_signature_added_when_secret_set PASSED
tests/test_hermes_fork.py::test_no_hmac_when_secret_unset PASSED
tests/test_hermes_fork.py::test_sse_still_works_when_hermes_returns_500 PASSED
tests/test_hermes_fork.py::test_no_fork_when_hermes_url_unset PASSED

============================== 11 passed in 3.38s ==============================
```

`git status --short`:

```text
 M docs/handoffs/active/2026-06-19-m2-hermes-hmac-sign-025.md
 M docs/handoffs/active/2026-06-19-m4-implement-show-emoji-and-text-024.md
 m esp/xiaozhi-esp32
 M openai-shim/README.md
 M openai-shim/src/openai_shim/app.py
 M openai-shim/src/openai_shim/hermes_backend.py
 M openai-shim/tests/test_hermes_fork.py
```

Notes:
- H025-owned changes are the current handoff plus the four `openai-shim/` files listed above.
- `docs/handoffs/active/2026-06-19-m4-implement-show-emoji-and-text-024.md` and `esp/xiaozhi-esp32` are pre-existing H024 dirty state and were not modified for H025.

## Open Questions for Auditor
- None. H025 explicitly says no auditor handoff; M2 batch review is deferred.
