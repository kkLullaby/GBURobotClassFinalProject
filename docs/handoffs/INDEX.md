# Handoff Index

> This file is auto-loaded so the agent gets a fast picture of
> handoff status. Auto-maintained (PostToolUse hook) or updated
> manually.
>
> At project initialization this file is nearly empty; it starts
> filling up once the first handoff is written.

Last compacted: 2026-06-19

## Active (status: pending|claimed|blocked)

- [2026-06-19-mcp-endpoint-server-bringup-016](active/2026-06-19-mcp-endpoint-server-bringup-016.md) planner → **user** (pending, ~25 min): "起 xinnan-tech mcp-endpoint-server (port 8004) + 配进 xiaozhi-server + 真 M1 pipe round-trip + ESP32 voice 调 echo tool" — M1 spike 升级真链路

## Recent done / archived (last 7 days)

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
