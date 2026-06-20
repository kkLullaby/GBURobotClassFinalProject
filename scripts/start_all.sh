#!/bin/bash
# ottagent 一键启动 — 复现完整 voice demo 链路
#
# 使用前提:
#   1. 手机开热点, 笔记本 + ESP32 OttoRobot 都连这个热点
#   2. ESP32 之前已经通过 BluFi 配过这个 SSID (否则要先 BluFi 配网)
#   3. clash-verge 在跑 (DeepSeek 走代理, lark feishu 走 NO_PROXY direct)
#   4. ~/.config/openai-shim/.env 含 DEEPSEEK_API_KEY (chmod 600)
#   5. ~/.config/lark-mcp/.env 含 LARK_APP_ID/SECRET/USER_MOBILE (chmod 600)
#
# 启动后对机器人讲话:
#   "你好"                       → hermes 路径, 喇叭说话
#   "挥挥手" / "转个圈"           → raw_deepseek 路径, 舵机真动
#   "给我发个飞书消息说一切正常"   → hermes 调 lark tool, 飞书真到
#
# 状态查看:
#   tail -f /tmp/shim.log
#   docker logs -f xiaozhi-esp32-server
#
# 停掉:
#   bash scripts/stop_all.sh    (或手动 pkill openai_shim + docker compose down)

set -u  # 注意: 不用 set -e, 单步失败要 报警但继续

# ──────────────────────────────────────────────────────────────────────
# 颜色 + 工具
# ──────────────────────────────────────────────────────────────────────
RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; BLU=$'\e[34m'; BOLD=$'\e[1m'; CLR=$'\e[0m'
ok()    { echo "${GRN}✅${CLR} $*"; }
warn()  { echo "${YEL}⚠️${CLR}  $*"; }
fail()  { echo "${RED}❌${CLR} $*"; }
info()  { echo "${BLU}→${CLR}  $*"; }
step()  { echo ""; echo "${BOLD}=== $* ===${CLR}"; }

# ──────────────────────────────────────────────────────────────────────
# 路径常量
# ──────────────────────────────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
XINNAN_DIR="$HOME/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server"
MCP_ENDPOINT_DIR="$HOME/code/xinnan-tech/mcp-endpoint-server"
SHIM_ENV="$HOME/.config/openai-shim/.env"
LARK_ENV="$HOME/.config/lark-mcp/.env"
XINNAN_CONFIG="$XINNAN_DIR/data/.config.yaml"

# ──────────────────────────────────────────────────────────────────────
# Step 1: pre-flight 检查
# ──────────────────────────────────────────────────────────────────────
step "Step 1/7 pre-flight 检查"

PREFLIGHT_OK=1

# 1a. docker
if ! command -v docker >/dev/null; then
  fail "docker 没装"; PREFLIGHT_OK=0
else ok "docker 在"; fi

# 1b. clash-verge (DeepSeek 走代理)
if ! pgrep -f verge-mihomo >/dev/null && ! pgrep -f clash >/dev/null; then
  warn "clash-verge / mihomo 没跑 — DeepSeek 调用可能因 fake-ip TLS 死 (bitter #45)"
  warn "    若发现 DeepSeek connection error, 先把 clash-verge 起来"
else ok "clash-verge 在跑"; fi

# 1c. hermes
if ! command -v hermes >/dev/null; then
  fail "hermes 没装 (uv tool install --force --with 'hermes-agent[mcp]' hermes-agent)"; PREFLIGHT_OK=0
else ok "hermes 在 ($(hermes --version 2>/dev/null | head -1))"; fi

# 1d. 两个 secret .env
if [ ! -f "$SHIM_ENV" ]; then
  fail "$SHIM_ENV 不存在"
  echo "    cat > $SHIM_ENV <<'EOF'"
  echo "    DEEPSEEK_API_KEY=sk-你的真key"
  echo "    EOF"
  echo "    chmod 600 $SHIM_ENV"
  PREFLIGHT_OK=0
else
  PERM=$(stat -c '%a' "$SHIM_ENV")
  if [ "$PERM" != "600" ]; then warn "$SHIM_ENV 权限 $PERM (建议 600): chmod 600 $SHIM_ENV"
  else ok "$SHIM_ENV (chmod 600)"; fi
fi

if [ ! -f "$LARK_ENV" ]; then
  warn "$LARK_ENV 不存在 — 飞书 channel 跑不了, voice/motor demo 仍可"
else
  PERM=$(stat -c '%a' "$LARK_ENV")
  if [ "$PERM" != "600" ]; then warn "$LARK_ENV 权限 $PERM (建议 600)"
  else ok "$LARK_ENV (chmod 600)"; fi
fi

