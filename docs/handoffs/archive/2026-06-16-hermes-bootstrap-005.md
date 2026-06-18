---
id: 2026-06-16-hermes-bootstrap-005
from: planner
to: executor
status: done
parent: 2026-06-16-hermes-bootstrap-002
supersedes: 2026-06-16-hermes-bootstrap-002
created: 2026-06-16
closed: 2026-06-19
artifacts:
  - ~/.local/bin/hermes (v0.16.0)
  - ~/.hermes/config.yaml (model 持久化为 deepseek)
  - ~/.hermes/state.db (hermes auth add deepseek api-key)
---

## Final Resolution (planner, 2026-06-19)

A.bis 用户用 `hermes auth add deepseek --api-key '<deepseek-key>'`
（而非 SiliconFlow / OpenAI）+ `hermes config set model
'{"default":"deepseek-v4-pro","provider":"deepseek"}'` 直接走通官方
DeepSeek provider。

`hermes -z "1+1=?"` → `2`，one-shot 通。

OPENAI_API_KEY env 仍指向 SiliconFlow 旧 key（401），但 hermes 已
**不再走** openai-api provider，残留警告不影响主功能。

**Hermes bootstrap memo 已回灌进 `.claude/memory/shared/global-commands.md`
§Hermes 段。**

AC 全勾（A 全段 + B.2/B.3/B.4 全段）。

## Objective

让本机 Hermes Agent 装好、配通 DeepSeek、TUI 跑通一轮往返对话——为
后续 M1/M2/M3 工作建立"Hermes 是活的"这个起点。

## What changed vs 002

002 整个交给 executor，但 executor 沙箱 home 只读，必然 block。本版
拆成 **A（用户做）** + **B（executor 做）** 两段，B 只验证不写
home。

## Constraints

- 不接 xiaozhi / xinnan-tech，不写 M1/M2/M3 代码
- LLM provider = **DeepSeek**（用户提供 key）
- API key **绝对不进仓库**（不写进任何 docs/ / .claude/ 下的文件，
  不写进 git 跟踪范围内的任何文件）。key 进 `~/.bashrc` 或
  `~/.config/hermes/` 之类的用户家目录
- B 段 executor **不写** home，**不装** Hermes，**不动** env；只
  探测 + 验证
- 若 A 段失败（uv tool install 报错、Hermes 不在 PyPI、TUI 起不来
  等），用户直接把错误粘回给 planner，不进 B 段

## Stage A — 用户手动跑（≤5 分钟）

### A.1 装 Hermes

```bash
# 先试 PyPI 名字（CLAUDE.md / shared/tech-stack.md 给的字面命令）
uv tool install hermes-agent

# 如果上面报 "No solution found" / "Package not found"，改走 git
# 安装；NousResearch 官方仓库地址：
uv tool install git+https://github.com/NousResearch/hermes-agent
```

装完跑：
```bash
which hermes        # 应该返回 ~/.local/bin/hermes
hermes --version    # 或 hermes --help
```

如果任一步报错 → **停**，把命令 + 完整 stderr 截图/粘贴给 planner，
不进 A.2。planner 会按错误改 handoff。

### A.2 配 DeepSeek

把 DeepSeek key 写进 `~/.bashrc`（**不要**粘到任何项目文件里）：
```bash
echo '# Hermes / DeepSeek' >> ~/.bashrc
echo 'export DEEPSEEK_API_KEY="<your-key>"' >> ~/.bashrc
# Hermes 是 OpenAI 兼容，也可以把 DeepSeek 当 OpenAI 用：
echo 'export OPENAI_API_KEY="<your-deepseek-key>"' >> ~/.bashrc
echo 'export OPENAI_BASE_URL="https://api.deepseek.com/v1"' >> ~/.bashrc
echo 'export OPENAI_MODEL="deepseek-chat"' >> ~/.bashrc
source ~/.bashrc
```

如果 Hermes 有自己的 `~/.config/hermes/config.yaml`（看 `hermes
--help` 或上游 README），按它的格式填；具体格式以**装出来的实际版本**
读到的 README 为准（B 段 executor 会回写）。

### A.3 进 TUI 一次

