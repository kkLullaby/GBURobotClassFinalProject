# hermes-xiaozhi-plugin

M3 Stage A plugin skeleton for XiaoZhi (ESP32-S3 OttoRobot) as a first-class
Hermes Agent platform. It follows ADR-0005: transcripts enter Hermes through
the M2 `openai-shim` signed webhook path, while reverse sends are prepared to
go through M1 and the ESP32 `self.otto.show_text` tool.

## Install

Development install into Hermes' user plugin directory is left for H028.bis.
The expected shape is:

```bash
mkdir -p ~/.hermes/plugins
ln -s "$(realpath hermes-xiaozhi-plugin/src/hermes_xiaozhi)" \
  ~/.hermes/plugins/xiaozhi
```

Then run `hermes gateway run` in the H028.bis user-led verification step.

## Env Vars

| name | required | purpose |
|---|---|---|
| `XIAOZHI_WEBHOOK_PORT` | yes | Incoming webhook port, default `8645` |
| `XIAOZHI_WEBHOOK_SECRET` | yes | HMAC secret shared with M2 `openai-shim` |
| `XIAOZHI_DEVICE_ID` | no | Default ESP32 MAC, for example `ac:a7:04:30:91:78` |
| `XIAOZHI_MCP_ADAPTER_URL` | no | M1 reverse send endpoint; disabled when unset |

## Current Limits

Stage A does not install the plugin, run Hermes, or listen for webhooks.
`connect()` is a stub. `send()` returns success without an M1 URL and, when
`XIAOZHI_MCP_ADAPTER_URL` is set, POSTs to `/tools/show_text` with
`{"device_id", "text", "kind": "chat"}` while keeping failures non-fatal.

## Stage B/C TODO

- H028.bis: install into `~/.hermes/plugins/xiaozhi` and verify
  `hermes gateway run` registers platform `xiaozhi`.
- H028.bis: point M2 `HERMES_TRANSCRIPT_URL` at the XiaoZhi adapter webhook.
- H029: add the M1 `show_text_proxy` path and replace stub reverse send with
  the real ESP32 display call chain.

## Test

```bash
PYTHONPATH="$HOME/.local/share/uv/tools/hermes-agent/lib/python3.13/site-packages" \
  /home/kk/miniconda3/bin/python -m pytest -xvs tests/
```
