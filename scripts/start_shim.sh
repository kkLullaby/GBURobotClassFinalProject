#!/bin/bash
# Start openai-shim in hybrid mode.
#
# Secrets live OUTSIDE the repo (chmod 600):
#   ~/.config/openai-shim/.env   — DEEPSEEK_API_KEY
#   ~/.config/lark-mcp/.env      — LARK_*  (inherited by hermes subprocess)
#
# Proxy notes (bitter lesson #35 + clash-verge quirk):
# - clash-verge sets `all_proxy=socks://...` (bare scheme, httpx rejects).
# - We strip BOTH cases, then re-export with explicit `socks5://`.
# - `NO_PROXY=open.feishu.cn,open.larksuite.com` so feishu calls go DIRECT
#   (bitter lesson #36/#37).

set -e

# Kill any existing shim
pkill -9 -f 'openai_shim.app:app' 2>/dev/null || true
sleep 2

cd "$(dirname "$0")/../openai-shim"

# Load lark env so hermes subprocess sees LARK_*
if [ -f ~/.config/lark-mcp/.env ]; then
  set -a; source ~/.config/lark-mcp/.env; set +a
fi

# Load shim secrets (DEEPSEEK_API_KEY)
if [ ! -f ~/.config/openai-shim/.env ]; then
  echo "ERROR: ~/.config/openai-shim/.env missing — create it with DEEPSEEK_API_KEY=sk-..."
  exit 1
fi
set -a; source ~/.config/openai-shim/.env; set +a

# Wipe inherited proxy env (both cases — httpx prefers lowercase)
unset all_proxy http_proxy https_proxy no_proxy
unset ALL_PROXY HTTP_PROXY HTTPS_PROXY NO_PROXY

# Re-export with valid scheme (socks5:// not bare socks://)
export ALL_PROXY=socks5://127.0.0.1:7897
export HTTPS_PROXY=http://127.0.0.1:7897
export HTTP_PROXY=http://127.0.0.1:7897
export NO_PROXY="localhost,127.0.0.1,open.feishu.cn,open.larksuite.com"

export OPENAI_SHIM_BACKEND=hybrid
export HERMES_AGENT_TIMEOUT_S=300

nohup /home/kk/miniconda3/bin/python -m uvicorn \
  openai_shim.app:app --host 0.0.0.0 --port 8089 --log-level info \
  > /tmp/shim.log 2>&1 &
disown
echo "shim started PID=$!  (log: /tmp/shim.log)"
