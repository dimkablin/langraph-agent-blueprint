import assert from "node:assert/strict";
import test from "node:test";

import { buildActivityEntries } from "../src/runtime/activityTimeline.ts";
import { appendUserMessage, applyRuntimeEvent, applySessionDetail, applyStreamFrame, createInitialRuntimeState, markStreamingStopped } from "../src/runtime/reducer.ts";
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

test("session detail hides persisted tool result messages from chat history", () => {
  const state = applySessionDetail(createInitialRuntimeState(), {
    session_id: "session_1",
    title: "folder question",
    messages: [
      {
        id: "human-1",
        role: "human",
        type: "HumanMessage",
        content: "привет что в папке?",
        tool_calls: [],
      },
      {
        id: "ai-tool-call",
        role: "ai",
        type: "AIMessage",
        content: "",
        tool_calls: [{ id: "call_glob", name: "glob", args: { pattern: "*" } }],
      },
      {
        id: "tool-glob",
        role: "tool",
        type: "ToolMessage",
        content: '{"name":"glob","status":"ok","content":"C:\\\\project\\\\README.md"}',
        tool_calls: [],
        tool_call_id: "call_glob",
      },
      {
        id: "ai-final",
        role: "ai",
        type: "AIMessage",
        content: "В папке проекта находится README.md.",
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
    ["привет что в папке?", "В папке проекта находится README.md."],
  );
  assert.equal(state.finalResponse, "В папке проекта находится README.md.");
});

test("unknown events are preserved as generic activities", () => {
  const state = applyRuntimeEvent(createInitialRuntimeState(), event("future_event", { value: 1 }));

  assert.equal(state.activities.length, 1);
  assert.equal(state.activities[0].kind, "event");
  assert.equal(state.activities[0].label, "future_event");
});

test("structured activity payloads take precedence over runtime event fallback", () => {
  const state = applyRuntimeEvent(
    createInitialRuntimeState(),
    event("tool_call_started", {
      id: "call_1",
      name: "custom_probe",
      activity: {
        id: "activity_1",
        type: "custom.probe.started",
        source: { kind: "tool", name: "custom_probe" },
        category: "tool",
        status: "running",
        title: "Custom Probe",
        summary: "Running custom probe",
        data: { phrase: "hello" },
        refs: [],
      },
    }),
  );

  assert.equal(state.activities.length, 1);
  assert.equal(state.activities[0].id, "activity_1");
  assert.equal(state.activities[0].kind, "tool");
  assert.equal(state.activities[0].eventType, "custom.probe.started");
  assert.equal(state.activities[0].label, "Custom Probe");
  assert.equal(state.activities[0].status, "running");
  assert.deepEqual(state.activities[0].data, { phrase: "hello" });
});

test("tool lifecycle activities with the same tool_call_id update one visible timeline row", () => {
  let state = applyRuntimeEvent(
    createInitialRuntimeState(),
    event("tool_call_started", {
      activity: {
        id: "activity_call_1_started",
        type: "tool.glob.started",
        source: { kind: "tool", name: "glob" },
        category: "tool",
        status: "running",
        title: "Find files started",
        summary: "Finding files matching `README*`.",
        data: { tool_call_id: "call_1", tool_name: "glob", operation: "search.glob", pattern: "README*" },
        refs: [],
      },
    }),
  );
  state = applyRuntimeEvent(
    state,
    event("tool_call_finished", {
      activity: {
        id: "activity_call_1_completed",
        type: "tool.glob.completed",
        source: { kind: "tool", name: "glob" },
        category: "tool",
        status: "success",
        title: "Find files completed",
        summary: "Found 1 file match(es).",
        data: { tool_call_id: "call_1", tool_name: "glob", operation: "search.glob", pattern: "README*", result_count: 1 },
        refs: [],
      },
    }),
  );

  assert.equal(state.activities.length, 2);
  assert.equal(state.timeline.length, 1);
  assert.equal(state.timeline[0].kind, "activity");
  if (state.timeline[0].kind === "activity") {
    assert.equal(state.timeline[0].activities.length, 1);
    assert.equal(state.timeline[0].activities[0].id, "activity_call_1_started");
    assert.equal(state.timeline[0].activities[0].eventType, "tool.glob.completed");
    assert.equal(state.timeline[0].activities[0].status, "success");
    assert.deepEqual(state.timeline[0].activities[0].data, {
      tool_call_id: "call_1",
      tool_name: "glob",
      operation: "search.glob",
      pattern: "README*",
      result_count: 1,
    });
  }
});

test("permission and approved tool activity share one timeline row with debug history", () => {
  let state = applyRuntimeEvent(
    createInitialRuntimeState(),
    event("permission_required", {
      tool_call_id: "call_1",
      tool_name: "bash",
      action: "shell",
      risk: "high",
      reason: "Shell commands can modify the system.",
      activity: {
        id: "activity_call_1_requested",
        type: "permission.tool.requested",
        source: { kind: "permission", name: "bash" },
        category: "permission",
        status: "pending",
        title: "Permission required",
        summary: "Shell commands can modify the system.",
        data: { tool_call_id: "call_1", tool_name: "bash", action: "shell", risk: "high" },
        refs: [],
      },
    }),
  );
  state = applyRuntimeEvent(
    state,
    event("permission_resolved", {
      tool_call_id: "call_1",
      tool_name: "bash",
      decision: "approved",
      activity: {
        id: "activity_call_1_approved",
        type: "permission.tool.approved",
        source: { kind: "permission", name: "bash" },
        category: "permission",
        status: "success",
        title: "Permission approved",
        summary: "Approved by user.",
        data: { tool_call_id: "call_1", tool_name: "bash", decision: "approved" },
        refs: [],
      },
    }),
  );
  state = applyRuntimeEvent(
    state,
    event("tool_call_started", {
      activity: {
        id: "activity_call_1_started",
        type: "tool.bash.started",
        source: { kind: "tool", name: "bash" },
        category: "tool",
        status: "running",
        title: "Run Bash command",
        summary: "Running `npm test`.",
        data: { tool_call_id: "call_1", tool_name: "bash", operation: "shell.run", command: "npm test" },
        refs: [],
      },
    }),
  );
  state = applyRuntimeEvent(
    state,
    event("tool_call_finished", {
      activity: {
        id: "activity_call_1_completed",
        type: "tool.bash.completed",
        source: { kind: "tool", name: "bash" },
        category: "tool",
        status: "success",
        title: "Run Bash command completed",
        summary: "Command exited with code 0.",
        data: { tool_call_id: "call_1", tool_name: "bash", operation: "shell.run", command: "npm test", exit_code: 0 },
        refs: [],
      },
    }),
  );

  assert.equal(state.activities.length, 4);
  assert.equal(state.timeline.length, 1);
  assert.equal(state.timeline[0].kind, "activity");
  if (state.timeline[0].kind === "activity") {
    assert.equal(state.timeline[0].activities.length, 1);
    const [entry] = buildActivityEntries(state.timeline[0].activities);
    assert.deepEqual(
      entry.activities.map((item) => item.eventType),
      ["permission.tool.requested", "permission.tool.approved", "tool.bash.started", "tool.bash.completed"],
    );
    assert.ok(Array.isArray(entry.debugPayload));
    assert.deepEqual(
      entry.debugPayload.map((item) => item.type),
      ["permission.tool.requested", "permission.tool.approved", "tool.bash.started", "tool.bash.completed"],
    );
  }
});

test("unknown structured activity category renders as generic event activity", () => {
  const state = applyRuntimeEvent(
    createInitialRuntimeState(),
    event("agent_activity", {
      activity: {
        id: "activity_future",
        type: "vendor.future.completed",
        source: { kind: "vendor", name: "future" },
        category: "future",
        status: "success",
        title: "Future activity",
        summary: "A future producer emitted this.",
        data: { value: 1 },
        refs: [],
      },
    }),
  );

  assert.equal(state.activities[0].kind, "event");
  assert.equal(state.activities[0].status, "success");
  assert.equal(state.activities[0].label, "Future activity");
});

test("permission denied activity stays visible as blocked", () => {
  const state = applyRuntimeEvent(
    createInitialRuntimeState(),
    event("permission_resolved", {
      tool_call_id: "call_1",
      decision: "rejected",
      activity: {
        id: "activity_permission",
        type: "permission.tool.denied",
        source: { kind: "permission", name: "bash" },
        category: "permission",
        status: "blocked",
        title: "Permission denied",
        summary: "Permission denied: destructive shell command blocked.",
        data: { tool_name: "bash" },
        refs: [],
      },
    }),
  );

  assert.equal(state.pendingPermission, null);
  assert.equal(state.activities[0].kind, "permission");
  assert.equal(state.activities[0].status, "blocked");
  assert.equal(state.activities[0].summary, "Permission denied: destructive shell command blocked.");
});

test("activity events do not replace final response chat messages", () => {
  let state = applyRuntimeEvent(
    createInitialRuntimeState(),
    event("agent_activity", {
      activity: {
        id: "activity_done",
        type: "runtime.run.completed",
        source: { kind: "runtime", component: "AssistantGraphRuntime" },
        category: "runtime",
        status: "success",
        title: "Run completed",
        data: {},
        refs: [],
      },
    }),
  );
  state = applyRuntimeEvent(state, event("final_response", { content: "Final answer text" }));

  assert.deepEqual(state.messages.map((message) => message.content), ["Final answer text"]);
  assert.equal(state.activities[0].eventType, "runtime.run.completed");
  assert.equal(state.finalResponse, "Final answer text");
});

test("structured activity is rendered in the chat timeline before the bound assistant message", () => {
  let state = appendUserMessage(createInitialRuntimeState(), "Run checks");
  state = applyRuntimeEvent(state, event("model_token", { token: "Thinking" }, "token_1"));
  state = applyRuntimeEvent(
    state,
    event("tool_call_started", {
      activity: {
        id: "activity_shell",
        type: "tool.bash.started",
        source: { kind: "tool", name: "bash" },
        category: "verification",
        status: "running",
        title: "Run Bash command",
        summary: "Running `pytest -q`.",
        data: { operation: "shell.run", command: "pytest -q" },
        refs: [],
      },
    }),
  );
  state = applyRuntimeEvent(
    state,
    event(
      "final_response",
      {
        content: "Tests passed.",
        activity: {
          id: "activity_run_completed",
          type: "runtime.run.completed",
          source: { kind: "runtime", component: "AssistantGraphRuntime" },
          category: "runtime",
          status: "success",
          title: "Run completed",
          data: {},
          refs: [],
        },
      },
      "final_1",
    ),
  );

  assert.deepEqual(
    state.timeline.map((item) => item.kind),
    ["message", "message", "activity", "message"],
  );
  const activityItem = state.timeline[2];
  assert.equal(activityItem.kind, "activity");
  assert.equal(activityItem.messageId, "final_1");
  assert.equal(activityItem.activities[0].eventType, "tool.bash.started");
  assert.equal(state.timeline[3].kind, "message");
  if (state.timeline[3].kind === "message") {
    assert.equal(state.timeline[3].message.content, "Tests passed.");
  }
});

test("session detail restores persisted activity above the final assistant message", () => {
  const state = applySessionDetail(createInitialRuntimeState(), {
    session_id: "session_1",
    title: "activity session",
    messages: [
      { id: "human_1", role: "human", type: "HumanMessage", content: "Run checks", tool_calls: [] },
      { id: "ai_1", role: "ai", type: "AIMessage", content: "Checks passed.", tool_calls: [] },
    ],
    events: [
      event(
        "tool_call_finished",
        {
          activity: {
            id: "activity_check",
            type: "tool.bash.completed",
            source: { kind: "tool", name: "bash" },
            category: "verification",
            status: "success",
            title: "Run Bash command completed",
            summary: "Command exited with code 0.",
            data: { command: "pytest -q", exit_code: 0 },
            refs: [],
          },
        },
        "event_check",
      ),
    ],
    tool_calls: [],
    todos: [],
    memory: {},
    usage: {},
    context: { references: [], fragments: [], attachments: [], budget: {}, errors: [] },
    child_runs: [],
    metadata: {},
  });

  assert.deepEqual(
    state.timeline.map((item) => item.kind),
    ["message", "activity", "message"],
  );
  assert.equal(state.timeline[1].kind, "activity");
  if (state.timeline[1].kind === "activity") {
    assert.equal(state.timeline[1].messageId, "ai_1");
    assert.equal(state.timeline[1].activities[0].eventType, "tool.bash.completed");
  }
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
