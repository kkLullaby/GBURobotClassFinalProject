# lark-event-listener

Long-connection listener for Lark/Feishu IM events — the **inbound** counterpart
to [`lark-mcp-server`](../lark-mcp-server/)'s outbound `lark_send_message_to_self`
tool. Part of the [ottagent](../README.md) project.

> 让飞书 ottagent app 成为 hermes 的一个 channel:你在飞书私聊机器人,
> 机器人通过 hermes 推理 + 调 lark tool **真回你**。

## Flow

```
你的飞书账号
   │  ① 私聊给 ottagent app 发 "今天怎么样"
   ↓
飞书开放平台
   │  ② 长连接 ws push event (im.message.receive_v1)
   ↓
lark-event-listener (本包)
   │  ③ 过滤 (跳过 bot 自己 / 群聊 / 非文本 / 重复 message_id)
   │  ④ spawn `hermes -z "<prompt>" --yolo --accept-hooks`
   ↓
hermes-agent
   │  ⑤ DeepSeek reason → tool_call lark_send_message_to_self(text=...)
   ↓
飞书 OpenAPI → 你的飞书私聊收到回复
```

详见 [ADR-0009](../docs/adr/0009-lark-inbound-long-connection.md)。

## 装

```bash
cd lark-event-listener
UV_CACHE_DIR=/tmp/uv-cache uv pip install --system -e '.[test]'
pyx -m pytest -xvs tests/    # 14/14 PASS in <1s
```

## 配凭证

复用 lark-mcp-server 的 `~/.config/lark-mcp/.env` (不需要新文件)。长连接模式
**不需要** `LARK_ENCRYPT_KEY` / `LARK_VERIFICATION_TOKEN` — 那两个是 webhook
模式的凭证,长连接走 ws 协议层鉴权,SDK 自动处理。

如果还没装好 `lark-mcp-server`,先按 [那边 README](../lark-mcp-server/README.md)
跑完 Step 1-3。

## 飞书后台:开通长连接事件订阅 (~3 min, 一次性)

1. 打开 <https://open.feishu.cn/> → 进 ottagent app → 左侧 **"事件与回调"**
2. **"事件订阅"** 子菜单 → 添加事件 → 搜 `接收消息 v2.0` (`im.message.receive_v1`) → 添加
3. 同页 **"事件订阅方式"** → 切换到 **"使用长连接接收"**
4. 左侧 **"版本管理与发布"** → 重新创建版本 → 提交审核 → 管理员同意

> ⚠️ 如果之前为了 webhook 配过 verification_token / encrypt_key,**可以保留**,
> 长连接模式 SDK 不会用它们,但留着不影响。

## 启停

```bash
# 起 (后台 nohup)
bash ../scripts/start_lark_listener.sh
tail -f /tmp/lark_listener.log

# 期望看到:
#   ... lark_event_listener.main: lark_event_listener starting (long-connection)...
#   ... lark_oapi: connected to ws-feishu, ready to receive events

# 停
pkill -9 -f lark_event_listener.main
```

也跟着 ottagent 全链路一键启动:
```bash
bash ../scripts/start_all.sh    # Step 6 自动起 listener
bash ../scripts/stop_all.sh     # 一并杀
```

## 验证 (端到端)

确保 listener + lark-mcp-server (registered to hermes) + hermes 都在:

```bash
hermes mcp list | grep lark    # 应见 lark
pgrep -f lark_event_listener.main    # 应有 PID
```

打开飞书 → ottagent app 私聊 → 发文本 `"hello ottagent"`,然后:

```bash
# 1. 看 listener 是否收到
tail -f /tmp/lark_listener.log
# 应见: received from ou_xxx (chat=oc_xxx msg_id=om_xxx): hello ottagent
#       spawn hermes: hermes -z ...

# 2. 看 hermes 是否真调 lark tool (cold spawn ~3-5s, DeepSeek ~5-15s)
# /tmp/lark_listener.log 后面应见: hermes done (rc=0). stdout_head=...

# 3. 飞书私聊应该收到 ottagent 的回复 (~10-30s 后)
```

## 防死循环

机器人通过 `lark_send_message_to_self` 发出去的消息也会触发
`im.message.receive_v1`(receiver = 自己),如果不过滤会自激刷消息。
本包用 **两层防御**:

1. `sender_type == "app"` → skip (任何 bot/app 发的都不响应)
2. (可选) 设 `LARK_BOT_OPEN_ID=ou_xxx` 环境变量,精确按 bot 自身 open_id 过滤

正常情况下 #1 已经够,#2 是冗余。

## 已知限制

- **只支持私聊 (p2p)**。群聊事件会被 skip — 留下一期 (需要决定 "ottagent 在群里
  什么时候发话" 的策略,@mention only? 直接刷屏?)。
- **只支持文本消息 message_type=text**。表情/卡片/图片/语音 当前 skip + log;
  下一期可以加 sticker → emoji 翻译,图片 → 视觉理解。
- **不会用 lark thread_id / root_id 串上下文**。每条消息都是独立 hermes session
  (跟 voice 路径一样的限制)。
- **响应延迟 10-30s**: hermes cold spawn + DeepSeek thinking + lark API。比 IM
  自然体验差;答辩时跟 demo 用户明说"这是 LLM reasoning 时间"。

## 调试

```bash
# 长连接握手失败 (常见: app_id/secret 错 / 飞书后台没开长连接订阅 / 没发版)
grep -E 'ERROR|connect failed' /tmp/lark_listener.log | tail

# Listener 跑着但消息没触发 hermes (常见: 不是 p2p / message_type 不是 text)
grep 'skip event' /tmp/lark_listener.log | tail

# hermes 跑了但飞书没收回复 (常见: hermes 没调 tool,只 stdout 文本)
grep 'hermes done' /tmp/lark_listener.log | tail
# 然后 prompt-engineering 加强 prompt 让 hermes 必调 tool
```

## License

MIT. See [LICENSE](../LICENSE).
