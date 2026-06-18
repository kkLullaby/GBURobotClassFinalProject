---
id: 2026-06-16-hermes-bootstrap-002
from: planner
to: executor
status: blocked
parent:
created: 2026-06-16
artifacts:
  - ~/.local/share/uv/tools/hermes-agent/ (uv tool install 后会出现)
  - ~/.config/hermes/  或 项目内自创建的配置目录
---

## Objective

通过 `uv tool install hermes-agent` 在本机装好 Hermes Agent，配通一个
LLM provider，进 TUI 完成一轮往返对话（输入 "你好" 拿到 LLM 回复），
证明 Hermes 本身能独立跑——为后续 M1/M2/M3 工作建立"Hermes 是活的"
这个起点。

## Constraints

- **不**接 xiaozhi、不接 xinnan-tech、不写任何 M1/M2/M3 代码。这一步
  把 Hermes 当独立产品装，验证它能跑。
- LLM provider 选 **DeepSeek**（成本低、国内延迟可接受、不需要梯子）
  作为默认；如果用户已经在 `~/.bashrc` / `~/.config/` 有其它 provider
  的 key（OpenAI / Anthropic / Ollama），可以用那个，但**必须在 What
  I Did 段记录最终用的是哪个 + 来源**
- 不要把任何 API key 写进本仓库的文件；env 走 `~/.bashrc` 或 Hermes
  自己的配置目录（取决于 Hermes 的约定，需要读它的 README/docs）
- 如果 `uv tool install hermes-agent` 失败（PyPI 上不一定有这个名字），
  立刻 stop，把错误贴到 What I Did 改 status: blocked，由 planner 决
  定走 `uv tool install git+https://github.com/NousResearch/hermes-agent`
  还是 `uvx --from <repo> hermes` 还是其它路径

## Acceptance Criteria

- [ ] `which hermes` 返回非空（在 `~/.local/bin/` 或 uv 管理的路径下）
- [ ] `hermes --version` 或 `hermes --help` 能正常打印（证明二进制可
      执行、没缺依赖）
- [ ] `hermes` 进 TUI 不报错，能进到对话主界面
- [ ] 在 TUI 输入一句话（如 "你好" 或 "1+1=?"），LLM 在 30s 内有回
      复（如果是慢的本地 LLM 走 Ollama，60s 内即可）
- [ ] 至少一次跨 session 验证：退出 TUI 再 `hermes` 进一次，看看历史
      是否在；记录观察结果（不是 AC，是 fact-finding，写进 What I Did）
- [ ] 把"装的什么版本、配的哪个 provider、配置文件在哪、env var 在哪
      读"写一段 ≤15 行的"Hermes bootstrap memo"贴到 What I Did，让以
      后的 Claude session 不用重新摸索

## Context Pointers

- @docs/architecture.md（§Hermes 在本项目中的角色）
- @docs/research-notes.md（如果里面写了 Hermes 装法 / 选型理由）
- @CLAUDE.md（§常用命令 §Hermes 段 + §Project Scope —— Hermes 本身
  不在仓库内，配置文件在 `~/.config/hermes/` 之类的用户目录）
- @.claude/memory/shared/global-commands.md（§Hermes 段，目前只写了
  `uv tool install hermes-agent` + `hermes`，本 handoff done 后回填
  实际可用的命令）
- 上游：<https://github.com/NousResearch/hermes-agent>
- LLM provider 注册入口（DeepSeek）：<https://platform.deepseek.com>
  （不强制；如果用户已有别家 key 优先复用）
- `uv` 已装：`/home/kk/.local/bin/uv`
- 当前未装：`uv tool list` 为空

## Out of Scope

- 不接 xiaozhi 任何组件
- 不写 M2 openai-shim
- 不装 Hermes 的任何 channel plugin（discord / telegram / xiaozhi 都不装）
- 不调 MCP server / agent loop 等高级特性，进 TUI 能对话即可

## Suggested Steps

1. 先看 Hermes 上游 README + docs 是不是真的支持 `uv tool install
   hermes-agent`。如果 PyPI 上没有 `hermes-agent` 包，PyPI 搜一下名
   字，或者 `uv tool install git+https://github.com/NousResearch/hermes-agent`
