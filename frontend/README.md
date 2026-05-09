# LangGraph Agent Frontend

This frontend is a TypeScript React thin client for `langgraph-agent-blueprint`.
It calls the FastAPI/LangGraph runtime and does not execute tools, own permission
policy, or duplicate graph workflow logic in the browser.

## Run

```bash
lg-agent serve --factory --host 127.0.0.1 --port 8000 --reload
npm install
npm run dev
```

Set a backend URL with:

```bash
set VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Architecture

- `src/api/`: typed HTTP and SSE clients for runtime endpoints.
- `src/runtime/`: event reducer, selectors, and view-model helpers.
- `src/components/`: presentation-only chat, approval, session, context,
  registry, and settings views.

The live chat path uses `POST /chat/stream` and parses Server-Sent Event
`StreamFrame` payloads. Approval uses `POST /approval` with typed
`PermissionDecisionDTO`.

The Settings view is a separate tabbed page. It is read-only for backend/runtime config and uses local-only
preferences for theme, density, event verbosity, debug-event visibility, and
auto-scroll. It uses `GET /mcp/snapshot` for passive MCP status so opening the
settings page does not start configured MCP stdio processes.
