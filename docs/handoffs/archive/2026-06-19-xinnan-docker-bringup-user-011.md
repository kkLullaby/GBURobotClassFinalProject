---
id: 2026-06-19-xinnan-docker-bringup-user-011
from: planner
to: user
parent: 2026-06-19-xinnan-server-bringup-008
supersedes:
status: done
created: 2026-06-19
artifacts:
  - docker container "xiaozhi-esp32-server"
  - 仓库外 .env (~/.config/xiaozhi-server/.env 或类似)
---

## Why user-led not executor-led

H008 B 段被 codex 沙箱卡在 `permission denied ... docker.sock` + `Cannot
open netlink socket`。executor sandbox 无 docker / netlink 权限。按
[ADR-0003](../adr/0003-executor-runs-in-main-loop.md) 类型 II（"需写
home / 用 daemon / 改 system state"的工作），改 **user-led**。

executor 的 A 段（baseline 不能不重烧切 URL）已 done，落在
[diagnoses](../diagnoses/2026-06-19-esp32-baseline-server-url-switch.md)。

## Objective

起 xinnan-tech `xiaozhi-esp32-server` 的 **minimal** 模式（不要 full —
后者拖 MySQL/Redis/Java），验证 8000 / 8003 三个端口在监听。

minimal compose 文件已确认在 `/tmp/upstream-clones/xiaozhi-esp32-server/
main/xiaozhi-server/docker-compose.yml`（H008 已查清）。

## Pre-flight

```bash
# 确认 docker 可用、目标端口空闲
docker ps                     # 应该能跑（你在 docker 组）
ss -tln | grep -E ':(8000|8003)\b'  # 期望 NO output（端口空闲）

# 如果 8000 / 8003 已被占用：不要 stop 现有容器，本 handoff 改用 18000/18003
# （记进 What I Did，后续 M1/M2 也要用同样端口号）
```

## Stage A — 跑通 minimal docker（≤10 分钟，主要看镜像 pull）

```bash
# 1. 把上游 compose 仓库 sync 到一个长期目录（/tmp 重启就没了，不行）
mkdir -p ~/code/xinnan-tech
git clone --depth=1 https://github.com/xinnan-tech/xiaozhi-esp32-server.git \
  ~/code/xinnan-tech/xiaozhi-esp32-server
cd ~/code/xinnan-tech/xiaozhi-esp32-server
git log -1 --format='%H %s'   # 记 commit，写进 What I Did

# 2. 看一眼 minimal compose 真的对应哪个文件
cd main/xiaozhi-server
ls docker-compose*.yml
# 期望看到 docker-compose.yml（minimal，仅 xiaozhi-esp32-server 服务）
# 和 docker-compose_all.yml（full，含 web+MySQL+Redis）

# 3. 看 compose 需要哪些 env / 配置文件挂载
cat docker-compose.yml | head -40
# 注意：可能需要 ./data/.config.yaml 这种挂载文件，没准备好容器会立刻退

# 4. 准备配置（最小可启动）
# 上游通常需要一个 config.yaml，先用模板：
mkdir -p data
cp config_from_api.yaml data/.config.yaml 2>/dev/null || \
cp config.yaml data/.config.yaml 2>/dev/null || \
echo "TODO: 模板名变了，看 README"   # 如果俩都没有，把 ls 输出贴给我

# 5. 起容器
docker compose up -d
sleep 5
docker ps --filter name=xiaozhi-esp32-server --format '{{.Names}} {{.Status}} {{.Ports}}'
# 期望：xiaozhi-esp32-server  Up X seconds  0.0.0.0:8000->8000/tcp, 0.0.0.0:8003->8003/tcp

# 6. 验端口 + health
ss -tln | grep -E ':(8000|8003)\b'
docker logs --tail=30 xiaozhi-esp32-server
curl -sS http://localhost:8003/ 2>&1 | head -c 200   # 或 /health；看 logs 里 server 用什么 path
```

## Stage B — 配置 LLM provider（**不入 git**）