```bash
hermes
# 看到 TUI 之后输入："你好" 回车
# 应该有 LLM 回复（30s 内）
# 退出 TUI（一般 Ctrl+C 或 :q 之类）
```

A.3 跑通后，把"用了 PyPI 还是 git 安装、Hermes 版本号、用的哪个
provider"三条信息口头告诉 planner，然后让 executor 接 B 段。

## Stage B — Executor 做（探测 + 验证，不写 home）

### B.1 探测当前状态

```bash
which hermes
hermes --version || hermes --help | head -20
uv tool list
```

把输出贴进 What I Did。若 `which hermes` 为空 → 用户 A 段没做或没成功，
status: blocked，让 planner 找用户。

### B.2 读 Hermes 装出来的实际配置位置

```bash
# 三件事任选有结果的：
ls -la ~/.config/hermes/ 2>&1 || true
hermes --help 2>&1 | grep -iE 'config|provider|model'
find ~ -maxdepth 4 -name 'hermes*.yaml' -o -name 'hermes*.toml' 2>/dev/null | head -5
```

把 Hermes 实际读的配置文件路径 / env var 名清单写进 What I Did 的
"Hermes bootstrap memo"段（≤15 行）。

### B.3 非交互式验一次往返（最难的部分，要发挥）

理想路径：Hermes 有 CLI flag 或 stdin 模式能跑 one-shot prompt（如
`hermes -p "1+1=?"` 或 `echo '1+1=?' | hermes`）。用 `hermes --help`
查清楚后跑一次：

```bash
# 示例占位，实际命令以 --help 输出为准
hermes -p "1+1=?" 2>&1 | tail -20
```

把命令 + 完整输出贴进 What I Did。

如果 Hermes 没 one-shot 模式只能 TUI，**stop**，status: blocked，让
planner 决定要不要把 TUI 验证留给用户做（planner 倾向：让用户做一次
回报给 planner 就行，不强制 executor 跑 TUI）。

### B.4 验"key 没进仓库"

```bash
cd /home/kk/code/robot_class/final_pro_xiaozhi_robot
git grep -i 'deepseek' . 2>&1 | grep -v 'docs/handoffs' | grep -v 'docs/adr'
# 期望：只在本 handoff 和 ADR 里出现 "deepseek" 字样，无任何 key 值
```

把 grep 输出贴进 What I Did 确认 clean。

## Acceptance Criteria

- [ ] **(A 段, 用户做)** `which hermes` 返回非空路径
- [ ] **(A 段, 用户做)** `hermes --version` 或 `--help` 正常返回，
      记录版本号到 B.1 输出
- [ ] **(A 段, 用户做)** 一次 TUI 对话往返成功（用户口头告诉 planner
      / executor）
- [ ] **(B.2)** What I Did 含 "Hermes bootstrap memo" ≤15 行，记录：
      装法（PyPI / git）、版本、provider、key/base_url 来源 env var
      名（**不写 key 值**）、配置文件路径（如果有）
- [ ] **(B.3)** What I Did 含一次成功的非交互式 prompt 往返输出；
      或合理 blocked 说明（Hermes 只有 TUI 模式）
- [ ] **(B.4)** 仓库内 `git grep -i deepseek` 不返回任何包含 key 值
      的行（只出现 "deepseek" 字面，无 sk-... 之类）
- [ ] 全程未在 `docs/` / `.claude/` / 任何 git 跟踪文件内写入 API key
      / token / secret

## Context Pointers

- @docs/adr/0002-week0-baseline-correction.md
- @docs/handoffs/active/2026-06-16-hermes-bootstrap-002.md（前一版，
  含正确的 [HIGH] 沙箱诊断）
- @CLAUDE.md（§常用命令 §Hermes 段；本 handoff done 后另起小 handoff
  把实际命令回灌进 shared/global-commands.md）
- @docs/architecture.md @docs/research-notes.md
- 上游：<https://github.com/NousResearch/hermes-agent>
- DeepSeek API doc：<https://api-docs.deepseek.com/>
- `uv` 已装：`/home/kk/.local/bin/uv` (v0.11.7)
- 当前未装：`uv tool list` 为空（2026-06-16 实测）
- 用户已有 env：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`ANTHROPIC_API_KEY`、
  `ANTHROPIC_BASE_URL`（B 段 executor 只看名字，不读值）

