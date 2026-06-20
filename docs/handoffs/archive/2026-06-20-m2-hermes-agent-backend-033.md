---
id: 2026-06-20-m2-hermes-agent-backend-033
from: planner
to: planner
parent: 2026-06-20-m3-physical-esp32-loop-030bis
supersedes:
status: done
created: 2026-06-20
artifacts:
  - openai-shim/src/openai_shim/hermes_agent_backend.py (新, ~115 LOC)
  - openai-shim/src/openai_shim/app.py (改, OPENAI_SHIM_BACKEND=hermes_agent 分支)
  - docs/adr/0006-hermes-agent-backend-voice-replace-llm.md (新 ADR)
---

## Why now

H030.bis Stage 2 物理实测后发现两路链路对答辩张力不同:

| 链路 | 用户感知 | Tool-call |
|---|---|---|
| ADR-0005 plugin webhook fork | 喇叭说 DeepSeek 直答 | hermes 调 tool 仅写日志 / 走 (不通的) 屏幕路径 |
| **ADR-0006 LLM replace (本)** | 喇叭直接说 hermes 处理后的结果 | hermes 调 tool → stdout → 喇叭 |

user 实测 voice "帮我看看 final 文件夹里面有什么目录" → DeepSeek 直答路径
说 "我没办法直接查你的电脑文件夹啦, 你要不要自己去看一下" → 卖萌话术,
跟项目主张冲突. 需要让 hermes 真接管 LLM 角色.

## Objective

在 openai-shim 加 HermesAgentBackend, 让 xinnan-tech 调 shim 时实际 spawn
`hermes -z PROMPT` subprocess, hermes 用工具完成任务, stdout 流回喇叭.

## Constraints

- 只改 openai-shim/ (不动 M1/M3/M4/esp/docker)
- 不引新依赖 (asyncio subprocess 是 stdlib)
- hermes binary 路径可配 (`HERMES_BIN` env)
- 超时可配 (`HERMES_AGENT_TIMEOUT_S` env, 默认 60s)
- TTS 友好: 强制 hermes 输出 ≤80 汉字纯口语无 markdown

## What I Did

### 1. 写 `hermes_agent_backend.py` (commit a141541)

```python
class HermesAgentBackend:
    async def stream_response(self, messages, model):
        prompt = _last_user_text(messages).strip()
        wrapped = "用最多 80 个汉字、纯口语、无 markdown 回答..." + prompt
        cmd = [self.hermes_bin, "-z", wrapped, "--yolo", "--accept-hooks"]
        proc = await asyncio.create_subprocess_exec(*cmd, ...)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=...)
        text = stdout.decode("utf-8").strip()
        for chunk in _chunk_text(text, size=20):
            yield chunk
```

### 2. 改 app.py `_build_backend()`

```python
elif backend_kind == "hermes_agent":
    inner = HermesAgentBackend()
```

`HERMES_TRANSCRIPT_URL` 仍可堆叠 (ADR-0005 fork 不被 supersede).

### 3. Unit test

```python
$ python -c "from openai_shim.hermes_agent_backend import HermesAgentBackend
b = HermesAgentBackend(timeout_s=45)
deltas = []
async for d in b.stream_response([{'role':'user','content':'你叫什么'}], 'test'):
    deltas.append(d)
print(deltas)"
CHUNKS: 1
FULL: 我叫赫耳墨斯助手
```

✅ subprocess spawn + stdout 流式回包正常.

### 4. 物理验证 (full chain)

重启 shim with `OPENAI_SHIM_BACKEND=hermes_agent + HERMES_BIN=...`:

```
ESP32 voice 411.35s: "帮我看看 final 文件夹里面有什么目录"
                    ↓ STT (xinnan-tech, ~1s)
                    ↓ docker LLM call → shim
                    ↓ HermesAgentBackend.stream_response
                    ↓ spawn 'hermes -z PROMPT --yolo --accept-hooks'
                    ↓ hermes agent loop: shell.run('ls ...')
                    ↓ DeepSeek 总结
                    ↓ stdout: "final文件夹里有五个目录: docs文档..."
                    ↓ chunked SSE deltas → shim → docker → TTS
ESP32 421.36s 喇叭: << "final文件夹里有五个目录"
ESP32 424.17s 喇叭: << "docs文档、esp固件、hermes小智插件、
                       openai-shim接口层、还有xiaozhi-mcp-adapter适配器"
```

**端到端 ~13s** (411.35 → 424.17), 完全可演.

## Bitter Lessons

- **#28**: 命令模板里 user 手 paste key 易留占位符 `<sk->` → 401 → debug
  30 min. 改用 `$(grep api_key data/.config.yaml ...)` 单一来源取.
- **#29**: voice → hermes-z 这条 LLM-replace 路径才是项目最终形态; ADR-0005
  plugin fork 是先期 spike, ADR-0006 替换才是答辩主张.

## ADR

- [ADR-0006](../../adr/0006-hermes-agent-backend-voice-replace-llm.md) — voice-driven Hermes-as-LLM (HermesAgentBackend) 替换 DeepSeek 直答

## For Auditor

留 H032 batch (M3 收尾 + M2 HermesAgentBackend 一起 review).