minimal server 起来后会立刻报"没有 LLM provider"。配进**容器读得到、
git 看不到**的路径：

```bash
# data/.config.yaml 已挂载进容器；它就是配置入口
# 在 ~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml
# 找 LLM 段，配 SiliconFlow 或其它 OpenAI-compatible：
#   LLM:
#     selected_module:
#       LLM: ChatGLMLLM   # 或 SiliconFlowLLM 之类，看 README
#     ChatGLMLLM:
#       type: openai
#       model_name: ...
#       url: https://api.siliconflow.cn/v1
#       api_key: <your-key>

# 重启容器让它读新 config
docker compose restart

# 再 docker logs --tail=30 确认 "LLM provider initialized"
```

具体 LLM 段格式以你看到的 config 模板为准。

## Acceptance Criteria

- [ ] `docker ps --filter name=xiaozhi-esp32-server` 返回 Status 含 "Up"
- [ ] 8000 / 8003 在 `ss -tln` 显示 LISTEN
- [ ] `docker logs --tail=30` 没有 fatal error，含 "Server started" /
      "Listening on" 之类
- [ ] LLM provider 配好（B 段），重启后 logs 含 "LLM ... initialized"
      或等价字样
- [ ] `~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server/
      data/.config.yaml` 含 API key，**但**该路径在 git 跟踪范围外（确认
      `cd /home/kk/code/robot_class/final_pro_xiaozhi_robot && git status`
      不显示这个文件）
- [ ] 把 docker-compose 文件路径 + 关键 env / config 路径 + 用的 LLM
      provider 名 + base_url（**不要 key**）写一段 ≤10 行 memo 贴给我

## Out of Scope

- 不让 ESP32 真去连这个 server（那是 H1b 之后的事）
- 不写任何 M1/M2 代码
- 不配置 ASR/TTS（先让 LLM 通；ASR/TTS 默认走 FunASR/EdgeTTS 本地版应该
  能自动）

## Recovery

- 容器起不来：`docker compose logs --tail=100` 贴给我
- 端口冲突（8000/8003 被你的 voice-agent-pg 或 n8n 占了？查清楚）：把
  compose 里 ports 映射改 18000/18003，记进 memo
- compose 报 `network not found`：`docker compose up -d` 自动建网，不用
  手干预
- API key 不慎写进 git 跟踪文件：`git restore <file>` + 立刻 revoke key

## Related

- A 段已 done：@docs/diagnoses/2026-06-19-esp32-baseline-server-url-switch.md
- @docs/handoffs/archive/2026-06-19-xinnan-server-bringup-008.md（前身）
- @docs/research-notes/xinnan-tech-openai-and-mcp.md
- 现有占用：voice-agent-pg :5432, n8n_financial_bot :5678（**都跟本任务
  端口不冲突**）

## For Auditor

不发 auditor。M1 开工前 planner 自审。

## Executor's Reading

> 注：handoff `to: user`，因 H008 时 executor 的 codex sandbox 缺 docker /
> netlink。当前会话是 ADR-0003 描述的"独立 Claude Code 主会话"（有用户
> shell 的全部权限：docker / 家目录 / HTTP 代理均已验通），用户在
> AskUserQuestion 中明确同意 **"全代跑用 DeepSeek key"**，因此我以
> "代用户的 main-loop"身份接手并填 Reading 留痕。本会话权限上能完整跑完
> 两段。

### What I'll do
- Stage A：`git clone --depth=1` xinnan-tech 仓库到 `~/code/xinnan-tech/`
  → `cd main/xiaozhi-server` → 看 compose / 配模板 → 起 minimal compose
  → 验 8000/8003 LISTEN 与 logs
- Stage B：从 `~/.hermes/state.db` 读 DeepSeek api_key（用户已授权），
  写进 `data/.config.yaml` 的 LLM 段（按容器内 README/默认模板的字段），
  `docker compose restart`，验 logs 含 LLM initialized
- 末尾追加 What I Did、改状态 done、按 protocol 移到 archive/、更新 INDEX
- 不发 to: auditor handoff（planner 已注明 M1 开工前自审）