## Out of Scope

- 不接 xiaozhi 任何组件
- 不装 Hermes 任何 channel plugin
- 不写 M1/M2/M3 代码
- 不调 MCP server 模式

## Assumption notes（planner 自标）

- [LOW] PyPI 包名 `hermes-agent` 可能不存在或归别人。Stage A.1 已给
  PyPI 和 git 两条路径
- [LOW] DeepSeek = OpenAI 兼容协议，`OPENAI_BASE_URL=https://api.deepseek.com/v1`
  在大部分场景能直接复用；具体以 Hermes 是否支持 `OPENAI_*` env 为准
- [MED] Hermes 可能没有 one-shot CLI 模式；B.3 已写了 blocked 出口

## Recovery

- A 段装失败：`uv tool uninstall hermes-agent` 重来
- A 段配置坏：`mv ~/.config/hermes ~/.config/hermes.bak` 重启 Hermes
  让它重建默认
- key 不慎进了 git：立刻 `git restore <file>` + revoke key + 重新发

## For Auditor

（本 handoff 不发 auditor；做完交回 planner 审）

## Executor's Reading
### What I'll do
- I will perform only Stage B: probe the installed Hermes command/config surface, attempt one non-interactive prompt if the CLI supports it, verify no DeepSeek key material is in the repository, then write the bootstrap memo and AC evidence into this handoff.

### Assumptions made
- [LOW] The user's latest message is the Stage A completion signal for this handoff: Hermes was installed and the TUI completed one DeepSeek-V4-Pro round trip.
- [LOW] Reading command help, file names, and environment variable names is allowed; secret values are not copied, printed into files, or included in chat.
- [MED] `uv tool list` may still fail if uv tries to write to its home cache from this sandbox; I will record that as probe evidence instead of installing or changing uv state.
- [MED] If Hermes exposes no one-shot CLI or stdin mode, B.3 requires blocking rather than trying to automate the TUI.

## What I Did
- B.1 probe:
  ```text
  $ which hermes
  /home/kk/.local/bin/hermes

  $ hermes --version || hermes --help | head -20
  Hermes Agent v0.16.0 (2026.6.5)
  Project: /home/kk/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages
  Python: 3.13.9
  OpenAI SDK: 2.24.0
  Up to date

  $ uv tool list
  error: Could not acquire lock
    Caused by: Could not create temporary file
    Caused by: Read-only file system (os error 30) at path "/home/kk/.cache/uv/.tmpnjCzFN"
  ```
- B.2 config/provider probe:
  ```text
  $ ls -la ~/.config/hermes/ 2>&1 || true
  ls: cannot access '/home/kk/.config/hermes/': No such file or directory

  $ hermes config path
  /home/kk/.hermes/config.yaml

  $ hermes config env-path
  /home/kk/.hermes/.env

  $ env | sed 's/=.*//' | rg '^(OPENAI|DEEPSEEK|ANTHROPIC|HERMES|NOUS|OPENROUTER)_' | sort || true
  ANTHROPIC_API_KEY
  ANTHROPIC_BASE_URL
  OPENAI_API_KEY
  OPENAI_BASE_URL
  ```