2. 装完后 `uv tool list` 应该能看到 hermes-agent
3. 看 Hermes 怎么读 LLM provider 配置：通常是 `~/.config/hermes/config.yaml`
   或类似路径，或环境变量 `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` / `ANTHROPIC_API_KEY`
4. 选一个 provider，配 key 和 base_url（DeepSeek 用 OpenAI 兼容接
   口，`OPENAI_BASE_URL=https://api.deepseek.com/v1` + `OPENAI_API_KEY=<key>`
   + `OPENAI_MODEL=deepseek-chat` 这种常见模式；具体以 Hermes 文档为准）
5. `hermes` 启动 → 试一轮对话
6. 把以上路径全部写进 What I Did 的 bootstrap memo

## Candidate Root Causes

不是 bug-class，无 root cause 段。

## Assumption notes（planner 自标）

- [LOW] `uv tool install hermes-agent` 这个命令字面正确（CLAUDE.md 和
  shared/tech-stack.md 都这么写）—— 如果 PyPI 上不存在，executor 自
  决一个替代方案、记录到 Open Questions
- [LOW] DeepSeek 作为默认 provider —— 如果用户 reject，给个备选名单
  让用户挑

## Recovery

- 装坏了：`uv tool uninstall hermes-agent` 后重来
- 配置坏了：把 `~/.config/hermes/` 整个备份后删掉，让 Hermes 自己重
  建默认配置

## For Auditor

（本 handoff 不发 auditor；做完直接交回 planner 审）

## Executor's Reading
### What I'll do
- Try the handoff's literal `uv tool install hermes-agent` path first, then verify `hermes` and TUI conversation only if the install succeeds without writing secrets into the repository.

### Assumptions made
- [LOW] Existing `OPENAI_*` / `ANTHROPIC_*` environment variables, if used later, count as "user already has another provider key" under the handoff; values must not be copied into repo files or this handoff.
- [MED] If install succeeded, using the existing OpenAI-compatible environment instead of DeepSeek would be acceptable because the handoff explicitly permits an already-configured provider when recorded.
- [HIGH] This executor sandbox cannot write to `/home/kk/.cache`, `/home/kk/.local`, or likely `~/.config/hermes`; satisfying the requested persistent `uv tool install` and Hermes config locations requires user-side execution or relaxed filesystem permissions.

## What I Did
- Read the handoff context pointers for Hermes project role, install command expectations, and provider/key handling.
- Confirmed `uv` exists: `uv --version` prints `uv 0.11.7 (x86_64-unknown-linux-gnu)`.
- Confirmed `hermes` is not currently on `PATH`: `which hermes` returns no path.
- Confirmed the sandbox cannot write the normal home locations:
  - `/home/kk`: not writable
  - `/home/kk/.cache`: not writable
  - `/home/kk/.local`: not writable
- Ran the required install command and stopped on failure:
  ```text
  $ uv tool install hermes-agent
  error: Could not acquire lock
    Caused by: Could not create temporary file
    Caused by: Read-only file system (os error 30) at path "/home/kk/.cache/uv/.tmpUriws6"
  ```
- Detected provider-related environment variable names already present (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`) but did not copy or store secret values.
- No Hermes files, config files, or repository source files were created for this handoff.

## Open Questions for Auditor
- None; this handoff is blocked before installation and does not go to auditor.

## Planner Resolution (2026-06-16)

Executor 的 [HIGH] 假设正确，是 planner 设计问题：本 handoff 同时
要求 (a) 装 `hermes` 进 `~/.local/`、(b) 读 `~/.config/hermes/`、
(c) 让 TUI 跑起来——这三件事都需要写用户 home，executor 沙箱
read-only，必然 block。

Hermes 装这件事跟 ESP-IDF 5.5.2 同性质：**用户全局环境的依赖，
应该由用户自己装**，executor 只做"装好之后是否能跑"的客观验证。

本 handoff 终结为 blocked。后续工作迁移到
[2026-06-16-hermes-bootstrap-005](2026-06-16-hermes-bootstrap-005.md)
（supersedes: 002），改为"用户装 + executor 探测验证"两段。
