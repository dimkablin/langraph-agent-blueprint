# Persistent multi-user conversation history

This project now has a user-scoped conversation persistence layer for ChatGPT-like chat history. The feature is intentionally backend-first: API routes and services enforce ownership, while the frontend consumes only the current user's conversation list.

## Architecture overview

- `ConversationService` is the service boundary for history use cases. Every public method requires `user_id` first so access control is enforced before reads or writes.
- `SQLiteConversationStorage` is the local/dev durable backend. It stores normalized records in `storage_dir/conversations.sqlite3` and exposes a repository-shaped API that can be replaced by a PostgreSQL implementation without changing FastAPI routes or React components.
- Existing `SessionStorage` remains available for legacy session artifacts and local development flows. Conversation history is a separate normalized store and does not mix memory records into raw chat history.
- Chat endpoints create or load a conversation before invoking LangGraph. The conversation id is also the `session_id`; `thread_id` is enforced from the conversation record, giving a stable mapping for resume/reload flows instead of trusting client-generated thread ids.
- Streaming runs batch durable writes at turn completion: user message, final assistant message, important stream events, tool calls, and artifact references can be appended in one storage transaction.

## Data model summary

SQLite tables are initialized automatically on startup:

- `users`: `user_id`, display/timestamp metadata.
- `conversations`: `conversation_id`, `session_id`, `thread_id`, `user_id`, `project_id`, title, active/archive/delete state, timestamps, metadata JSON, schema version.
- `messages`: normalized ordered messages with role/content/idempotency keys and metadata JSON.
- `stream_events`: ordered runtime/progress events keyed by `(conversation_id, event_id)` for deduplication.
- `tool_calls`: ordered tool call/result payloads with idempotency keys. Known secret-bearing keys are redacted before persistence.
- `artifacts`: persisted artifact references, not raw files.
- `checkpoint_refs`: reserved for durable LangGraph checkpoint references.

Indexes cover user conversation lists, conversation message/event ordering, and idempotency constraints.

## User scoping

The API boundary reads the current dev-mode user from `X-User-Id`. If the header is omitted, local development falls back to `dev-user`. Empty user ids return `401`; overly long ids return `400`.

All conversation APIs pass this user id into `ConversationService`, and storage queries include both `conversation_id` and `user_id`. Cross-user reads, renames, archives, deletes, and appends return `404` so another user's conversation existence is not disclosed.

The React API client sends `X-User-Id` on conversation, chat, stream, workspace, and other JSON requests. The browser stores the dev user id in `localStorage` key `langgraph-agent-blueprint:user-id`; node tests and non-browser environments fall back to `dev-user`.

## API routes

- `GET /conversations`: list active conversations for the current user. Query params: `include_archived`, `q`, `limit`.
- `POST /conversations`: create a conversation with optional title/project/thread metadata.
- `GET /conversations/{conversation_id}`: load conversation metadata, messages, events, tool calls, and artifacts.
- `PATCH /conversations/{conversation_id}`: rename a conversation.
- `POST /conversations/{conversation_id}/archive`: archive a conversation so it is hidden from normal lists.
- `DELETE /conversations/{conversation_id}`: soft-delete a conversation.
- `POST /conversations/{conversation_id}/messages`: append an idempotent turn/messages/events batch.
- `POST /chat` and `POST /chat/stream`: create or continue a persisted conversation, then run the graph. Use `session_id` to continue an existing conversation.

Example:

```bash
curl -H 'X-User-Id: alice' http://127.0.0.1:8000/conversations
curl -H 'X-User-Id: alice' -H 'Content-Type: application/json' \
  -d '{"message":"continue this chat","session_id":"session_..."}' \
  http://127.0.0.1:8000/chat/stream
```

## Local SQLite and production PostgreSQL path

Local/dev requires no migration command; `SQLiteConversationStorage` creates `conversations.sqlite3` under the configured storage directory.

For production, use the same schema shape in PostgreSQL and wire a PostgreSQL repository implementation behind `ConversationService`. Table names, constraints, and indexes should mirror `SCHEMA_SQL` in `src/langgraph_agent_blueprint/storage/conversation_storage.py`; translate JSON text columns to `jsonb`, timestamp text columns to `timestamptz`, and `INSERT OR IGNORE`/SQLite conflict clauses to PostgreSQL `ON CONFLICT DO NOTHING`.

Recommended PostgreSQL constraints/indexes:

- `conversations(user_id, deleted_at, archived_at, updated_at DESC)`
- unique `conversations(user_id, thread_id)`
- `messages(conversation_id, order_index)`
- unique partial `messages(conversation_id, idempotency_key) WHERE idempotency_key IS NOT NULL`
- primary key or unique `(conversation_id, event_id)` on `stream_events`
- unique partial `tool_calls(conversation_id, idempotency_key) WHERE idempotency_key IS NOT NULL`

## Frontend behavior

The sidebar now loads the user-scoped `/conversations` list instead of legacy global sessions. It supports:

- new chat;
- active conversation selection;
- conversation reload after page refresh via the persisted active session id;
- title display;
- simple rename/archive/delete actions;
- empty/error states;
- local query filtering for visible conversations.

Because backend routes are user-scoped, frontend filtering is not the security boundary.

## Idempotency, streaming durability, and redaction

- Message and tool call writes support idempotency keys.
- Stream events are deduplicated by `(conversation_id, event_id)`.
- `append_turn` writes the turn batch in one transaction and updates conversation timestamps after durable append.
- Known secret keys (`api_key`, `authorization`, `access_token`, `refresh_token`, `token`, `password`, `secret`, etc.) are redacted recursively before durable tool/event/message metadata storage.
- Very large raw graph state is not exposed to the frontend. LangGraph checkpoint references have a dedicated table, but a full PostgreSQL-backed checkpointer remains a separate production hardening step.

## Verification commands

```bash
pytest tests/test_conversation_persistence.py tests/test_conversation_api_contract.py
cd frontend && npm test -- conversations-api.test.ts
python scripts/measure_conversation_persistence.py
```

## Benchmark

Run:

```bash
python scripts/measure_conversation_persistence.py
```

The benchmark simulates 100 users, two conversations per user, and two turns per conversation through `ConversationService`. It reports read/write call counts, per-turn call deltas, and p50/p95 latency for create, append, list, and get operations.

## Known limitations

- The production PostgreSQL backend is documented as a porting path; this slice ships the swappable service boundary and durable SQLite backend.
- Completed-turn history survives server/page reload through the normalized conversation store. Full interrupted LangGraph checkpoint resume still depends on adding a durable checkpointer implementation.
- Tool calls/artifacts are persisted when surfaced through the conversation append path; existing legacy `SessionStorage` artifacts remain available separately.
