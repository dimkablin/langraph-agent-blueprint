# React CLI Frontend

The frontend is a React browser implementation of a CLI-like assistant surface.

## Scope

- Terminal-style transcript and input.
- Slash command hints.
- Tool hints.
- Skill hints.
- Keyboard/input hints.
- Runtime status bar with session/thread ids.
- Permission prompt with approve/reject actions.
- Calls only graph-facing API endpoints.

The frontend does not call tools or services directly. It calls:

- `POST /chat`
- `POST /approval`
- `GET /commands`
- `GET /skills`
- `GET /tools`

## Files

- `frontend/package.json`
- `frontend/index.html`
- `frontend/src/main.jsx`
- `frontend/src/App.jsx`
- `frontend/src/components.jsx`
- `frontend/src/api.js`
- `frontend/src/commandHints.js`
- `frontend/src/styles.css`
- `frontend/tests/frontend-static.test.mjs`

## Run

Start the Python API:

```bash
uvicorn claude_code_langgraph.api.server:create_app --factory --host 127.0.0.1 --port 8000
```

Start the React app:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Build:

```bash
npm --prefix frontend run build
```

Static frontend check:

```bash
npm --prefix frontend run test:static
```

## Permission Flow

When the graph interrupts for a risky tool, `/chat` returns `permission_required` and `thread_id`. The frontend shows a permission bar. Approve/reject calls `/approval`, which resumes the same LangGraph checkpoint.

## Design Notes

This is a dense operational interface, not a landing page. It keeps the Claude Code-like behavior visible as terminal transcript, command hints, tools, skills, and permission events.
