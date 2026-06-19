# xiaozhi-mcp-adapter

H015 spike for the xinnan-tech MCP endpoint path.

```text
xinnan-tech server mock
  ws://<host>:8004/mcp_endpoint/mcp/?token=...
        |
        v
xiaozhi_mcp_adapter.pipe
        |
        v
stdio JSON-RPC
        |
        v
xiaozhi_mcp_adapter.echo_tool
  echo(text) -> "echoed: " + text
```

## Install

```bash
cd xiaozhi-mcp-adapter
pip install -e .[test]
```

## Run The Pipe

```bash
export MCP_ENDPOINT='ws://127.0.0.1:8004/mcp_endpoint/mcp/?token=<token>'
python -m xiaozhi_mcp_adapter.pipe
```

`MCP_ENDPOINT` is the only configuration for this spike. The pipe always
launches the bundled echo tool as its stdio MCP child.

## Run The Echo Tool

```bash
python -m xiaozhi_mcp_adapter.echo_tool
```

The tool speaks MCP over stdin/stdout and blocks waiting for client messages.

## Test

```bash
pytest -xvs tests/
```

The test starts a mock WebSocket endpoint, sends `initialize`, `tools/list`,
and `tools/call`, then verifies the `echoed: hi` response.

## Relation To H016

H015 proves the local pipe and stdio tool round-trip without Docker, ESP32, or
Hermes. H016 should replace the mock WebSocket endpoint with the real
xinnan-tech 8004 MCP endpoint and token.