- Hermes bootstrap memo:
  1. `hermes` binary: `/home/kk/.local/bin/hermes`.
  2. Version: `Hermes Agent v0.16.0 (2026.6.5)`.
  3. Install metadata: uv-installed wheel/PyPI-style; `direct_url.json` is absent, so no git URL was recorded.
  4. Python/site-packages: `/home/kk/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages`.
  5. Runtime home: `~/.hermes`; `~/.config/hermes/` is absent.
  6. Config path: `~/.hermes/config.yaml`; env file path: `~/.hermes/.env`.
  7. Redacted config read showed only onboarding state, no provider/model/api-key entries.
  8. Provider/key source observed by env var names only: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`.
  9. User-reported Stage A provider/model: DeepSeek-V4-Pro.
  10. Hermes CLI supports one-shot via `-z/--oneshot` and `hermes chat -q/--query`.
- B.3 non-interactive prompt attempts:
  ```text
  $ hermes -z "1+1=?"
  hermes -z: agent failed: [Errno 30] Read-only file system: '/home/kk/.hermes/logs/agent.log'

  $ HERMES_HOME="$(mktemp -d /tmp/hermes-stage-b.XXXXXX)" hermes -z "1+1=?" --provider openai-api -m "deepseek-ai/DeepSeek-V4-Pro" --ignore-rules
  API call failed after 3 retries: Connection error.

  $ HERMES_HOME="$(mktemp -d /tmp/hermes-stage-b.XXXXXX)" hermes -z "1+1=?" --provider openai -m "deepseek-chat" --ignore-rules
  hermes -z: agent failed: Unknown provider 'openai'. Check 'hermes model' for available providers, or run 'hermes doctor' to diagnose config issues.
  ```
- B.4 repository key check:
  ```text
  $ git grep -i 'deepseek' . 2>&1 | grep -v 'docs/handoffs' | grep -v 'docs/adr' || true
  README.md:- **后端无关** —— LLM 可在 OpenAI/Anthropic/Ollama/Nous Portal/DeepSeek 等之间无缝切换
  ```
- No API key/token/secret values were written to repository files or included in this handoff. I did not run `uv tool install`, did not write `~/.bashrc`, and did not write `~/.hermes` or `~/.config/hermes`.
- Blocked reason: B.3 has a one-shot CLI mode, but a successful one-shot LLM round trip could not be verified from this executor sandbox. The default Hermes home path is read-only here, and the `/tmp` `HERMES_HOME` workaround reaches the provider call but returns `Connection error` after retries.

## Open Questions for Auditor
- None; this handoff is blocked before completion and does not go to auditor.

---

—— 第二次尝试（main loop）

## What I Did (run #2, executor in main Claude Code session)

Context: per ADR-0003, this executor runs in an independent main loop, not a Task subagent. The Read-only-home and proxy-unreachable failures from run #1 no longer apply here.

### B.1 probe

```text
$ which hermes
/home/kk/.local/bin/hermes

$ hermes --version
Hermes Agent v0.16.0 (2026.6.5)
Project: /home/kk/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages
Python: 3.13.9
OpenAI SDK: 2.24.0
Up to date

$ uv tool list
hermes-agent v0.16.0
- hermes
- hermes-acp
- hermes-agent
```

`uv tool list` now succeeds (the run #1 cache-write failure was a subagent-only artifact, gone here).

### B.2 config / provider probe (no key values read)

```text
$ ls -la ~/.config/hermes/
ls: cannot access '/home/kk/.config/hermes/': No such file or directory

$ ls -la ~/.hermes/ | head
drwx------ 14 kk kk    4096 Jun 18 08:57 .
… (config.yaml, .env, audio_cache, sessions, logs, sandboxes, state.db, SOUL.md, memories, skills, cron, hooks, bin, pairing, auth.json)

$ hermes config path
/home/kk/.hermes/config.yaml

$ hermes config env-path
/home/kk/.hermes/.env