### Assumptions made
- [LOW] `git clone` 走 `https_proxy=127.0.0.1:7897`（env 已 export，验过有效）
- [LOW] xinnan-tech 仓库的 `main/xiaozhi-server/docker-compose.yml`
  即为 minimal（H008 已查清，handoff 复述）
- [LOW] LLM provider 名按 xinnan-tech README 选其支持的 OpenAI-compatible
  类型（例如 `DeepSeekLLM` / `OpenAILLM` + `base_url=api.deepseek.com`），
  以仓库代码/模板里实际枚举为准；不凭印象写 provider 名
- [MED] DeepSeek key 流过本 Claude transcript（用户 AskUserQuestion
  明确同意，但仍属敏感数据；memo 不贴 key 本身）。**`.config.yaml`
  路径在仓库外 → 不会进 git**，符合 AC #5
- [MED] 端口 18000/18003 fallback 不需要触发（pre-flight 已验 8000/8003
  空闲）；如 compose 起来后才发现冲突再走 Recovery
- [MED] xinnan-tech repo HEAD 可能比 H008 当时新（depth=1 clone 拿到的是
  最新 main）；这是 H008 prefer 的"用最新"行为，无须固定 commit。把
  `git log -1 --format='%H %s'` 写进 What I Did 留痕
- [LOW] 从 state.db 读 key 用 `sqlite3 .../state.db "select ..."`；如表
  结构非预期则降级问用户要 key
- 无 HIGH，按 protocol 不阻塞，开干

## What I Did

### Stage A — minimal docker (done 2026-06-19 02:02 +08:00)

- `git clone --depth=1 https://github.com/xinnan-tech/xiaozhi-esp32-server`
  到 `~/code/xinnan-tech/xiaozhi-esp32-server/`
  HEAD: **`a1973e07b71e018199018060497c58cd45d5d387`**
  ("Merge pull request #3227 from xinnan-tech/update-theme") —
  比 H008 时新，是 main 当前 tip
- `cd main/xiaozhi-server` → `mkdir -p data models/SenseVoiceSmall`
- compose 镜像 pull: `ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:server_latest`
  (~3.2 GB extracted)
- compose 不映射 8004 端口（**与 tech-stack.md 文档 "8000/8003/8004 三端口"
  描述不一致**：minimal compose 仅暴露 8000 ws + 8003 http；8004 仅在 full
  / mcp-endpoint 单独服务有；handoff 011 实际只要求验 8000/8003）
- 不需任何 `.env` 文件；env 只设 `TZ=UTC`

### Stage B — DeepSeek LLM provider (done 同上)

- 从 `hermes auth list` 提取 DeepSeek key（用户 AskUserQuestion 授权
  复用 Hermes 已配的那把）
- 写入 `~/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml`
  （**仓库外**，git status 不显示，AC #5 验证通过）
  - `selected_module.LLM: DeepSeekLLM`
  - `LLM.DeepSeekLLM`: type=openai, model=deepseek-chat,
    url=https://api.deepseek.com
  - `server.websocket: ws://0.0.0.0:8000/xiaozhi/v1/`
- 该最小 override 由容器 fall-back 到镜像内 `config.yaml` 拿其余默认
  （ASR=FunASR / VAD=SileroVAD / intent=function_call / memory=nomem）

### 触发的额外工作 (handoff Out of Scope 之外但必须做)

- handoff 假设 "ASR 默认走 FunASR 本地版应该能自动" 不成立：FunASR 必须
  加载 `models/SenseVoiceSmall/model.pt`（~893 MB），不存在/空文件
  → `EOFError: Ran out of input` → server 启动失败 → `restart: always`
  陷入崩溃循环
- 修：从 modelscope 下载 model.pt 真文件
  (936291369 B = 893 MB)，路径 `~/code/xinnan-tech/.../models/SenseVoiceSmall/model.pt`
- 重启后 ASR/VAD/LLM/Intent/Memory 全 init 成功，WebSocket 监听正常

