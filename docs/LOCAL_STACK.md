# Local full-stack Docker Compose

This stack is for manual local testing only. It starts the FastAPI backend, the built React frontend, Langfuse, and the local services Langfuse needs: Postgres, ClickHouse, Redis, and MinIO. All ports are bound to `127.0.0.1`; no production services or real provider keys are used.

## Start

From the repository root:

```bash
docker compose -f docker-compose.local.yml up --build
```

Wait until Compose reports the app containers as healthy or running, then open:

- Frontend: http://127.0.0.1:5173
- Backend API: http://127.0.0.1:8010
- Backend commands endpoint: http://127.0.0.1:8010/commands
- Langfuse UI: http://127.0.0.1:3002
- MinIO API: http://127.0.0.1:9090
- MinIO console: http://127.0.0.1:9091

The backend runs with the fake LLM provider and local dummy Langfuse project keys. The matching Langfuse project/user are bootstrapped by the `langfuse-web` container for local use only.

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
