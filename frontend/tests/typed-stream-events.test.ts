import assert from "node:assert/strict";
import test from "node:test";

import type { RuntimeEvent, StreamFrame } from "../src/api/schemas.ts";
import { buildActivityEntries } from "../src/runtime/activityTimeline.ts";
import { applyRuntimeEvent, applyStreamFrame, createInitialRuntimeState } from "../src/runtime/reducer.ts";
import { buildSubagentTimelineRows } from "../src/runtime/subagentTimeline.ts";

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

test("model message progress payload is rendered as assistant text rather than activity", () => {
  const state = applyRuntimeEvent(
    createInitialRuntimeState(),
    {
      id: "model_progress_legacy",
      type: "model_message",
      timestamp: "2026-05-08T00:00:00Z",
      session_id: "session_1",
      severity: "info",
      data: {
        content: "Привет! Сначала проанализирую структуру проекта.",
        stream_event: {
          kind: "progress",
          message: "Привет! Сначала проанализирую структуру проекта.",
          stage: "model_message",
          message_id: "assistant_legacy",
        },
      },
    },
  );

  assert.deepEqual(state.messages.map((message) => message.content), ["Привет! Сначала проанализирую структуру проекта."]);
  assert.equal(state.timeline.some((item) => item.kind === "activity"), false);
  assert.equal(state.activities.some((activity) => activity.summary.includes("Привет!")), false);
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
      scope: "subagent",
      child_run_id: "child_1",
      child_thread_id: "thread_child_1",
      child_session_id: "session_child_1",
      subagent_name: "writer",
    }),
  );

  assert.equal(state.pendingPermission?.tool_call_id, "write_1");
  assert.equal(state.pendingPermission?.tool_name, "write_file");
  assert.equal(state.pendingPermission?.scope, "subagent");
  assert.equal(state.pendingPermission?.child_thread_id, "thread_child_1");
  assert.equal(state.pendingPermission?.subagent_name, "writer");

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

test("typed subagent stream events use stable run ids and dedupe by sequence", () => {
  let state = createInitialRuntimeState();

  const subagentPayload = {
    kind: "subagent",
    phase: "event",
    subagent_id: "backend_agent",
    run_id: "child_backend",
    sequence: 2,
    name: "backend",
    child_event_type: "model_token",
    child_event: { type: "model_token", data: { token: "Backend" } },
    child_stream_event: { kind: "assistant_delta", message_id: "child_msg_1", delta: "Backend" },
  };

  state = applyRuntimeEvent(state, typedEvent("subagent_event_1", subagentPayload));
  state = applyRuntimeEvent(state, typedEvent("subagent_event_duplicate", subagentPayload));

  assert.equal(state.activities.length, 1);
  assert.equal(state.activities[0].id, "subagent:child_backend:2");
  assert.equal(state.activities[0].eventType, "subagent_event");
  assert.equal(state.activities[0].data.subagent_id, "backend_agent");
  assert.equal(state.activities[0].data.run_id, "child_backend");
  assert.equal(state.activities[0].data.sequence, 2);
  assert.deepEqual(state.activities[0].data.child_stream_event, { kind: "assistant_delta", message_id: "child_msg_1", delta: "Backend" });
});

test("interleaved typed subagent streams stay separated in the shared timeline", () => {
  let state = createInitialRuntimeState();
  const streamEvents = [
    subagentEvent("backend_agent", "child_backend", 0, "started", { name: "backend" }),
    subagentEvent("frontend_agent", "child_frontend", 0, "started", { name: "frontend" }),
    subagentEvent("backend_agent", "child_backend", 1, "event", {
      name: "backend",
      child_event_type: "model_message",
      child_stream_event: { kind: "assistant_final", message_id: "backend_msg", content: "Backend done" },
    }),
    subagentEvent("frontend_agent", "child_frontend", 1, "event", {
      name: "frontend",
      child_event_type: "model_message",
      child_stream_event: { kind: "assistant_final", message_id: "frontend_msg", content: "Frontend done" },
    }),
    subagentEvent("backend_agent", "child_backend", 2, "finished", { name: "backend", summary: "Backend done" }),
    subagentEvent("frontend_agent", "child_frontend", 2, "finished", { name: "frontend", summary: "Frontend done" }),
  ];

  for (const [index, streamEvent] of streamEvents.entries()) {
    state = applyRuntimeEvent(state, typedEvent(`subagent_${index}`, streamEvent));
  }

  const entries = buildActivityEntries(state.activities);
  const backend = entries.find((entry) => entry.activity.data.run_id === "child_backend");
  const frontend = entries.find((entry) => entry.activity.data.run_id === "child_frontend");

  assert.equal(entries.length, 2);
  assert.ok(backend);
  assert.ok(frontend);
  assert.deepEqual(backend.activities.map((activity) => activity.data.sequence), [0, 1, 2]);
  assert.deepEqual(frontend.activities.map((activity) => activity.data.sequence), [0, 1, 2]);
  assert.equal(buildSubagentTimelineRows(backend.activities).find((row) => row.kind === "message")?.content, "Backend done");
  assert.equal(buildSubagentTimelineRows(frontend.activities).find((row) => row.kind === "message")?.content, "Frontend done");
});

function subagentEvent(
  subagentId: string,
  runId: string,
  sequence: number,
  phase: "started" | "event" | "finished" | "error" | "cancelled" | "timeout",
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    kind: "subagent",
    phase,
    subagent_id: subagentId,
    run_id: runId,
    sequence,
    ...overrides,
  };
}
