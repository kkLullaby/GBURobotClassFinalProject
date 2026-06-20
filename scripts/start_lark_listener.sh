#!/bin/bash
# Start the lark-event-listener (long-connection client).
#
# Secrets in ~/.config/lark-mcp/.env (chmod 600): LARK_APP_ID/SECRET/USER_MOBILE/HOST
#
# Proxy: feishu open.feishu.cn is a domestic endpoint that the clash fake-ip
# pool resolves to 28.0.0.7 — must go direct. Same NO_PROXY trick as shim
# (bitter lesson #45). The listener itself only talks to feishu, so we can
# safely unset all proxy vars rather than route them.

set -e

# Kill any existing listener
pkill -9 -f 'lark_event_listener.main' 2>/dev/null || true
sleep 2

if [ ! -f ~/.config/lark-mcp/.env ]; then
  echo "ERROR: ~/.config/lark-mcp/.env missing — see lark-mcp-server/README.md"
  exit 1
fi
set -a; source ~/.config/lark-mcp/.env; set +a

# Wipe all proxy env (both cases). Listener only contacts feishu.
unset all_proxy http_proxy https_proxy no_proxy
unset ALL_PROXY HTTP_PROXY HTTPS_PROXY NO_PROXY

# Make sure hermes subprocess inherits the rest of env correctly
export LARK_ENV_FILE="$HOME/.config/lark-mcp/.env"
# Optional: how long to wait for hermes to finish before killing it
export LARK_LISTENER_HERMES_TIMEOUT_S="${LARK_LISTENER_HERMES_TIMEOUT_S:-180}"

nohup /home/kk/miniconda3/bin/python -m lark_event_listener.main \
  > /tmp/lark_listener.log 2>&1 &
disown
echo "lark_event_listener started PID=$!  (log: /tmp/lark_listener.log)"
echo ""
echo "Watch:"
echo "  tail -f /tmp/lark_listener.log"
echo ""
echo "Expect within ~5s:"
echo "  ... lark_event_listener.main: lark_event_listener starting (long-connection)..."
echo "  ... lark_oapi: connected ..."
