#!/bin/bash
# ottagent 一键停 — 配套 start_all.sh

set -u

RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; CLR=$'\e[0m'
ok()   { echo "${GRN}✅${CLR} $*"; }
warn() { echo "${YEL}⚠️${CLR}  $*"; }

XINNAN_DIR="$HOME/code/xinnan-tech/xiaozhi-esp32-server/main/xiaozhi-server"
MCP_ENDPOINT_DIR="$HOME/code/xinnan-tech/mcp-endpoint-server"

# 1. shim
if pgrep -f 'openai_shim.app:app' >/dev/null; then
  pkill -9 -f 'openai_shim.app:app'
  ok "killed shim"
else warn "shim 没在跑"; fi

# 2. lark-event-listener (飞书 inbound)
if pgrep -f 'lark_event_listener.main' >/dev/null; then
  pkill -9 -f 'lark_event_listener.main'
  ok "killed lark_event_listener"
fi

# 3. sidecar (若有)
if pgrep -f xiaozhi_mcp_adapter >/dev/null; then
  pkill -9 -f xiaozhi_mcp_adapter
  ok "killed sidecar"
fi

# 3. docker (默认只 stop, 不 down, 保留 volumes/network 下次秒起)
if [ "${1:-}" = "--down" ]; then
  (cd "$XINNAN_DIR" && docker compose down 2>/dev/null)
  (cd "$MCP_ENDPOINT_DIR" && docker compose down 2>/dev/null)
  ok "docker compose down (含 volumes 清理)"
else
  (cd "$XINNAN_DIR" && docker compose stop 2>/dev/null)
  (cd "$MCP_ENDPOINT_DIR" && docker compose stop 2>/dev/null)
  ok "docker compose stop (容器保留, 下次 start_all.sh 秒起)"
  warn "要彻底清掉容器: bash $0 --down"
fi

echo ""
ok "停妥. 重启: bash $(dirname "$0")/start_all.sh"
