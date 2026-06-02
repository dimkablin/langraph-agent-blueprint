# Local full-stack Docker Compose

This stack is for manual local testing only. It starts the FastAPI backend, the built React frontend, Langfuse, and the local services Langfuse needs: Postgres, ClickHouse, Redis, and MinIO. All ports are bound to `127.0.0.1`. Real LLM provider keys may be supplied through an uncommitted local `.env`; never commit those secrets.

## Start

From the repository root:

```bash
cp .env.example .env
mkdir -p mounted-projects
docker compose -f docker-compose.local.yml up --build
```

`mounted-projects` is gitignored and mounted into the backend container at `/workspace`. Put or clone projects under that host directory, then enter `/workspace/<project-directory>` in the frontend project picker.

Wait until Compose reports the app containers as healthy or running, then open:

- Frontend: http://127.0.0.1:5173
- Backend API: http://127.0.0.1:8010
- Backend commands endpoint: http://127.0.0.1:8010/commands
- Langfuse UI: http://127.0.0.1:3002
- MinIO API: http://127.0.0.1:9090
- MinIO console: http://127.0.0.1:9091

By default, the backend runs with the fake LLM provider and local dummy Langfuse project keys. The matching Langfuse project/user are bootstrapped by the `langfuse-web` container for local use only.

## Real LLM credentials

Compose reads provider configuration from the project-root `.env` file. Keep `.env` uncommitted and set only the provider you want to test. Supported variables are the same ones read by the backend config: `LLM_PROVIDER`, `MODEL_NAME`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `OPENAI_COMPATIBLE_BASE_URL`, `OPENAI_COMPATIBLE_API_KEY`, `OPENAI_COMPATIBLE_MODEL`, `OLLAMA_BASE_URL`, and `OLLAMA_MODEL`.

OpenAI example with dummy placeholders:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-local-key-here
OPENAI_MODEL=gpt-4o-mini
MODEL_NAME=gpt-4o-mini
```

Anthropic example with dummy placeholders:

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-local-key-here
ANTHROPIC_MODEL=claude-3-5-haiku-latest
MODEL_NAME=claude-3-5-haiku-latest
```

OpenAI-compatible example with dummy placeholders:

```env
LLM_PROVIDER=openai_compatible
OPENAI_COMPATIBLE_BASE_URL=http://host.docker.internal:11434/v1
OPENAI_COMPATIBLE_API_KEY=not-needed
OPENAI_COMPATIBLE_MODEL=qwen3:14b
MODEL_NAME=qwen3:14b
```

After changing `.env`, recreate only the backend unless frontend code changed:

```bash
docker compose -f docker-compose.local.yml up -d --build --force-recreate backend
```

Verify non-secret effective provider variables without printing key values:

```bash
docker compose -f docker-compose.local.yml exec backend python - <<'PY'
import os
for name in ["LLM_PROVIDER", "MODEL_NAME", "OPENAI_MODEL", "ANTHROPIC_MODEL", "OPENAI_COMPATIBLE_BASE_URL", "OPENAI_COMPATIBLE_MODEL"]:
    print(f"{name}={os.getenv(name, '')}")
for name in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_COMPATIBLE_API_KEY"]:
    print(f"{name}=<set>" if os.getenv(name) else f"{name}=<unset>")
PY
```

## Project selection in Docker

The native OS folder picker (`POST /workspaces/pick`) is not available from the headless backend container. In Docker, use the path-entry flow in the frontend project menu instead:

1. Put or clone the host project under `mounted-projects` or set `LOCAL_PROJECTS_DIR` in `.env` to another host directory.
2. Recreate the backend if you changed `LOCAL_PROJECTS_DIR`.
3. Click the project selector and enter the container path, for example `/workspace/my-project`.

Do not enter a Windows host path such as `C:\Users\...` from inside the Docker UI; the backend can only see mounted container paths. The system folder-picker button is still shown for non-container/manual backends, but Docker users should expect the path-entry flow to work instead.

The compose frontend is built with `VITE_API_BASE_URL=http://127.0.0.1:8010`, so browser requests go to the host-mapped backend port. The root `.env.example` and `frontend/.env.example` use the same value for manual local frontend runs against this compose backend.

## Smoke checks

```bash
curl -f http://127.0.0.1:5173/
curl -f http://127.0.0.1:8010/commands
curl -f -X POST http://127.0.0.1:8010/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"hello from local compose"}'
curl -f http://127.0.0.1:3002/
```

After the `/chat` request, open Langfuse at http://127.0.0.1:3002 and check the local project for traces. Langfuse ingestion can lag by a few seconds.

## Logs

```bash
docker compose -f docker-compose.local.yml ps
docker compose -f docker-compose.local.yml logs -f backend frontend langfuse-web langfuse-worker
```

## Stop

```bash
docker compose -f docker-compose.local.yml down
```

This stops containers and preserves named volumes, including Langfuse data and `.storage` runtime state.

## Optional clean reset

Only run this when you intentionally want to delete local stack data:

```bash
docker compose -f docker-compose.local.yml down -v
```

No destructive cleanup is performed by default.

## Port conflicts

The compose file uses stable localhost ports:

- `5173` frontend
- `8010` backend API mapped to container `8000`
- `3002` Langfuse UI mapped to container `3000`
- `5432`, `6379`, `8123`, `9000`, `9090`, `9091` for local supporting services

If one is occupied, edit only the host-side port in `docker-compose.local.yml` and update this document for the new local URL.
