---
id: 2026-06-20-lark-inbound-channel-039
from: planner
to: user
parent: 2026-06-20-shim-startup-script-038
status: done
created: 2026-06-20
artifacts:
  - lark-event-listener/ (新增独立 Python 包)
  - scripts/start_lark_listener.sh
  - docs/adr/0009-lark-inbound-long-connection.md
---

## Objective

补齐飞书 channel 的入口方向:用户在飞书 ottagent app 私聊机器人,机器人通过
hermes-z + lark tool **真回**。把 ADR-0008 (outbound only) 闭环成双向 channel。

## D1 spike 前置 (planner 做)

`xiaozhi_say` MCP tool (飞书消息 → 物理喇叭说话) **未实现**。D1 spike 发现
`mcp-endpoint-server /call/` 是 WebSocket 端点而非 HTTP POST,xinnan-tech 主
server 也没暴露主动 TTS 入口,改 xinnan-tech 上游代码 out of scope。所以本期
只做飞书 ↔ 飞书 单向闭环,物理喇叭不响。详见 ADR-0009 "D1 spike 结论"。

## What planner did (代码侧已完成)

| File | 行数 | 状态 |
|---|---|---|
| `lark-event-listener/pyproject.toml` | 34 | ✅ |
| `lark-event-listener/src/lark_event_listener/__init__.py` | 9 | ✅ |
| `lark-event-listener/src/lark_event_listener/handler.py` | ~180 | ✅ dedup + filter + spawn |
| `lark-event-listener/src/lark_event_listener/main.py` | ~110 | ✅ lark_oapi.ws.Client wiring |
| `lark-event-listener/tests/conftest.py` | ~18 | ✅ proxy unset fixture |
| `lark-event-listener/tests/test_handler.py` | ~170 | ✅ 14/14 PASS in 0.06s |
| `lark-event-listener/README.md` | ~120 | ✅ |
| `scripts/start_lark_listener.sh` | ~45 | ✅ |
| `scripts/start_all.sh` | (改) +25 | ✅ 加 Step 6/8 起 listener |
| `scripts/stop_all.sh` | (改) +5 | ✅ 加 pkill lark_event_listener |
| `docs/adr/0009-lark-inbound-long-connection.md` | ~140 | ✅ |
| `docs/adr/INDEX.md` | (改) +1 | ✅ |

**pytest**: `14/14 PASS in 0.06s`,覆盖 dedup / sender filter (app + open_id) /
chat_type / message_type / dedup LRU 淘汰 / hermes 失败不抛 / 空文本 skip。

## What user needs to do

### Phase 0 — 飞书开放平台后台 (~3 min, 一次性)

1. 打开 <https://open.feishu.cn/> → 进 ottagent app → 左侧 **"事件与回调"**
2. **"事件订阅"** → 添加 → 搜 `接收消息 v2.0` (`im.message.receive_v1`) → 添加
3. 同页 **"事件订阅方式"** → 切到 **"使用长连接接收"**
4. 左侧 **"版本管理与发布"** → 创建新版本 → 提交 → 管理员同意

### Phase 1 — 装 + 单测
```bash
cd /home/kk/code/robot_class/final_pro_xiaozhi_robot/lark-event-listener
UV_CACHE_DIR=/tmp/uv-cache uv pip install --system -e '.[test]'
pyx -m pytest -xvs tests/
# 期望: 14/14 PASS
```

### Phase 2 — 起 listener (单独)
```bash
bash ../scripts/start_lark_listener.sh
tail -f /tmp/lark_listener.log
# 期望 ~5s 内: "lark_event_listener starting (long-connection)..."
# 然后 lark_oapi 输出 "connected" 之类
```

### Phase 3 — 飞书 → 飞书 端到端验
打开飞书 → 找 ottagent app 私聊 → 发文本 `"你好 ottagent 自检"`

期望 timeline:
1. `/tmp/lark_listener.log` 立刻多一行 `received from ou_xxx (chat=oc_xxx msg_id=om_xxx): 你好 ottagent 自检`
2. 下一行 `spawn hermes: hermes -z ...`
3. ~10-30s 后 `hermes done (rc=0). stdout_head=...`
4. 飞书私聊收到 ottagent 的回复 (内容由 hermes 拟)

### Phase 4 — 一键启停 (含 voice 链路同时活)
```bash
bash scripts/start_all.sh    # Step 6/8 自动起 lark listener
bash scripts/stop_all.sh     # 一并杀干净
```

## Acceptance Criteria
- [x] (机器侧) lark-event-listener pytest 14/14 PASS
- [x] (机器侧) start_lark_listener.sh 起得来,无 set -e 红
- [x] (机器侧) stop_all.sh 能干净杀 lark_event_listener
- [ ] (用户侧) Phase 0 飞书后台长连接订阅开通
- [ ] (用户侧) Phase 2 listener 启动 log 见 "connected"
- [ ] (用户侧) Phase 3 飞书发 "你好" → 飞书收 ottagent 回复
- [ ] (用户侧) Phase 4 start_all.sh 全 8 step 通,inbound + voice 两条线并存

## Bitter lessons absorbed (#48-#50, 见 ADR-0009)

- **#48**: `mcp-endpoint-server /call/` 是 ws 端点,不是 HTTP POST;路径名
  同形不同义,看 README 不够,必须 grep `@app.websocket` 确认。
- **#49**: 飞书长连接模式不需要 ENCRYPT_KEY / VERIFICATION_TOKEN (那是
  webhook 的);.env 不要照搬 webhook 教程乱加 key。
- **#50**: 飞书 SDK callback 是 sync `Callable[[Event], None]`,async handler
  必须 `loop.create_task(...)` 调度,不能直接 await。

## Out of scope (留下一期)

- 飞书群聊接入 (策略未定:@mention only?)
- 飞书 → 物理 ESP32 喇叭说话 (D1 spike 砍;需要决定怎么绕开 xinnan-tech 限制)
- 飞书富文本/图片/语音 message_type 处理
- 多轮上下文 (lark thread_id → hermes session 串)
- ESP32 主动 push 飞书 (PIR / 摄像头 → lark) → 真正的 channel 第 3 阶段