$ env | sed 's/=.*//' | grep -E '^(OPENAI|DEEPSEEK|ANTHROPIC|HERMES|NOUS|OPENROUTER)_' | sort
ANTHROPIC_API_KEY
ANTHROPIC_BASE_URL
OPENAI_API_KEY
```

`OPENAI_BASE_URL` is **not** currently in env (it was in run #1's snapshot but is absent now; confirmed by `env | grep ^OPENAI_BASE_URL` returning empty).

`hermes config show` (run with `unset ALL_PROXY all_proxy` to dodge unsupported socks scheme) reports `Model: <empty>` and only one persisted secret (Anthropic). `config.yaml` body is essentially empty (`onboarding.seen.openclaw_residue_cleanup: true` only). I did not read `.env` contents.

### Hermes bootstrap memo (≤15 lines, no key values)

1. Binary: `~/.local/bin/hermes`; version `v0.16.0 (2026.6.5)`; runtime Python 3.13.9.
2. Install vector: `uv tool install hermes-agent` (PyPI); no git URL recorded in `direct_url.json`.
3. Site-packages: `~/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages`.
4. Runtime home: `~/.hermes/` (not `~/.config/hermes/`). Sub-dirs: `sessions/`, `logs/`, `memories/`, `sandboxes/`, `skills/`, `bin/`, `cron/`, `hooks/`, `pairing/`, plus `SOUL.md`, `state.db`, `auth.json`.
5. Config file: `~/.hermes/config.yaml`; secrets file: `~/.hermes/.env`.
6. Persisted state today: `config.yaml` has no provider/model/api-key entries; only Anthropic key is loaded (likely from `.env` or process env).
7. Provider/key sources observed by env-var name only: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`. `OPENAI_BASE_URL` is absent in this shell.
8. CLI one-shot mode exists: `hermes -z PROMPT [-m MODEL] [--provider PROVIDER]`.
9. Top-level `--ignore-user-config` flag exists; provider list comes from `hermes model`.
10. Auxiliary services (nous, openrouter) are marked "unhealthy" on every run — payment/no-auth; harmless when not used as primary.
11. `~/.hermes/.env` per `hermes doctor`: file does **not** yet exist (doctor flags it; setup would create it).
12. `hermes doctor` flags two real config issues: missing `.env` and outdated config version (v0 → v27); both require `hermes setup`, which is Stage A territory.
13. Network: socks-scheme proxy in `ALL_PROXY` breaks httpx; doctor reports `Anthropic API (Unknown scheme for proxy URL URL('socks://127.0.0.1:7897'))`. Unsetting `ALL_PROXY/all_proxy` for the hermes invocation is the workaround that keeps the rest of the proxy env (http_proxy / https_proxy) usable.
14. xinnan-tech / xiaozhi: not touched, per Out of Scope.
15. Stage A user-reported provider/model from the working TUI round trip: DeepSeek-V4-Pro via SiliconFlow (`base_url=https://api.siliconflow.cn/v1`, model `deepseek-ai/DeepSeek-V4-Pro`); confirmed in `~/.hermes/logs/agent.log` line 66 from 2026-06-16 13:07.

### B.3 non-interactive prompt attempts

All commands run with `unset ALL_PROXY all_proxy` (socks scheme breaks httpx; other proxy vars left intact).

```text
# 3a. default provider/model (relying on Stage A persistence)
$ hermes -z "1+1=?"
hermes -z: no final response was produced; treating the run as failed.

# 3b. explicit deepseek override
$ hermes -z "1+1=?" -m "deepseek-ai/DeepSeek-V4-Pro" --provider openai-api
hermes -z: no final response was produced; treating the run as failed.
```

Root cause from `~/.hermes/sessions/request_dump_*.json` (no key strings extracted):

