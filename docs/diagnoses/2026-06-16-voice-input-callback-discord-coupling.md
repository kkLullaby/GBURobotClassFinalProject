---
id: 2026-06-16-voice-input-callback-discord-coupling
status: current
verdict: YES
question: "Hermes 的 `_voice_input_callback` 机制（roadmap 第 16 天 🔥🔥 风险）是不是 Discord-specific？"
upstream_repo: NousResearch/hermes-agent
upstream_commit: 426f321e84062e00fd5e6e9271aef48263cafffb   # main, 2026-06-18
read_at: 2026-06-18
related:
  - docs/research-notes/hermes-discord-adapter.md
  - docs/adr/0001-adopt-agent-arch.md  (pitfall #4)
  - docs/roadmap.md  (Week 3 风险 1 / 降级方案 B)
---

# Diagnoses: `_voice_input_callback` 与 Discord 的耦合程度

## Verdict: **YES** — Discord-specific

`_voice_input_callback` 这个**名字**所代表的"音频 → agent loop 注入回调"
机制，**目前在 Hermes 上游 (commit 426f321) 是 Discord adapter 私有的**：

- 既不存在于通用基类
- 也不存在于其它 10 个 platform adapter 中
- 入参签名硬绑 Discord 概念 (`guild_id`, `user_id: int`)
- 周边整套 stack (VoiceReceiver / VoiceMixer / nacl / discord.opus) 全是 discord.py 私有协议

## 代码证据 (≥3 条)

### 证据 1 — 回调属性只在 Discord adapter 里声明

```
$ rg 'voice_input_callback' --type py
plugins/platforms/discord/adapter.py:647: self._voice_input_callback: Optional[Callable] = None  # set by run.py
plugins/platforms/discord/adapter.py:2588:            if self._voice_input_callback:
plugins/platforms/discord/adapter.py:2589:                await self._voice_input_callback(...)
gateway/run.py:10157:        if hasattr(adapter, "_voice_input_callback"):
gateway/run.py:10158:            adapter._voice_input_callback = self._handle_voice_channel_input
gateway/run.py:10172:            adapter._voice_input_callback = None
gateway/run.py:10193:            adapter._voice_input_callback = None
... (10+ hits, all only under plugins/platforms/discord/, gateway/run.py, tests/gateway/)
```

`rg 'voice_input_callback' gateway/platforms/base.py` 0 命中——基类
`BasePlatformAdapter` (`base.py:1803`) 完全不知道这个东西。

`rg -l voice_input_callback plugins/platforms/` 只命中 `discord/`，
其它 10 个 adapter (`google_chat/teams/irc/line/mattermost/ntfy/photon/simplex/homeassistant`) 0 命中。

### 证据 2 — 回调签名硬绑 Discord 概念

`plugins/platforms/discord/adapter.py:2587-2592`：

```python
if self._voice_input_callback:
    await self._voice_input_callback(
        guild_id=guild_id,    # ← Discord-only 概念
        user_id=user_id,      # ← discord int snowflake
        transcript=transcript,
    )
```

`gateway/run.py:10270`：

```python
async def _handle_voice_channel_input(
    self, guild_id: int, user_id: int, transcript: str
):
    ...
    adapter = self.adapters.get(Platform.DISCORD)   # ← 硬编码平台
    if not adapter: return
    text_ch_id = adapter._voice_text_channels.get(guild_id)
    ...
```

注入 + 消费两侧都假设 Discord：runner 拿到回调后第一件事是
`self.adapters.get(Platform.DISCORD)`，签名里的 `guild_id` 直接用于查
Discord 文本频道映射。

### 证据 3 — 周边 stack 全栈依赖 discord.py 协议

- `plugins/platforms/discord/adapter.py:55-56`：`import discord` 失败整
  个 adapter 失活（`DISCORD_AVAILABLE = False`）
- `:217` `class VoiceReceiver` — 380 行解 RTP/NaCl/DAVE/Opus，全用
  discord.py 私有 API (`vc._connection.add_socket_listener`,
  `discord.opus.Decoder`)
- `:404` `import nacl.secret; box = nacl.secret.Aead(self._secret_key)`
  — Discord Voice Gateway 专属加密
- `voice_mixer.py:1-16`：`discord.py (Rapptz) ships no audio mixer...`
  整个出方向也绑死 `discord.opus.Encoder.FRAME_SIZE` 与
  `discord.AudioSource.read()` 20ms 轮询

xiaozhi 走的是**完全不同的栈**：xinnan-tech server 在
`core/handle/receiveAudioHandle.py:39` 的 `startToChat(conn, text)` 处
就已经把音频做完 VAD/ASR 拿到 transcript；ESP32 → server 走自家 WS +
Opus payload，没有 RTP、没有 NaCl、没有 DAVE，**90% 的 Discord 入站 stack
直接报废**。

### 证据 4（旁证）— Telegram 等通用 voice 没走这个回调

`gateway/run.py:8061-8067` 显示通用 voice path：

```python
# MessageType.AUDIO = audio file attachment (e.g. .mp3, .m4a) — never STT
# MessageType.VOICE = voice message (Opus/OGG) — always STT
if event.message_type == MessageType.AUDIO: ...
elif event.message_type == MessageType.VOICE or ...:
```

通用 voice 是 **adapter 自己上传文件 → STT → 直接构造 `MessageEvent(VOICE)`**
进 `handle_message()`，**不**经过 `_voice_input_callback` 钩子。
说明这个钩子是 Discord adapter 为了"voice channel 实时流"特殊场景搞的
私有约定，不是 Hermes 通用 voice ingest API。

## 影响评估 — 对 ADR-0001 pitfall #4 与 M3 工作量

### 名字层面 vs. 机制层面

- **名字层面**：M3 不应试图"在 xiaozhi adapter 上加一个 `_voice_input_callback`
  让 runner 自动 wire"——runner 端的 `hasattr` 探测和回调消费都硬编码
  Discord，wire 上去也不会被调用。
- **机制层面**：好消息是 Hermes 通用 voice ingest 已经存在
  ("adapter 拿到 transcript → `MessageEvent(MessageType.VOICE)` →
  `handle_message(event)`"，gateway/run.py:8061-8067 + adapter.py:2607
  共同证明)。M3 完全可以走这条**通用**路径，不需要碰 `_voice_input_callback`。

### roadmap "降级方案 B" 触发判断

**结论：不需要触发完整降级方案 B。**

降级方案 B 的本意是"如果回调机制是 Discord-only 且无通用替代，M3 要重写
整个 inbound voice 路径"。现实是：

- 回调机制（`_voice_input_callback` 这个**钩子本身**）确实 Discord-only ✅
- **但**通用 inbound voice 已经存在 = adapter 内部完成 STT，自己构造
  `MessageEvent(VOICE)`，调 `handle_message()`。这条路 M3 抄起来很短。

### M3 实际工作量重估

| 工作 | 时长估计 | 备注 |
|---|---|---|
| 写 `XiaozhiAdapter(BasePlatformAdapter)` 骨架 (connect/disconnect/send) | 1.5 天 | 抄 discord adapter 但只保留消息收发，扔掉所有 voice channel 代码 |
| M1 收到 transcript → 调 `XiaozhiAdapter.handle_message(MessageEvent(VOICE))` | 0.5 天 | 5 行胶水，对应 run.py:10325-10340 的 pattern |
| send TTS 回小智（出方向） | 1 天 | 通过 M1 转发文本，由 xinnan-tech server 自家 TTS 发声 |
| 联调 + 修 session key 之类的小坑 | 1 天 | pitfall #9 |

**合计 ≈ 4 天**，而非 roadmap 风险段假设的"如果是 Discord-specific 则
8 → 18 天"。原 18 天估算的隐含假设是"通用 voice ingest 也不存在"，
本次证据 4 推翻了这个假设。

### 建议（不替 planner 决策，仅列证据）

1. 把 ADR-0001 pitfall #4 从"最大未知 (🔥🔥)"降级为"已确认 + 已有解决方案"
   （写新 ADR supersede 或在 #4 末尾追加确认行）。
2. 不启动降级方案 B，按通用 `MessageEvent(VOICE)` 路径继续 M3 计划。
3. M3 设计文档明确写："不要复用 `_voice_input_callback` 这个名字，
   xiaozhi adapter 自己持有 transcript 入口（建议
   `_on_xiaozhi_transcript`），内部走 `BasePlatformAdapter.handle_message`"。
4. roadmap Week 3 第 2 天的"硬性确认"节点可以提前关闭（本诊断即结论）。

— 由 planner 起 ADR 决定是否采纳上述 4 条。
