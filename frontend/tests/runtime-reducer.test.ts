import assert from "node:assert/strict";
import test from "node:test";

import { applyRuntimeEvent, applyStreamFrame, createInitialRuntimeState, markStreamingStopped } from "../src/runtime/reducer.ts";
import type { RuntimeEvent } from "../src/api/schemas.ts";

function event(type: string, data: Record<string, unknown> = {}): RuntimeEvent {
  return {
    id: `event_${type}`,
    type,
    timestamp: "2026-05-08T00:00:00Z",
    session_id: "session_1",
    severity: "info",
    data,
  };
}

test("final_response event appends an assistant message", () => {
  const state = applyRuntimeEvent(createInitialRuntimeState(), event("final_response", { content: "Hello from graph" }));

  assert.equal(state.messages.at(-1)?.role, "assistant");
  assert.equal(state.messages.at(-1)?.content, "Hello from graph");
  assert.equal(state.finalResponse, "Hello from graph");
});

test("permission_required and permission_resolved update modal state", () => {
  const withPermission = applyRuntimeEvent(
    createInitialRuntimeState(),
    event("permission_required", {
      tool_call_id: "call_1",
      tool_name: "write_file",
      action: "write",
      risk: "high",
      args_summary: "writes README.md",
      reason: "Needs approval",
    }),
  );

  assert.equal(withPermission.pendingPermission?.tool_call_id, "call_1");
  assert.equal(withPermission.pendingPermission?.tool_name, "write_file");

  const resolved = applyRuntimeEvent(withPermission, event("permission_resolved", { tool_call_id: "call_1", decision: "rejected" }));

  assert.equal(resolved.pendingPermission, null);
  assert.equal(resolved.activities.at(-1)?.kind, "permission");
});

test("context events populate context panel state", () => {
  let state = createInitialRuntimeState();
  state = applyRuntimeEvent(state, event("context_fragment_added", { id: "ctx_1", kind: "file", title: "README.md", trust: "trusted_local", token_estimate: 12 }));
  state = applyRuntimeEvent(state, event("context_budget_applied", { max_tokens: 100, used_tokens: 12, included: ["ctx_1"] }));
  state = applyRuntimeEvent(state, event("context_resolution_error", { message: "not found", reference: "@missing.md" }));

  assert.equal(state.context.fragments.length, 1);
  assert.equal(state.context.fragments[0].title, "README.md");
  assert.equal(state.context.budget?.used_tokens, 12);
  assert.equal(state.context.errors.length, 1);
});

test("unknown events are preserved as generic activities", () => {
  const state = applyRuntimeEvent(createInitialRuntimeState(), event("future_event", { value: 1 }));

  assert.equal(state.activities.length, 1);
  assert.equal(state.activities[0].kind, "event");
  assert.equal(state.activities[0].label, "future_event");
});

test("done stream frame updates active session and final response", () => {
  const state = applyStreamFrame(createInitialRuntimeState(), {
    type: "done",
    session_id: "session_1",
    final_response: "Done text",
  });

  assert.equal(state.sessionId, "session_1");
  assert.equal(state.finalResponse, "Done text");
  assert.equal(state.messages.at(-1)?.content, "Done text");
  assert.equal(state.isStreaming, false);
});

test("streaming can be stopped without leaving the composer in streaming mode", () => {
  const state = markStreamingStopped({
    ...createInitialRuntimeState(),
    isStreaming: true,
  });

  assert.equal(state.isStreaming, false);
});
