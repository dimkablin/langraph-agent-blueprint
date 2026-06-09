import assert from "node:assert/strict";
import test from "node:test";

import type { RuntimeEvent, StreamFrame } from "../src/api/schemas.ts";
import { buildActivityEntries } from "../src/runtime/activityTimeline.ts";
import { applyRuntimeEvent, applyStreamFrame, createInitialRuntimeState } from "../src/runtime/reducer.ts";

function typedEvent(id: string, streamEvent: Record<string, unknown>): RuntimeEvent {
  return {
    id,
    type: "agent_activity",
    timestamp: "2026-05-08T00:00:00Z",
    session_id: "session_1",
    severity: "info",
    data: { stream_event: streamEvent },
  };
}

function eventFrame(id: string, streamEvent: Record<string, unknown>): StreamFrame {
  return { type: "event", event: typedEvent(id, streamEvent) };
}

test("typed assistant stream events build one assistant message and ignore duplicate done final text", () => {
  let state = { ...createInitialRuntimeState(), isStreaming: true };

  state = applyRuntimeEvent(
    state,
    typedEvent("typed_delta_1", { kind: "assistant_delta", message_id: "assistant_1", delta: "Hello" }),
  );
  state = applyRuntimeEvent(
    state,
    typedEvent("typed_delta_2", { kind: "assistant_delta", message_id: "assistant_1", delta: " world" }),
  );

  assert.equal(state.messages.length, 1);
  assert.equal(state.messages[0].content, "Hello world");
  assert.equal(state.messages[0].id, "assistant_1");

  state = applyStreamFrame(state, eventFrame("typed_final_1", {
    kind: "assistant_final",
    message_id: "assistant_1",
    content: "Hello world",
  }));
  state = applyStreamFrame(state, { type: "done", session_id: "session_1", final_response: "Hello world" });

  assert.equal(state.messages.length, 1);
  assert.equal(state.messages[0].content, "Hello world");
  assert.equal(state.finalResponse, "Hello world");
  assert.equal(state.isStreaming, false);
});

test("typed tool lifecycle events render one structured timeline block without magic event names", () => {
  let state = { ...createInitialRuntimeState(), isStreaming: true };

  state = applyRuntimeEvent(
    state,
    typedEvent("tool_started", {
      kind: "tool_lifecycle",
      phase: "started",
      tool_call_id: "call_1",
      tool_name: "bash",
      title: "Run command",
      args_summary: "npm test",
      command: "npm test",
    }),
  );
  state = applyRuntimeEvent(
    state,
    typedEvent("tool_completed", {
      kind: "tool_lifecycle",
      phase: "completed",
      tool_call_id: "call_1",
      tool_name: "bash",
      title: "Run command",
      result_summary: "All tests passed",
      command: "npm test",
      exit_code: 0,
    }),
  );

  const activityGroup = state.timeline.find((item) => item.kind === "activity");
  assert.ok(activityGroup);
  assert.equal(activityGroup.activities.length, 1);
  assert.equal(activityGroup.activities[0].kind, "tool");
  assert.equal(activityGroup.activities[0].status, "success");
  assert.equal(activityGroup.activities[0].data.tool_call_id, "call_1");

  const entries = buildActivityEntries(activityGroup.activities);
  assert.equal(entries.length, 1);
  assert.equal(entries[0].title, "Run command");
  assert.equal(entries[0].summary, "All tests passed");
});

test("typed permission state opens and clears the pending permission modal state", () => {
  let state = createInitialRuntimeState();

  state = applyRuntimeEvent(
    state,
    typedEvent("permission_required", {
      kind: "permission_state",
      status: "required",
      tool_call_id: "write_1",
      tool_name: "write_file",
      action: "write",
      risk: "medium",
      args_summary: "{\"path\":\"README.md\"}",
      reason: "File writes require approval",
      args: { path: "README.md" },
    }),
  );

  assert.equal(state.pendingPermission?.tool_call_id, "write_1");
  assert.equal(state.pendingPermission?.tool_name, "write_file");

  state = applyRuntimeEvent(
    state,
    typedEvent("permission_resolved", {
      kind: "permission_state",
      status: "approved",
      tool_call_id: "write_1",
      tool_name: "write_file",
      reason: "Approved",
    }),
  );

  assert.equal(state.pendingPermission, null);
});
