import assert from "node:assert/strict";
import test from "node:test";

import { applyRuntimeEvent, applySessionDetail, applyStreamFrame, createInitialRuntimeState, markStreamingStopped } from "../src/runtime/reducer.ts";
import type { RuntimeEvent, StreamFrame } from "../src/api/schemas.ts";

function event(type: string, data: Record<string, unknown> = {}, id = `event_${type}`): RuntimeEvent {
  return {
    id,
    type,
    timestamp: "2026-05-08T00:00:00Z",
    session_id: "session_1",
    severity: "info",
    data,
  };
}

function eventFrame(type: string, data: Record<string, unknown> = {}, id?: string): StreamFrame {
  return { type: "event", event: event(type, data, id) };
}

function applyFrames(frames: StreamFrame[]) {
  let state = { ...createInitialRuntimeState(), isStreaming: true };
  for (const frame of frames) {
    state = applyStreamFrame(state, frame);
  }
  return state;
}

test("final_response event appends an assistant message", () => {
  const state = applyRuntimeEvent(createInitialRuntimeState(), event("final_response", { content: "Hello from graph" }));

  assert.equal(state.messages.at(-1)?.role, "assistant");
  assert.equal(state.messages.at(-1)?.content, "Hello from graph");
  assert.equal(state.finalResponse, "Hello from graph");
});

test("model_token events update a streaming assistant draft", () => {
  let state = { ...createInitialRuntimeState(), isStreaming: true };

  state = applyRuntimeEvent(state, event("model_token", { token: "Hello" }));
  state = applyRuntimeEvent(state, event("model_token", { token: " world" }));

  assert.equal(state.messages.length, 1);
  assert.equal(state.messages[0].role, "assistant");
  assert.equal(state.messages[0].content, "Hello world");
  assert.equal(state.isStreaming, true);

  state = applyRuntimeEvent(state, event("model_message", { content: "Hello world" }));

  assert.equal(state.messages.length, 1);
  assert.equal(state.messages[0].role, "assistant");
  assert.equal(state.messages[0].content, "Hello world");
  assert.equal(state.isStreaming, true);
});

test("model_token events preserve whitespace-only chunks before final message", () => {
  let state = { ...createInitialRuntimeState(), isStreaming: true };

  state = applyRuntimeEvent(state, event("model_token", { token: "Line 1" }, "token_1"));
  state = applyRuntimeEvent(state, event("model_token", { token: "\n" }, "token_2"));
  state = applyRuntimeEvent(state, event("model_token", { token: "Line 2" }, "token_3"));
  state = applyRuntimeEvent(state, event("model_token", { token: "\n\n" }, "token_4"));
  state = applyRuntimeEvent(state, event("model_token", { token: "Line 3" }, "token_5"));
  state = applyRuntimeEvent(state, event("model_message", { content: "Line 1\nLine 2\n\nLine 3" }));
  state = applyRuntimeEvent(state, event("final_response", { content: "Line 1\nLine 2\n\nLine 3" }));

  assert.deepEqual(state.messages.map((message) => message.content), ["Line 1\nLine 2\n\nLine 3"]);
  assert.equal(state.finalResponse, "Line 1\nLine 2\n\nLine 3");
});

test("model_token after a completed model message starts a new assistant draft", () => {
  let state = { ...createInitialRuntimeState(), isStreaming: true };

  state = applyRuntimeEvent(state, event("model_token", { token: "Calling tool" }));
  state = applyRuntimeEvent(state, event("model_message", { content: "Calling tool" }));
  state = applyRuntimeEvent(state, event("model_token", { token: "Tool result" }));

  assert.equal(state.messages.length, 2);
  assert.equal(state.messages[0].content, "Calling tool");
  assert.equal(state.messages[1].content, "Tool result");
});