# 1e. xinnan-tech docker compose
if [ ! -f "$XINNAN_DIR/docker-compose.yml" ]; then
  fail "找不到 xinnan-tech compose: $XINNAN_DIR/docker-compose.yml"; PREFLIGHT_OK=0
else ok "xinnan-tech compose"; fi

if [ ! -f "$MCP_ENDPOINT_DIR/docker-compose.yml" ]; then
  fail "找不到 mcp-endpoint compose: $MCP_ENDPOINT_DIR/docker-compose.yml"; PREFLIGHT_OK=0
else ok "mcp-endpoint compose"; fi

[ $PREFLIGHT_OK -eq 0 ] && { fail "pre-flight 不通过, 修上面 ❌ 项再来"; exit 1; }

# ──────────────────────────────────────────────────────────────────────
# Step 2: 检测笔记本当前 IP, 对比 xinnan-tech config 里的 ESP32 server URL
# ──────────────────────────────────────────────────────────────────────
step "Step 2/7 检测 IP + 同步 xinnan-tech config"

# wlp0s20f3 是这台机器的 wifi 接口名, 别的机器改这里
WIFI_IFACE=$(ip -4 -o addr show | awk '$2 ~ /^wl/ && $4 ~ /^[0-9]/ {print $2; exit}')
LAPTOP_IP=$(ip -4 -o addr show "$WIFI_IFACE" 2>/dev/null | awk '{print $4}' | cut -d/ -f1)

if [ -z "$LAPTOP_IP" ]; then
  fail "拿不到 wifi IP, 笔记本是否连上手机热点了?"
  exit 1
fi
ok "笔记本 IP: ${BOLD}$LAPTOP_IP${CLR} (iface $WIFI_IFACE)"

if [ -f "$XINNAN_CONFIG" ]; then
  CURRENT_WS_IP=$(grep -oE 'ws://[0-9.]+' "$XINNAN_CONFIG" | head -1 | sed 's|ws://||')
  if [ -n "$CURRENT_WS_IP" ] && [ "$CURRENT_WS_IP" != "$LAPTOP_IP" ]; then
    warn "xinnan-tech config 的 ws URL 是 $CURRENT_WS_IP, 现 IP 是 $LAPTOP_IP — 自动改"
    sed -i.bak "s|ws://$CURRENT_WS_IP|ws://$LAPTOP_IP|g" "$XINNAN_CONFIG"
    ok "改完 ($XINNAN_CONFIG.bak 备份)"
    XINNAN_NEEDS_RESTART=1
  elif [ "$CURRENT_WS_IP" = "$LAPTOP_IP" ]; then
    ok "xinnan-tech config ws URL 已匹配 ($LAPTOP_IP)"
    XINNAN_NEEDS_RESTART=0
  else
    warn "config 里没找到 ws://, 跳过"
    XINNAN_NEEDS_RESTART=0
  fi
else
  warn "$XINNAN_CONFIG 不存在 (容器没跑过?), 跳过"
  XINNAN_NEEDS_RESTART=0
fi

cat <<EOF

${YEL}⚠️  ESP32 固件烧写时的 OTA URL 也指向某个 IP, 通常是 http://$LAPTOP_IP:8003/xiaozhi/ota/${CLR}
    如果笔记本 IP 跟当时烧写时不一样, ESP32 boot 时 hit 不到 OTA 服务, 喇叭不响.
    解 = 给笔记本设固定 DHCP, 或让手机 hotspot 永远分配同一个 IP, 或重 BluFi 配
    不知道当时烧的 IP 是多少? 看 esp/xiaozhi-esp32/build/ 或 monitor 重启时 boot 日志.
EOF

# ──────────────────────────────────────────────────────────────────────
# Step 3: 启动 docker 容器 (mcp-endpoint + xiaozhi-esp32-server)
# ──────────────────────────────────────────────────────────────────────
step "Step 3/7 起 docker 容器"

# mcp-endpoint-server
if docker ps --format '{{.Names}}' | grep -q '^mcp-endpoint-server$'; then
  ok "mcp-endpoint-server 已在"
else
  info "起 mcp-endpoint-server..."
  (cd "$MCP_ENDPOINT_DIR" && docker compose up -d) || { fail "mcp-endpoint up 失败"; exit 1; }
  ok "mcp-endpoint-server up"
fi

# xiaozhi-esp32-server
if [ "${XINNAN_NEEDS_RESTART:-0}" = "1" ]; then
  info "config 改过, restart xiaozhi-esp32-server..."
  (cd "$XINNAN_DIR" && docker compose restart)
  sleep 5
  ok "xiaozhi-esp32-server restarted"
elif docker ps --format '{{.Names}}' | grep -q '^xiaozhi-esp32-server$'; then
  ok "xiaozhi-esp32-server 已在"
