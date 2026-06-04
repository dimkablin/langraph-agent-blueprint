import assert from "node:assert/strict";
import test from "node:test";

import { archiveConversation, deleteConversation, fetchConversationDetail, fetchConversations, renameConversation } from "../src/api/conversations.ts";

test("conversation history API uses user-scoped conversation endpoints", async () => {
  const calls: { url: string; init: RequestInit }[] = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    if (String(url).endsWith("/conversations/conversation_1")) {
      return jsonResponse({
        conversation: {
          conversation_id: "conversation_1",
          session_id: "conversation_1",
          thread_id: "conversation_1",
          user_id: "dev-user",
          title: "Hello",
          status: "active",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
          metadata: {},
          schema_version: 1,
        },
        messages: [{ message_id: "msg_1", role: "user", content: "Hello", created_at: "2026-01-01T00:00:00Z" }],
        events: [],
        tool_calls: [],
        artifacts: [],
      });
    }
    return jsonResponse([
      {
        conversation_id: "conversation_1",
        session_id: "conversation_1",
        thread_id: "conversation_1",
        title: "Hello",
        status: "active",
        message_count: 1,
        event_count: 0,
        tool_call_count: 0,
        artifact_count: 0,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ]);
  };

  try {
    const list = await fetchConversations();
    const detail = await fetchConversationDetail("conversation_1");

    assert.equal(list[0].session_id, "conversation_1");
    assert.equal(detail.messages[0].id, "msg_1");
    assert.equal(calls[0].url, "http://127.0.0.1:8000/conversations");
    assert.equal((calls[0].init.headers as Record<string, string>)["X-User-Id"], "dev-user");
    assert.equal(calls[1].url, "http://127.0.0.1:8000/conversations/conversation_1");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("conversation history actions call rename archive and delete routes", async () => {
  const calls: { url: string; init: RequestInit }[] = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    if (init.method === "DELETE") {
      return new Response(null, { status: 204 });
    }
    return jsonResponse({
      conversation_id: "conversation_1",
      session_id: "conversation_1",
      thread_id: "conversation_1",
      user_id: "dev-user",
      title: "Renamed",
      status: "active",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      metadata: {},
      schema_version: 1,
    });
  };

  try {
    await renameConversation("conversation_1", "Renamed");
    await archiveConversation("conversation_1");
    await deleteConversation("conversation_1");

    assert.equal(calls[0].url, "http://127.0.0.1:8000/conversations/conversation_1");
    assert.equal(calls[0].init.method, "PATCH");
    assert.deepEqual(JSON.parse(String(calls[0].init.body)), { title: "Renamed" });
    assert.equal(calls[1].url, "http://127.0.0.1:8000/conversations/conversation_1/archive");
    assert.equal(calls[1].init.method, "POST");
    assert.equal(calls[2].url, "http://127.0.0.1:8000/conversations/conversation_1");
    assert.equal(calls[2].init.method, "DELETE");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), { status: 200, headers: { "Content-Type": "application/json" } });
}
