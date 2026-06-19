# Handoff Index

> This file is auto-loaded so the agent gets a fast picture of
> handoff status. Auto-maintained (PostToolUse hook) or updated
> manually.
>
> At project initialization this file is nearly empty; it starts
> filling up once the first handoff is written.

Last compacted: 2026-06-19

## Active (status: pending|claimed|blocked)

- [2026-06-19-mcp-endpoint-server-bringup-016](active/2026-06-19-mcp-endpoint-server-bringup-016.md) planner → **user** (blocked, Stage A/B/C done by planner main-loop, Stage D ESP32 voice 留 user; **新加 ready-to-run paste 块** 6h 后基础设施仍 LIVE): "起 xinnan-tech mcp-endpoint-server (port 8004) + 配进 xiaozhi-server + 真 M1 pipe round-trip + ESP32 voice 调 echo tool" — **9/13 AC ✅**：mcp-endpoint up + KEY/TOKEN extracted + config 含 `mcp接入点是 ws://10.2.244.38:8004/...` + M1 pipe `connected to MCP endpoint`；剩 4 AC 物理段：用户连 wifi 10.2 段 + 1-paste 命令在 §Stage D Ready-to-Run 段
- [2026-06-19-m2-deepseek-backend-021](active/2026-06-19-m2-deepseek-backend-021.md) planner → executor (**claimed**, **可交 coding agent / sandbox-friendly**): "M2 加 DeepSeekBackend 接 openai.AsyncOpenAI(base_url=api.deepseek.com) + fake-deepseek ASGI mock 测 + HermesBackend wrap 复用" — Week 1.4 真智能；与 H016 / H020 都不阻塞；H018(2)+H019(3)+H021(4)=9 测齐

## Recent done / archived (last 7 days)

- [2026-06-19-real-hermes-transcript-handshake-020](archive/2026-06-19-real-hermes-transcript-handshake-020.md) planner → user (done 2026-06-19, planner main-loop 代跑 per ADR-0003 II): "hermes webhook + shim → 真 Hermes session 收 transcript" — **5/5 Stage 全 ✅**：webhook platform 启用 + subscribe + gateway run + shim with HERMES_TRANSCRIPT_URL + curl 触发 + Hermes 真 spawn agent session `20260619_205520_be1c7197` 读到 `msg='XiaoZhi user said: hi from H020. Assistant replied: echoed: hi from H020.'`；ADR-0005 主线**全验证**。Stage D shim path 401 (HMAC 未签, 预期); D.bis 手算 HMAC 走通 X-Hub-Signature-256 (GitHub 风格, 不是 X-Hermes-*) → 收 202。Bitter lessons: HMAC 强制 + header name + agent 继承 proxy → DeepSeek 连不出 → demo polish 时改 ~/.hermes/.env
- [2026-06-19-m2-hermes-fork-transcript-019](archive/2026-06-19-m2-hermes-fork-transcript-019.md) planner → executor (done 2026-06-19, codex spike full sandbox completion): "M2 fork transcript 给 Hermes (HermesBackend 包 EchoBackend + httpx fire-and-forget POST + fake-hermes ASGI mock 测)" — codex 91 LOC backend + 140 LOC test 5/5 PASS **2.99s** (含原 H018 2 个 + 新 3 个: fork ok / hermes 500 still SSE / no fork without env)；echo_backend / sse 零修改；bonus: 加 `_openai_client()` helper 避 OpenAI SDK sandbox 平台探测线程池卡住；ADR-0005 主线收尾，H016+H018+H019 = demo §1 答辩可演
- [2026-06-19-m2-spike-openai-shim-018](archive/2026-06-19-m2-spike-openai-shim-018.md) planner → executor (done 2026-06-19, codex spike + planner unblock per ADR-0003 II): "M2 spike: openai-shim FastAPI + SSE + echo backend + pytest e2e" — codex 写 365 LOC 干净骨架（app.py + sse.py + echo_backend.py + e2e test + README 55 行），sandbox 无 PyPI 装不了 deps；planner main-loop 装 28 包 + `pytest -xvs tests/` **2/2 PASS 3.95s** + curl SSE smoke (frame 含 finish_reason="stop", `[DONE]` 收尾)。backend Protocol 接 H019 Hermes fork 已铺；ADR-0005 主线进度 +1

- [2026-06-19-m1-spike-echo-tool-015](archive/2026-06-19-m1-spike-echo-tool-015.md) planner → executor (done 2026-06-19, codex spike + planner unblock per ADR-0003 II): "M1 spike: echo tool round-trip" — codex 写出 428 LOC 干净骨架（pipe.py + echo_tool.py + e2e test + README）但 sandbox 无 PyPI 装不了 deps；planner main-loop 装 deps + 跑 `pytest -xvs tests/` → **PASSED in 1.17s**。bonus：发现 user 默认 python 是 PlatformIO penv，M1+ 必须用 conda python；shared/global-commands.md 待补