else
  info "起 xiaozhi-esp32-server..."
  (cd "$XINNAN_DIR" && docker compose up -d) || { fail "xiaozhi up 失败"; exit 1; }
  sleep 5
  ok "xiaozhi-esp32-server up"
fi

# 验端口
sleep 2
for p in 8000 8003 8004; do
  if ss -tln | grep -q ":$p "; then ok "port $p LISTEN"
  else fail "port $p 未 LISTEN"; fi
done

# ──────────────────────────────────────────────────────────────────────
# Step 4: 释放 mcp_endpoint slot (kill sidecar) — bitter lesson #32
# ──────────────────────────────────────────────────────────────────────
step "Step 4/7 释放 mcp_endpoint slot (#32)"

if pgrep -f xiaozhi_mcp_adapter >/dev/null; then
  pkill -9 -f xiaozhi_mcp_adapter
  sleep 1
  ok "killed xiaozhi_mcp_adapter (sidecar 抢 slot 会让 ESP32 注册不上 tools)"
else
  ok "无 sidecar 进程, slot clean"
fi

# ──────────────────────────────────────────────────────────────────────
# Step 5: 起 shim (hybrid mode)
# ──────────────────────────────────────────────────────────────────────
step "Step 5/7 起 openai-shim (hybrid)"

bash "$REPO_ROOT/scripts/start_shim.sh"
info "等 uvicorn import (≥3s, bitter #46)..."
sleep 4

if ss -tln | grep -q ':8089 '; then
  ok "port 8089 LISTEN"
  PID=$(pgrep -f 'openai_shim.app:app' | head -1)
  BACKEND=$(cat /proc/$PID/environ 2>/dev/null | tr '\0' '\n' | grep '^OPENAI_SHIM_BACKEND=' | cut -d= -f2)
  if [ "$BACKEND" = "hybrid" ]; then
    ok "shim backend = hybrid ✓"
  else
    fail "shim backend = '$BACKEND' (应是 hybrid) — 检查 scripts/start_shim.sh"
  fi
else
  fail "shim 没起, tail /tmp/shim.log:"
  tail -20 /tmp/shim.log
  exit 1
fi

# ──────────────────────────────────────────────────────────────────────
# Step 6: smoke (motor 路径不真发 voice, 走 HTTP)
# ──────────────────────────────────────────────────────────────────────
step "Step 6/7 smoke (motor 路径 + hermes 路径各 1 发)"

info "motor smoke: '挥挥手' → 期望 DeepSeek stream chunk"
RESP=$(timeout 20 curl -sS -N -X POST http://localhost:8089/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-v4-pro","stream":true,"messages":[{"role":"user","content":"挥挥手"}]}' 2>&1 | head -1)

if echo "$RESP" | grep -q 'reasoning_content\|choices'; then
  ok "motor → DeepSeek 真 stream chunk ✓"
elif echo "$RESP" | grep -q 'echoed:'; then
  fail "shim 还是 echo 模式! backend env 没注入"
elif echo "$RESP" | grep -q 'deepseek_upstream'; then
  warn "DeepSeek API 不通 — 看是 key 错 还是 proxy/fake-ip 问题:"
  echo "    $RESP" | head -c 200
else
  warn "smoke 没收到识别 chunk, 看 /tmp/shim.log:"
  echo "    $RESP" | head -c 200
fi

# ──────────────────────────────────────────────────────────────────────
# Step 7: 完成 + cheatsheet
# ──────────────────────────────────────────────────────────────────────
step "Step 7/7 全部就绪!"

cat <<EOF

${GRN}${BOLD}对机器人讲话测试:${CLR}
  ${BOLD}"你好小智, 你好"${CLR}
       → shim [hybrid] route=hermes_agent
       → hermes -z → 喇叭说话
  ${BOLD}"挥挥手"${CLR}  or  ${BOLD}"转个圈"${CLR}
       → shim [hybrid] route=raw_deepseek + tools 透传
       → DeepSeek 返 tool_calls=[self_otto_action] → ESP32 舵机真动
  ${BOLD}"给我发个飞书消息说一切正常"${CLR}
       → hermes 调 lark_send_message_to_self → 飞书真到 (~30-60s)
       → 喇叭说 "已发送"

${BLU}${BOLD}实时观察:${CLR}
  tail -f /tmp/shim.log                              # shim 路由日志
  docker logs -f --tail 20 xiaozhi-esp32-server      # ESP32 ↔ server 对话
  docker logs -f --tail 20 mcp-endpoint-server       # tool dispatch

${BLU}${BOLD}停掉:${CLR}
  bash $REPO_ROOT/scripts/stop_all.sh

${YEL}本次 IP: $LAPTOP_IP   (ESP32 → $LAPTOP_IP:8000/xiaozhi/v1/)${CLR}
EOF
