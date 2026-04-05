# AI Backend Engine

Model-agnostic AI job queue built on FastAPI, Dramatiq, Redis, and PostgreSQL.
Drop-in async job queue for any AI workload — swap providers without changing your API calls.

## Architecture

```
Client → POST /ai/jobs → FastAPI → Redis (Dramatiq broker) → Worker → ProviderRouter → AI Provider
                                                                                              ↓
Client ← GET /ai/jobs/{id} ←──────────────────────────────────────────────── Postgres (result)
```

Four Railway services: `api`, `worker`, `redis`, `postgres`.

## Supported providers

| Provider | Env var | Default model |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-haiku-4-5` |
| Google Gemini | `GEMINI_API_KEY` | `gemini-2.5-flash` |
| Ollama (self-hosted) | `OLLAMA_BASE_URL` | `llama3.2` |

Set `AI_PROVIDERS=openai,anthropic` to try OpenAI first, fall back to Anthropic automatically.

## Local development

```bash
cp .env.example .env
# Edit .env — add at least one provider API key
docker-compose up
```

## API

### Submit a job

```bash
curl -X POST http://localhost:8000/ai/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Summarise the benefits of async programming"}'
```

Response `202 Accepted`:
```json
{"job_id": "uuid", "status": "pending", "created_at": "2026-01-01T00:00:00Z"}
```

### Poll for result

```bash
curl http://localhost:8000/ai/jobs/{job_id}
```

Response when completed:
```json
{
  "job_id": "uuid",
  "status": "completed",
  "result": "...",
  "provider_used": "openai",
  "model_used": "gpt-4o-mini",
  "tokens_used": 312,
  "created_at": "...",
  "completed_at": "..."
}
```

### Health check

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok", "providers": {"openai": true}, "redis": true, "database": true}
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `AI_PROVIDERS` | `openai` | Ordered provider list, tried left to right |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama base URL |
| `DATABASE_URL` | — | PostgreSQL connection string (injected by Railway) |
| `REDIS_URL` | — | Redis connection string (injected by Railway) |
| `API_KEYS` | _(empty = no auth)_ | Comma-separated list of valid API keys |
| `WEBHOOK_SECRET` | — | HMAC secret for `X-Webhook-Signature` header |
| `WEBHOOK_TIMEOUT_SECONDS` | `10` | Webhook HTTP timeout |
| `RESULT_CACHE_TTL_SECONDS` | `3600` | Redis result cache TTL |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `60` | Per-API-key rate limit |

## Webhook callbacks

Set `callback_url` in your job request. On completion the engine POSTs:

```json
{
  "job_id": "uuid",
  "status": "completed",
  "result": "...",
  "provider_used": "openai",
  "tokens_used": 312
}
```

If `WEBHOOK_SECRET` is set, an `X-Webhook-Signature` HMAC-SHA256 header is included.