test("model_token chunks keep updating the active draft after streaming flag was cleared", () => {
  let state = createInitialRuntimeState();

  state = applyRuntimeEvent(state, event("model_token", { token: "Я" }));
  state = applyRuntimeEvent(state, event("model_token", { token: " не" }));

  assert.equal(state.messages.length, 1);
  assert.equal(state.messages[0].content, "Я не");
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

test("context events populate runtime context state", () => {
  let state = createInitialRuntimeState();
  state = applyRuntimeEvent(state, event("context_fragment_added", { id: "ctx_1", kind: "file", title: "README.md", trust: "trusted_local", token_estimate: 12 }));
  state = applyRuntimeEvent(state, event("context_budget_applied", { max_tokens: 100, used_tokens: 12, included: ["ctx_1"] }));
  state = applyRuntimeEvent(state, event("context_resolution_error", { message: "not found", reference: "@missing.md" }));

  assert.equal(state.context.fragments.length, 1);
  assert.equal(state.context.fragments[0].title, "README.md");
  assert.equal(state.context.budget?.used_tokens, 12);
  assert.equal(state.context.errors.length, 1);
});

test("compact_started creates a running non-message timeline separator", () => {
  const state = applyRuntimeEvent(createInitialRuntimeState(), event("compact_started", { reason: "message_threshold" }));

  assert.equal(state.messages.length, 0);
  assert.equal(state.timeline.length, 1);
  assert.equal(state.timeline[0].kind, "separator");
  assert.equal(state.timeline[0].label, "Контекст автоматически сжимается");
  assert.equal(state.timeline[0].status, "running");
});

test("compact_finished completes the running timeline separator", () => {
  let state = applyRuntimeEvent(createInitialRuntimeState(), event("compact_started", { reason: "message_threshold" }, "compact_start_1"));

  state = applyRuntimeEvent(state, event("compact_finished", { summary: "older context was summarized" }, "compact_finish_1"));

  assert.equal(state.messages.length, 0);
  assert.equal(state.timeline.length, 1);
  assert.equal(state.timeline[0].kind, "separator");
  assert.equal(state.timeline[0].label, "Контекст автоматически сжат");
  assert.equal(state.timeline[0].status, "done");
});

test("compact_finished creates a non-message timeline separator without a prior start", () => {
  const state = applyRuntimeEvent(createInitialRuntimeState(), event("compact_finished", { summary: "older context was summarized" }));

  assert.equal(state.messages.length, 0);
  assert.equal(state.timeline.length, 1);
  assert.equal(state.timeline[0].kind, "separator");
  assert.equal(state.timeline[0].label, "Контекст автоматически сжат");
  assert.equal(state.timeline[0].status, "done");
});

test("compact done frame does not append Context compacted as assistant message", () => {
  const state = applyFrames([
    eventFrame("compact_finished", { summary: "older context was summarized" }, "compact_1"),
    { type: "done", session_id: "session_1", final_response: "Context compacted." },
  ]);

  assert.equal(state.messages.length, 0);
  assert.equal(state.timeline.length, 1);
  assert.equal(state.timeline[0].kind, "separator");
  assert.equal(state.finalResponse, "Context compacted.");
  assert.equal(state.isStreaming, false);
});

test("session detail hides internal compaction summary messages", () => {
  const state = applySessionDetail(createInitialRuntimeState(), {
    session_id: "session_1",
    title: "hello",
    messages: [
      {
        id: "compact-summary",
        role: "system",
        type: "SystemMessage",
        content: "Compacted prior context: hello | assistant reply",
        tool_calls: [],
      },
      {
        id: "human-1",
        role: "human",
        type: "HumanMessage",
        content: "visible user message",
        tool_calls: [],
      },
      {
        id: "ai-1",
        role: "ai",
        type: "AIMessage",
        content: "visible assistant message",
        tool_calls: [],
      },
    ],
    events: [],
    tool_calls: [],
    todos: [],
    memory: {},
    usage: {},
    context: { references: [], fragments: [], attachments: [], budget: {}, errors: [] },
    child_runs: [],
    metadata: {},
  });

  assert.deepEqual(
    state.messages.map((message) => message.content),
    ["visible user message", "visible assistant message"],
  );
  assert.deepEqual(
    state.timeline.map((item) => (item.kind === "message" ? item.message.content : item.label)),
    ["visible user message", "visible assistant message"],
  );
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

test("text stream frames merge tokens, final events, and done frame without duplicate messages", () => {
  const state = applyFrames([
    eventFrame("model_token", { token: "Fake" }, "token_1"),
    eventFrame("model_token", { token: " response" }, "token_2"),
    eventFrame("model_token", { token: ": hello" }, "token_3"),
    eventFrame("model_message", { content: "Fake response: hello" }),
    eventFrame("final_response", { content: "Fake response: hello" }),
    { type: "done", session_id: "session_1", final_response: "Fake response: hello" },
  ]);

  assert.deepEqual(state.messages.map((message) => message.content), ["Fake response: hello"]);
  assert.equal(state.sessionId, "session_1");
  assert.equal(state.finalResponse, "Fake response: hello");
  assert.equal(state.isStreaming, false);
});

test("tool stream frames keep the tool preface and tool result as separate assistant messages", () => {
  const state = applyFrames([
    eventFrame("model_token", { token: "Calling" }, "token_1"),
    eventFrame("model_token", { token: " tool" }, "token_2"),
    eventFrame("model_token", { token: " read_file" }, "token_3"),
    eventFrame("model_message", { content: "Calling tool read_file" }),
    eventFrame("tool_call_started", { id: "call_1", name: "read_file" }),
    eventFrame("tool_call_finished", { id: "call_1", name: "read_file", status: "ok" }),
    eventFrame("model_token", { token: "Tool" }, "token_4"),
    eventFrame("model_token", { token: " read_file" }, "token_5"),
    eventFrame("model_token", { token: " ok:" }, "token_6"),
    eventFrame("model_token", { token: " tool-stream-ok" }, "token_7"),
    eventFrame("model_message", { content: "Tool read_file ok: tool-stream-ok" }),
    eventFrame("final_response", { content: "Tool read_file ok: tool-stream-ok" }),
    { type: "done", session_id: "session_1", final_response: "Tool read_file ok: tool-stream-ok" },
  ]);

  assert.deepEqual(state.messages.map((message) => message.content), [
    "Calling tool read_file",
    "Tool read_file ok: tool-stream-ok",
  ]);
  assert.deepEqual(
    state.activities.filter((activity) => activity.kind === "tool").map((activity) => activity.eventType),
    ["tool_call_started", "tool_call_finished"],
  );
  assert.equal(state.finalResponse, "Tool read_file ok: tool-stream-ok");
  assert.equal(state.isStreaming, false);
});

test("permission stream frames leave the pending permission open without inventing a final answer", () => {
  const state = applyFrames([
    eventFrame("model_token", { token: "Calling" }, "token_1"),
    eventFrame("model_token", { token: " tool" }, "token_2"),
    eventFrame("model_token", { token: " write_file" }, "token_3"),
    eventFrame("model_message", { content: "Calling tool write_file" }),
    eventFrame("permission_required", {
      tool_call_id: "call_1",
      tool_name: "write_file",
      action: "write",
      risk: "medium",
      args: { path: "created.txt", content: "hello" },
    }),
    { type: "done", session_id: "session_1" },
  ]);

  assert.deepEqual(state.messages.map((message) => message.content), ["Calling tool write_file"]);
  assert.equal(state.pendingPermission?.tool_call_id, "call_1");
  assert.equal(state.pendingPermission?.tool_name, "write_file");
  assert.deepEqual(state.pendingPermission?.args, { path: "created.txt", content: "hello" });
  assert.equal(state.finalResponse, null);
  assert.equal(state.isStreaming, false);
  assert.equal(state.activities.some((activity) => activity.kind === "tool"), false);
});

test("streaming can be stopped without leaving the composer in streaming mode", () => {
  const state = markStreamingStopped({
    ...createInitialRuntimeState(),
    isStreaming: true,
  });

  assert.equal(state.isStreaming, false);
});
