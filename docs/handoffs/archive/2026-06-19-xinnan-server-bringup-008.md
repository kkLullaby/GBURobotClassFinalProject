---
id: 2026-06-19-xinnan-server-bringup-008
from: planner
to: executor
status: blocked
parent:
created: 2026-06-19
artifacts:
  - docs/diagnoses/2026-06-19-esp32-baseline-server-url-switch.md  (新建, A 段)
  - docker container "xiaozhi-esp32-server"                          (B 段)
---

## Objective

两段（必须按 A → B 顺序）：

**A. spike**：回答 "上游 baseline 固件能不能**不重烧**就把 server URL 从
官方/16302 切到本地 docker server"——可能的路径有：WiFi 配网 AP 页面、
按键长按进配置模式、设备自带 web 控制台、菜单项 OTA URL、远程下发
config。verdict 落在 `docs/diagnoses/...esp32-baseline-server-url-
switch.md`，verdict ∈ {YES + 给出步骤 / NO + 必须重烧 / PARTIAL + 部
分可改}。

**B. docker bringup**：起 xinnan-tech `xiaozhi-esp32-server` 的
**minimal** 模式（不要 full 模式 —— 它会拖 MySQL/Redis/Java，体积差
10 倍），验证容器内 8000 / 8003 / 8004 三个端口在监听。

B 段**不**依赖 A 段结论。A 段 verdict 决定的是"是否还需要后续 H1b
重烧"，跟"docker 起没起得来"是两件事。

## Constraints

- minimal 模式 **必须**确认（official docker-compose.yml 可能默认 full；
  上游通常用一份单独的 `docker-compose.minimal.yml` 或环境变量分歧）
- 不**配置任何 LLM provider key** 写进 git 跟踪文件；docker 需要 LLM
  key 时通过 env / `.env` 文件，路径放仓库**外**（`~/.config/xiaozhi-
  server/.env` 之类）
- A 段是**只读 spike**：不烧固件、不连真设备、不动 ESP32 任何东西
- B 段允许跑 docker daemon；如果系统已经有同名容器（很可能没有，docker
  ps 实测无），先 `docker ps -a | grep xiaozhi` 看清楚，**不要**贸然
  `docker rm`
- 任何端口冲突（已被本机其它进程占用）→ 不强行抢占，记录 + status:
  blocked
- 错误处理纪律见 §Error-handling discipline

## Acceptance Criteria

### A 段（spike）

- [ ] `docs/diagnoses/2026-06-19-esp32-baseline-server-url-switch.md`
      存在，frontmatter `status: current` + `verdict: YES | NO | PARTIAL`
- [ ] body 至少 3 条证据（上游 README / docs / 代码 file:line，或官方
      App / web console 的截图说明 + 文档链接）
- [ ] 含一段"对 H1b 烧录链路的影响"：YES → H1b 可以推迟到真正写 M4
      时再做；NO → H1b 必须在 H008 之后立刻发；PARTIAL → planner 看
      具体形态决定

### B 段（docker）

- [ ] `docker ps --filter name=xiaozhi-esp32-server --format
      '{{.Names}} {{.Status}} {{.Ports}}'` 输出非空，Status 含 "Up"
- [ ] `ss -tlnp | grep -E ':(8000|8003|8004)\b'`（或 docker 内
      `netstat -tlnp`）三个端口都 listening
- [ ] 把 minimal 模式的 docker-compose 文件路径 + 关键 env var 列表写
      进 What I Did（≤15 行 memo），让以后的 Claude session 不用重新摸
- [ ] 至少跑一次 `curl -sS http://localhost:8003/health` 或等价 health
      endpoint（不存在的话用 docker logs 末 20 行代替），证明容器内部
      app 真的起来了不是只有进程框架

## Context Pointers

- @docs/research-notes/xinnan-tech-openai-and-mcp.md（003 已落档；上游
  的 OpenAI provider / MCP endpoint 描述在这里）
- 上游：<https://github.com/xinnan-tech/xiaozhi-esp32-server>
- 上游已 clone：`/tmp/upstream-clones/xiaozhi-esp32-server/` @ `a1973e07`
  （H007 可能也在用；只读，不冲突）
- @docs/architecture.md §6.1 (xinnan-tech minimal 模式选型背景)
- @docs/adr/0001-adopt-agent-arch.md §"本项目特有 pitfall" #8 (minimal
  vs full 差异巨大，必须显式确认是 minimal)
- @docs/roadmap.md §Week 0 §0.2
- @CLAUDE.md @.claude/rules/handoff-protocol.md @docs/adr/0003-executor-runs-in-main-loop.md
- 16302 web 烧录入口（A 段如果发现这是切 URL 的唯一手段，要在 diagnoses
  里记一笔）：<https://www.16302.com/firmwarehub/O3XoF1s>

## Out of Scope

- 不连真 ESP32（A 段全部 desk research；B 段只验 docker 端口，**不**
  让 ESP32 真去连 server——那是后续 handoff）
- 不写 M1 任何代码
- 不配置 LLM provider 跑通对话（先让 server 起来；provider 配置进下一
  个 handoff）