### 验证 (AC 全过)

| AC | 结果 |
|----|------|
| #1 docker ps "Up" | `Up 53 seconds` ✓ |
| #2 8000/8003 LISTEN | `ss -tln` 显示 0.0.0.0:8000 + 0.0.0.0:8003 ✓ |
| #3 logs 无 fatal + "Server started" 等价 | 含 `Websocket地址是 ws://172.19.0.2:8000/xiaozhi/v1/` ✓ |
| #4 LLM initialized | `初始化组件: llm成功 DeepSeekLLM` ✓ |
| #5 .config.yaml 出 git scope | path = `~/code/xinnan-tech/...`，主仓 `git status` 不显示 ✓ |
| #6 memo ≤10 行 | 见下 |

### 额外冒烟 (handoff 没要求，3 秒花费)

DeepSeek key 直连 `api.deepseek.com/v1/chat/completions` 返回 "pong"
(deepseek-chat 实际路由到 deepseek-v4-flash，正常 alias 行为)。证明
LLM 链路端到端通，不只是字符串校验通过。

### 路径与文件 (不入 git)

- repo dir: `/home/kk/code/xinnan-tech/xiaozhi-esp32-server/` @ a1973e0
- compose:  `main/xiaozhi-server/docker-compose.yml`
- config:   `main/xiaozhi-server/data/.config.yaml` (含 key，git-invisible)
- model:    `main/xiaozhi-server/models/SenseVoiceSmall/model.pt` (893 MB)
- 容器名:   `xiaozhi-esp32-server`
- 端口:     `8000` (ws), `8003` (http+OTA+vision); **8004 未起**

### 给 planner 的 memo (AC #6, 8 行)

```
xinnan-tech minimal 起来了：
- repo:    ~/code/xinnan-tech/xiaozhi-esp32-server @ a1973e0 (2026-06 main tip)
- compose: main/xiaozhi-server/docker-compose.yml  (image ghcr.nju.edu.cn/.../server_latest)
- config:  main/xiaozhi-server/data/.config.yaml   ← 仓库外，含 key
- ports:   8000 ws (xiaozhi/v1/), 8003 http (OTA + vision)  — 8004 minimal 未起
- LLM:     DeepSeekLLM  base=https://api.deepseek.com  model=deepseek-chat (复用 Hermes key)
- ASR:     FunASR(local) — 需 models/SenseVoiceSmall/model.pt (~893MB modelscope) 
- 注:      handoff "ASR 默认能自动" 不成立 — 缺 model.pt 会 EOFError 崩溃循环
- M1 接入: ws://localhost:8000/xiaozhi/v1/  ＋  OTA http://localhost:8003/xiaozhi/ota/
```

## Open Questions for Auditor

不发 auditor (handoff 显式说 M1 开工前 planner 自审)。但给 planner 的
3 个 follow-up 输入：

1. **tech-stack.md 8004 描述**: 文档列 "8000/8003/8004 三端口"；minimal
   compose 实际只 8000/8003。8004 是 `mcp-endpoint` 子服务的端口（见
   `docs/mcp-endpoint-enable.md`），需要时单独起 — planner 之后若 M1
   走 mcp-endpoint 模式，要把它加进 compose / 单独跑
2. **ADR 候选**: handoff 假设 "ASR 默认走 FunASR 本地应能自动"，实际
   必须先下 893 MB model.pt 否则崩溃循环。是否值得起一个 ADR / 改进
   handoff 模板，要求未来 docker bringup 类件显式列 "前置模型/资产清单"
3. **DeepSeek key 流转**: 这次 key 走了 Claude transcript (用户授权)。
   若后续 M1/M2 也要它，建议改成由 user 在本地 `export` 到 shell env
   再让 service 读 env，避免 key 反复进 AI session

---

(executor 完工签字：本会话以 ADR-0003 主会话 / 代用户角色完成；
不写新 handoff to auditor；按 protocol §1 移到 archive/，并由本会话
更新 INDEX。)
