# openai-shim

H018 spike for the OpenAI-compatible transcript entrypoint.

```text
xiaozhi-server / OpenAI SDK
  POST /v1/chat/completions stream=true
        |
        v
openai_shim.app FastAPI
        |
        v
echo_backend.stream_response()
        |
        v
SSE ChatCompletionChunk events
```

## Install

```bash
cd openai-shim
UV_CACHE_DIR=/tmp/uv-cache uv pip install --system -e '.[test]'
```

## Run

```bash
/home/kk/miniconda3/bin/python -m uvicorn openai_shim.app:app --port 8089
```

## Curl Smoke

```bash
curl -N -X POST http://localhost:8089/v1/chat/completions \
  -H 'Authorization: Bearer fake' \
  -H 'Content-Type: application/json' \
  -d '{"model":"echo","messages":[{"role":"user","content":"hi"}],"stream":true}'
```

Expected output is `data: {...}` SSE chunks ending with `data: [DONE]`.

## Test

```bash
/home/kk/miniconda3/bin/python -m pytest -xvs tests/
```

The tests use the real OpenAI Python SDK client against the ASGI app.

## Relation To H019

H018 only proves an OpenAI-compatible streaming surface. H019 should fork the
request transcript and final assistant text to Hermes per ADR-0005, replacing
only the backend path while keeping the FastAPI and SSE surface stable.

## H019 Hermes Fork

```bash
export HERMES_TRANSCRIPT_URL='http://localhost:8088/webhooks/xiaozhi-transcript'
hermes webhook subscribe xiaozhi-transcript \
  --prompt 'User said: {user}. Assistant replied: {assistant}.' \
  --description 'XiaoZhi robot transcript ingress (H019)' \
  --deliver-only
```

When the env var is set, the shim posts `{user, assistant, model, session,
timestamp_unix}` to Hermes after each streamed response. The fork is
fire-and-forget: Hermes failures are logged and do not break the SSE response.

## H021 DeepSeek Backend

Backend selection is explicit:

```bash
OPENAI_SHIM_BACKEND=echo                  # default
OPENAI_SHIM_BACKEND=deepseek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
HERMES_TRANSCRIPT_URL=http://localhost:8088/webhooks/xiaozhi-transcript
```

Example smoke with a placeholder key:

```bash
OPENAI_SHIM_BACKEND=deepseek DEEPSEEK_API_KEY=sk-... \
  /home/kk/miniconda3/bin/python -m uvicorn openai_shim.app:app --port 8089
curl -N -X POST http://localhost:8089/v1/chat/completions \
  -H "Authorization: Bearer fake" -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"用一句话介绍你自己"}],"stream":true}'
```

H022 should run the end-to-end path: DeepSeek backend plus Hermes fork plus ESP32 voice.