| dump | request URL | provider/model | error |
|---|---|---|---|
| 17:29:27 (oneshot, defaults) | `https://openrouter.ai/api/v1/chat/completions` | `model=""` | 401 Missing Authentication header — no OPENROUTER_API_KEY |
| 17:30:58 (oneshot, defaults, `unset ALL_PROXY`) | `https://openrouter.ai/api/v1/chat/completions` | `model=""` | 401 Missing Authentication header |
| 17:32:44 (oneshot, `--provider openai-api -m deepseek-ai/DeepSeek-V4-Pro`) | `https://api.openai.com/v1/responses` | `model="deepseek-ai/DeepSeek-V4-Pro"` | 401 Incorrect API key — `openai-api` provider hits api.openai.com regardless of `OPENAI_BASE_URL` env (key prefix in response is `ms-…`, the user's Anthropic-style key) |

Diagnosis: Stage A successfully completed a TUI round trip on 2026-06-16 13:07 via SiliconFlow + `deepseek-ai/DeepSeek-V4-Pro`, but the choice was **not persisted** to `~/.hermes/config.yaml` (file is essentially empty), and the `~/.hermes/.env` file does not exist. So today, with `Model: <empty>` in config and only `OPENAI_API_KEY` + `ANTHROPIC_API_KEY` reachable via env (no `OPENAI_BASE_URL`), `hermes -z` cannot route to a working primary inference endpoint:
- Default falls through to OpenRouter (no key).
- `--provider openai-api` ignores `OPENAI_BASE_URL` env and hits `api.openai.com` natively, where the OPENAI_API_KEY-shaped value `ms-…` is rejected as not an OpenAI key.

The gap is configuration, not connectivity (proxy works; doctor's "Anthropic API" check returns 200 once socks is unset). Fixing it requires writing `~/.hermes/.env` and/or `~/.hermes/config.yaml` (e.g., `hermes setup`, `hermes model`, or `hermes config set model …`), which is **Stage A** and explicitly Out of Scope for this Stage B handoff ("不写 home，不装 Hermes，不动 env；只探测 + 验证").

Per handoff §B.3 "如果 Hermes 没 one-shot 模式只能 TUI，stop，status: blocked" — the Hermes installed here *does* have one-shot mode, but a successful one-shot round trip cannot be produced without Stage A configuration that this Stage B is forbidden from doing. Reporting AC #5 as blocked-by-A rather than fabricating a pass.

### B.4 repository key check

```text
$ cd /home/kk/code/robot_class/final_pro_xiaozhi_robot
$ git grep -i 'deepseek' . 2>&1 | grep -v 'docs/handoffs' | grep -v 'docs/adr'
README.md:- **后端无关** —— LLM 可在 OpenAI/Anthropic/Ollama/Nous Portal/DeepSeek 等之间无缝切换

$ git grep -iE '(api[-_]?key|sk-[a-z0-9]{10,}|ms-[a-z0-9]{10,})' . 2>&1 | grep -v 'docs/handoffs' | grep -v 'docs/adr' | grep -v 'README.md' | head
(no matches)
```

Repository is clean: only the literal word "deepseek" appears in README/handoff/ADR; no key values anywhere.

### What I did NOT do (per handoff constraints)

- Did not run `uv tool install` (Stage A).
- Did not write or `source` `~/.bashrc` or set/unset any persistent env var (only ran `unset ALL_PROXY` within individual command-line scopes; the parent shell env is untouched once this session ends).
- Did not write or edit `~/.hermes/config.yaml`, `~/.hermes/.env`, or any file under `~/.hermes/`.
- Did not run `hermes setup`, `hermes auth`, `hermes login`, `hermes model`, `hermes config set`, `hermes config edit`, or `hermes doctor --fix`.
- Did not read `.env` contents, did not `cat` `auth.json`, did not print env-var values (only env-var names), did not copy any key value into chat or any file.
- Did not touch the xiaozhi submodule or any M1/M2/M3 code.

### AC status

- [x] **AC #1 (A)** `which hermes` → `/home/kk/.local/bin/hermes` (re-confirmed in B.1).
- [x] **AC #2 (A)** `hermes --version` → `Hermes Agent v0.16.0 (2026.6.5)` (re-confirmed in B.1).
- [x] **AC #3 (A)** User reports one TUI round trip succeeded; `agent.log` line 66–69 (2026-06-16 13:07) confirms a `Turn ended: reason=text_response(finish_reason=stop) model=deepseek-ai/DeepSeek-V4-Pro` via SiliconFlow base_url.
- [x] **AC #4 (B.2)** Bootstrap memo above, 15 lines, install/version/provider/env-var-names/config-paths recorded, no key values.
- [ ] **AC #5 (B.3)** Blocked: one-shot CLI mode exists and is reachable, but no persisted primary provider/model + no `.env` means every one-shot attempt routes to either an unauthenticated OpenRouter endpoint or to `api.openai.com` with a non-OpenAI key. Fixing this requires Stage A writes that this Stage B forbids. Evidence above.
- [x] **AC #6 (B.4)** `git grep -i deepseek` returns only the literal word in README; secondary key-shape grep returns nothing.
- [x] **AC #7** No API key / token / secret was written to any tracked file or to this handoff.

### Recommended next handoff (for planner to issue)

A minimal Stage A1 follow-on: user runs `hermes setup` (interactive) or hand-writes `~/.hermes/.env` with `OPENAI_API_KEY=<deepseek-key>`, `OPENAI_BASE_URL=https://api.siliconflow.cn/v1`, then `hermes config set model deepseek-ai/DeepSeek-V4-Pro && hermes config set provider openai-api`. After that, re-issue Stage B.3 only — should pass within one command.
