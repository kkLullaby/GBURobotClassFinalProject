---
status: draft
created: 2026-06-18
upstream_repo: NousResearch/hermes-agent
upstream_commit: 426f321e84062e00fd5e6e9271aef48263cafffb   # main, 2026-06-18 13:09 +0530
read_at: 2026-06-18
files_read:
  - plugins/platforms/discord/adapter.py (6801 lines)
  - plugins/platforms/discord/voice_mixer.py (379 lines)
  - gateway/platforms/base.py (relevant sections — `class BasePlatformAdapter` L1803+)
  - gateway/run.py (L10130-L10340 voice wiring)
---

# Hermes Discord adapter — 音频 → agent loop 数据流精读

## 关键文件与符号清单

| 文件 | 关键符号 | 作用 |
|---|---|---|
| `plugins/platforms/discord/adapter.py:604` | `class DiscordAdapter(BasePlatformAdapter)` | discord.py 主适配器，继承通用基类 |
| `…/adapter.py:217` | `class VoiceReceiver` | RTP 解密 + Opus 解码 + 静音切片器，**仅本文件持有** |
| `…/adapter.py:647` | `self._voice_input_callback: Optional[Callable] = None  # set by run.py` | 受 runner 注入的回调钩子 |
| `…/adapter.py:2588` | `if self._voice_input_callback: await self._voice_input_callback(guild_id, user_id, transcript)` | 调用点；**入参带 `guild_id`**，是 Discord 特有概念 |
| `…/adapter.py:464` | `self._decoders[ssrc] = discord.opus.Decoder()` | 直接用 discord.py 的 opus 解码器 |
| `…/adapter.py:404` | `import nacl.secret; box = nacl.secret.Aead(...)` | NaCl + DAVE E2EE 解密（Discord Voice Gateway 专属） |
| `…/adapter.py:55-56` | `try: import discord …  DISCORD_AVAILABLE = True` | 整个 adapter 依赖 `discord.py` |
| `…/voice_mixer.py:1-40` | `class VoiceMixer(discord.AudioSource)` | 出方向 PCM 软混音器；同样依赖 `discord.opus.Encoder.FRAME_SIZE` |
| `gateway/run.py:10157-10158` | `adapter._voice_input_callback = self._handle_voice_channel_input` | runner 在 `/voice join` 时注入 |
| `gateway/run.py:10270` | `async def _handle_voice_channel_input(self, guild_id, user_id, transcript)` | 把 transcript 包成 `MessageEvent(message_type=MessageType.VOICE)` 再过 `adapter.handle_message(event)` |

## "VoiceReceiver → 音频帧 → agent loop" 数据流

```
Discord Voice Gateway WS
        │  (NaCl/DAVE 加密 RTP, op=5 SPEAKING)
        ▼
VoiceConnectionState.add_socket_listener  ← discord.py 私有 API
        │
        ▼ raw UDP packet
VoiceReceiver._on_packet         (adapter.py:404+)
   ├─ nacl.secret.Aead.decrypt   (DAVE E2EE)
   ├─ discord.opus.Decoder.decode → 48k/16-bit/stereo PCM
   ├─ per-SSRC buffer + 1.5s silence detector
   ▼
完整 utterance PCM  ──►  pcm_to_wav (tempfile)
        │
        ▼
tools.transcription_tools.transcribe_audio   (Whisper)
        │
        ▼ transcript (str)
self._voice_input_callback(guild_id, user_id, transcript)   ← adapter.py:2588
        │
        ▼  (注入式回调，runner 在 join 时 wire)
gateway.run._handle_voice_channel_input
        │
        ▼ 构造 MessageEvent(message_type=VOICE, raw_message=SimpleNamespace(guild_id=...))
adapter.handle_message(event)  ──►  Agent loop
```

## Discord-specific 风险点（M3 抄此模板时必须替换的）

1. **`VoiceReceiver` 全 380 行**：解密用 `nacl.secret.Aead` + DAVE，
   解码用 `discord.opus.Decoder()`，订阅 `conn.add_socket_listener` —
   这三件事都是 `discord.py` 私有协议，xiaozhi 一件都用不上（小智走的是
   xinnan-tech WS + Opus payload + ASR 服务，已经"解过密"）。
2. **回调签名硬绑 `guild_id`/`user_id` (int)**：`_voice_input_callback(guild_id, user_id, transcript)` 入参是
   Discord 概念；xiaozhi 没有 guild，user_id 也是 ESP32 MAC/ device_id (str)。
3. **`VoiceMixer` 出方向**：依赖 `discord.opus.Encoder.FRAME_SIZE` 与
   discord.py 的 `AudioSource.read()` 20ms 轮询；xiaozhi 出 Opus 是由
   server 端 TTS 直接 push 给 ESP32（参考 xinnan-tech
   `receiveAudioHandle.py:133` 的 `tts_audio_queue.put`），不需要混音。
4. **`gateway/run.py:10157` "if hasattr(adapter, '_voice_input_callback'):"**：
   runner 用 `hasattr` 探测——意味着**基类 `BasePlatformAdapter` 没有这个
   属性**，是 Discord adapter 私有约定（已在 `gateway/platforms/base.py`
   逐行确认：`rg 'voice_input_callback' gateway/platforms/base.py` 无命中）。
5. **回调注入时机硬绑 slash command**：`_handle_voice_channel_join`
   (`run.py:10139+`) 在响应 `/voice join` 时才 wire 回调；M3 必须改成
   "连接建立即注入"，无 join/leave 概念。

## M3 复用 vs. 重写的判断

- **可抄的形：**入站 transcript → 构造 `MessageEvent(MessageType.VOICE)` →
  `adapter.handle_message(event)` 这条 5 行胶水（`gateway/run.py:10325-10340`）；
  小智的 transcript 来源不同，但生成的 `MessageEvent` 结构一致。
- **不能抄的实：**整个 `VoiceReceiver` 类、`VoiceMixer` 类、`_voice_input_callback`
  签名、`/voice join|leave|off` slash command 三段——这些都是 discord.py 协议层。
- **M3 实际要写的：**xiaozhi WS → 收到 server 端 transcript JSON 帧 →
  直接调一个 xiaozhi 自家的回调（名字别再叫 `_voice_input_callback`，建议
  `_on_xiaozhi_transcript(device_id, transcript)`），里面只复用 5 行胶水。