- [2026-06-19-flash-baseline-to-local-server-h1b-013](archive/2026-06-19-flash-baseline-to-local-server-h1b-013.md) planner → user (done 2026-06-19): "H1b 烧 baseline + 切 OTA 本地 docker + 一轮对话" — **Week 0 闭环 🎉**；Stage A/B planner main-loop 代跑，Stage C/D 用户物理端 (physical-ops coach session)；ESP32 MAC `ac:a7:04:30:91:78`，喇叭响，RTT 4-6s；bonus：server 自动发 MCP initialize 带 vision capability (待回灌 contract)

- [2026-06-19-idf-build-verify-h1a-012](archive/2026-06-19-idf-build-verify-h1a-012.md) planner → executor (done 2026-06-19, planner main-loop unblock per ADR-0003 II): "H1a 本机 IDF 5.5.2 build 验证 (OTTO_ROBOT 板; 不 flash)" — **xiaozhi.bin 3.5 MiB, 11% free**；3 处 unblock：codex 沙箱无 proxy + IDF submodules 用户漏 init + OTTO_ROBOT 板必须 append 3 个 CONFIG (HTTPD_WS_SUPPORT + CAMERA_OV2640/3660, 来自 `boards/otto-robot/config.json`)；7 min wall-clock 全冷 build；13 warning 全是上游
- [2026-06-19-docs-alignment-009](archive/2026-06-19-docs-alignment-009.md) planner → executor (done 2026-06-19): "Week 0 ADR 落地后 6 处文档对齐" — 6 处 wording 落地（CLAUDE.md IDF 不入库 / shared/ submodule + Hermes 命令实测 / tech-stack Week 0 commit pin / roadmap §Week 3 + Day 16 OBSOLETE banner / README clone 含 submodule）；未 commit；H012 blocked 摘要在 What I Did

- [2026-06-19-xinnan-docker-bringup-user-011](archive/2026-06-19-xinnan-docker-bringup-user-011.md) planner → **user** (done 2026-06-19, main-loop 代跑 per ADR-0003): "xinnan-tech minimal docker + DeepSeek LLM" — repo `a1973e0` 起在 `~/code/xinnan-tech/`, ports 8000/8003 LISTEN, DeepSeekLLM init ok; 额外发现：FunASR 需先下 893MB model.pt，否则 EOFError 崩溃循环；不发 auditor
- [2026-06-16-hermes-bootstrap-005](archive/2026-06-16-hermes-bootstrap-005.md) planner → executor (done 2026-06-19): "Hermes 装 + TUI + one-shot 跑通" — 用户 `hermes auth add deepseek` 修了 A.bis；`hermes -z "1+1=?"` → "2"；config memo 已回灌 shared/global-commands.md
- [2026-06-19-mcp-transcript-egress-spike-010](archive/2026-06-19-mcp-transcript-egress-spike-010.md) planner → executor (done 2026-06-19, codex run): "M1 transcript 出口 spike (supersedes 007)" — **verdict (d) other**: transcript 没 MCP-client callback，实际走 OpenAI-compatible `messages`；M3 → 几十行 < 1 天（可能引出 ADR-0005）
- [2026-06-19-xinnan-server-bringup-008](archive/2026-06-19-xinnan-server-bringup-008.md) planner → executor (A done / B → 011, 2026-06-19): "切本地 server spike (A) + docker bringup (B)" — **A verdict NO**: baseline 不重烧改不了 server URL → H1b 必须在 011 后立刻发；B 拆走给 user (011)
- [2026-06-16-submodule-fixup-004](archive/2026-06-16-submodule-fixup-004.md) planner → executor (done 2026-06-19, commit b15c5ec): "esp/xiaozhi-esp32 → 正式 submodule pin b392c63"
- [2026-06-18-upstream-code-reading-audit-006](archive/2026-06-18-upstream-code-reading-audit-006.md) executor → auditor review (done 2026-06-18): "审 003 verdict YES" — pass / accept
- [2026-06-16-upstream-code-reading-003](archive/2026-06-16-upstream-code-reading-003.md) planner → executor (done 2026-06-18): "上游代码精读 + Discord callback 诊断" — verdict YES

## Superseded / blocked-and-replaced (kept for trace, in archive/)

- [2026-06-16-submodule-fixup-001](archive/2026-06-16-submodule-fixup-001.md) blocked → superseded by 004 (AC #3/#6 错)
- [2026-06-16-hermes-bootstrap-002](archive/2026-06-16-hermes-bootstrap-002.md) blocked → superseded by 005 (executor 沙箱限制)
- [2026-06-18-mcp-transcript-egress-spike-007](archive/2026-06-18-mcp-transcript-egress-spike-007.md) blocked → superseded by 010 (cosmetic error stop-rule 过严)

## Archive

Older items in `archive/`. See [archive/INDEX.md](archive/INDEX.md) for monthly summaries.

---

## Maintenance

- Count threshold: active/ > 50 → oldest moves to archive/
- archive/ > 500 → into archive/deep/ (INDEX no longer mentions)
- Regenerate: `/regen-handoff-index` (post-plugin) or edit by hand