- 不动 esp/xiaozhi-esp32/ 工作树（只读上游 README）

## Error-handling discipline（**全项目通用，本节内容已写进 H010**）

按 H007 经验教训修正：

- **substantive error**（命令成功执行后产生的语义错误：文件不存在、
  权限拒绝、network refuse、docker pull 拒绝、git operation 冲突等）
  → status: blocked + 完整 stderr + 当前状态说明
- **cosmetic error**（你自己命令打错：路径拼错、引号缺一只、flag 名
  写错、shell quoting 问题等）→ **不要 block**，自己改正命令重试，
  在 What I Did 里加一行"重试 N 次后用 <修正后命令>"，继续
- **重复同类 substantive error ≥3 次**（你已经改 3 次还在错同一个）
  → status: blocked，承认这是 substantive 不是 cosmetic
- 改 status 之前先问自己："如果 planner 看到这条 block，第一句话会不
  会是'这只是你打错命令'？" yes → 不要 block

## Assumption notes（planner 自标）

- [LOW] xinnan-tech 的 docker-compose 文件路径在上游 README 里能找到
- [LOW] minimal 模式在上游有明确文档（不是隐藏配置）
- [MED] A 段 verdict 大概率是 PARTIAL：上游固件多半有 WiFi AP 页面但
  不一定有"server URL"字段；本机最终可能仍需要重烧。executor 按实际看
  到的写，不要为了配合 roadmap 强 verdict YES
- [MED] B 段 docker pull 拉镜像可能要 5-30 分钟（上百 MB），把镜像
  pull 时间作为可接受耗时，**不**算 block

## Recovery

- A 段一时找不到上游对 server URL 切换的描述：在 README 里搜
  `OTA_URL` / `WEBSOCKET_URL` / `配网` / `provisioning` 关键字；找
  代码：`grep -rn "ota_url\|websocket_url" esp/xiaozhi-esp32/main/`
  本仓库已有 submodule 可读
- B 段容器起不来：`docker logs xiaozhi-esp32-server | tail -50` 贴
  到 What I Did，常见原因是端口冲突 / config 文件缺失
- 端口冲突：不要 stop 主项目里现有的容器（postgres / n8n 之类）；
  把 xinnan-tech 端口映射改到 18000/18003/18004，记录在 memo 里

## For Auditor

不发 auditor。M1 开工前 planner 自审；M1 整段做完后 batch audit。

## Executor's Reading
### What I'll do
- 先静态确认 baseline 固件不重烧切换 server URL 的可行性并写 diagnosis，再按上游 minimal compose 起 `xiaozhi-esp32-server` 容器并验证端口/health/logs。

### Assumptions made
- [LOW] 本任务可读取但不修改 `esp/xiaozhi-esp32/` submodule，以本地代码和上游文档作为 A 段证据。
- [LOW] `docs/diagnoses/` 不在 planner-only 禁写清单内，允许作为本 handoff 的 A 段产物写入。
- [LOW] docker bringup 可以使用仓库外的 `/tmp` 或用户配置目录保存临时运行配置，不把 provider key 或本机私密配置写入 git 跟踪文件。
- [MED] 如果本机 8000/8003/8004 已占用，按 Recovery 使用 18000/18003/18004 映射并在 memo 记录；这会满足“容器起得来”但不是默认端口形态。

## What I Did
- A 段已完成：新建 `docs/diagnoses/2026-06-19-esp32-baseline-server-url-switch.md`，frontmatter `status: current`、`verdict: NO`。
- A 段结论：baseline 官方/16302 固件没有用户可达的无重烧 server URL 切换入口；H1b 需要后续发起 build/flash 或等价 NVS seed。
- A 段证据覆盖 README、`CONFIG_OTA_URL`、OTA response 写入 `websocket` NVS、WebSocket 连接读取 `websocket/url`、WiFi/BluFi 配网只写 WiFi 凭据、Otto boot button 只进 WiFi config。
- Cosmetic retry：第一次 `rg` 误把不存在的 `esp/xiaozhi-esp32/components` 放进搜索路径；重试 1 次后用正确路径 `esp/xiaozhi-esp32/main esp/xiaozhi-esp32/docs esp/xiaozhi-esp32/README.md` 完成检索。
- B 段已读上游 compose：minimal 是 `/tmp/upstream-clones/xiaozhi-esp32-server/main/xiaozhi-server/docker-compose.yml`，只含 `xiaozhi-esp32-server` 服务并映射 8000/8003；full 是 `docker-compose_all.yml`，额外含 web、MySQL、Redis。
- B 段阻塞在本机权限前置检查，尚未创建/启动容器，尚未做端口/health 验证。
- docker 检查命令的完整错误文本：

```text
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

- 端口监听检查命令的完整错误文本：

```text
Cannot open netlink socket: Operation not permitted
```

## Open Questions for Auditor
- 无；本 handoff 不发 auditor。当前需要用户/宿主环境提供 Docker API 和端口监听检查权限后才能继续 B 段。
