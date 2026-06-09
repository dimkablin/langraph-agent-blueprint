import assert from "node:assert/strict";
import test from "node:test";

import { buildSubagentTimelineRows } from "../src/runtime/subagentTimeline.ts";
import type { ActivityItem } from "../src/runtime/reducer.ts";

function subagentActivity(overrides: Partial<ActivityItem> & { id: string; eventType: string }): ActivityItem {
  return {
    id: overrides.id,
    kind: "subagent",
    category: "subagent",
    label: overrides.label ?? overrides.eventType,
    summary: overrides.summary ?? "",
    status: overrides.status ?? "info",
    timestamp: overrides.timestamp ?? "2026-06-04T00:00:00Z",
    eventType: overrides.eventType,
    data: overrides.data ?? {},
    relatedActivities: overrides.relatedActivities,
  };
}

test("subagent timeline aggregates streamed model tokens into one message row", () => {
  const rows = buildSubagentTimelineRows([
    subagentActivity({
      id: "start",
      eventType: "subagent_started",
      status: "running",
      data: { child_run_id: "child_backend", name: "backend" },
    }),
    subagentActivity({
      id: "token_1",
      eventType: "subagent_event",
      data: { child_run_id: "child_backend", child_event_type: "model_token", child_event: { type: "model_token", data: { token: "Backend" } } },
    }),
    subagentActivity({
      id: "token_2",
      eventType: "subagent_event",
      data: { child_run_id: "child_backend", child_event_type: "model_token", child_event: { type: "model_token", data: { token: " done" } } },
    }),
  ]);

  assert.deepEqual(rows.map((row) => row.kind), ["status", "message"]);
  assert.equal(rows[1].content, "Backend done");
  assert.equal(rows[1].status, "running");
});

test("subagent timeline replaces token draft with final model message when content matches", () => {
  const rows = buildSubagentTimelineRows([
    subagentActivity({
      id: "token_1",
      eventType: "subagent_event",
      data: { child_run_id: "child_backend", child_event_type: "model_token", child_event: { type: "model_token", data: { token: "Backend" } } },
    }),
    subagentActivity({
      id: "token_2",
      eventType: "subagent_event",
      data: { child_run_id: "child_backend", child_event_type: "model_token", child_event: { type: "model_token", data: { token: " done" } } },
    }),
    subagentActivity({
      id: "message",
      eventType: "subagent_event",
      data: {
        child_run_id: "child_backend",
        child_event_type: "model_message",
        child_event: { type: "model_message", data: { content: "Backend done" } },
      },
    }),
  ]);

  assert.equal(rows.length, 1);
  assert.equal(rows[0].kind, "message");
  assert.equal(rows[0].content, "Backend done");
});

test("subagent timeline drops decorative separator-only model messages", () => {
  const rows = buildSubagentTimelineRows([
    subagentActivity({
      id: "token_separator",
      eventType: "subagent_event",
      data: { child_run_id: "child_backend", child_event_type: "model_token", child_event: { type: "model_token", data: { token: "***" } } },
    }),
    subagentActivity({
      id: "message_separator",
      eventType: "subagent_event",
      data: { child_run_id: "child_backend", child_event_type: "model_message", child_event: { type: "model_message", data: { content: "*****" } } },
    }),
  ]);

  assert.equal(rows.length, 0);
});

test("subagent timeline hides technical child lifecycle and activity wrapper events", () => {
  const rows = buildSubagentTimelineRows([
    subagentActivity({
      id: "session_started",
      eventType: "subagent_event",
      data: { child_run_id: "child_backend", child_event_type: "session_started", child_event: { type: "session_started", data: {} } },
    }),
    subagentActivity({
      id: "agent_activity",
      eventType: "subagent_event",
      data: {
        child_run_id: "child_backend",
        child_event_type: "agent_activity",
        child_event: {
          type: "agent_activity",
          data: {
            activity: {
              id: "runtime_start",
              type: "runtime.session.started",
              category: "runtime",
              status: "running",
              title: "Session started",
            },
          },
        },
      },
    }),
    subagentActivity({
      id: "empty_final",
      eventType: "subagent_event",
      summary: "child_run_id, child_event_type, child_event",
      data: { child_run_id: "child_backend", child_event_type: "final_response", child_event: { type: "final_response", data: {} } },
    }),
  ]);

  assert.equal(rows.length, 0);
});

test("subagent timeline groups child tool lifecycle into one tool row", () => {
  const rows = buildSubagentTimelineRows([
    subagentActivity({
      id: "tool_started",
      eventType: "subagent_event",
      data: {
        child_run_id: "child_backend",
        child_event_type: "tool_call_started",
        child_event: {
          type: "tool_call_started",
          data: {
            id: "read_1",
            name: "read_file",
            activity: {
              id: "activity_read_started",
              type: "tool.read_file.started",
              category: "tool",
              status: "running",
              title: "Reading api.py",
              data: { tool_call_id: "read_1", tool_name: "read_file", operation: "file.read", path: "backend/api.py" },
            },
          },
        },
      },
    }),
    subagentActivity({
      id: "tool_finished",
      eventType: "subagent_event",
      data: {
        child_run_id: "child_backend",
        child_event_type: "tool_call_finished",
        child_event: {
          type: "tool_call_finished",
          data: {
            id: "read_1",
            name: "read_file",
            activity: {
              id: "activity_read_finished",
              type: "tool.read_file.completed",
              category: "tool",
              status: "success",
              title: "Read api.py",
              data: { tool_call_id: "read_1", tool_name: "read_file", operation: "file.read", path: "backend/api.py" },
            },
          },
        },
      },
    }),
  ]);

  assert.equal(rows.length, 1);
  assert.equal(rows[0].kind, "tool");
  assert.equal(rows[0].title, "Read api.py");
  assert.equal(rows[0].status, "success");
});

test("subagent timeline keeps command output in tool row details", () => {
  const rows = buildSubagentTimelineRows([
    subagentActivity({
      id: "shell_finished",
      eventType: "subagent_event",
      summary: "Command exited with code 0.",
      data: {
        child_run_id: "child_backend",
        child_event_type: "tool_call_finished",
        child_event: {
          type: "tool_call_finished",
          data: {
            id: "shell_1",
            name: "bash",
            activity: {
              id: "activity_shell_finished",
              type: "tool.bash.completed",
              category: "tool",
              status: "success",
              title: "Ran npm test",
              summary: "Command exited with code 0.",
              data: {
                tool_call_id: "shell_1",
                tool_name: "bash",
                operation: "shell.run",
                command: "npm test",
                stdout: "2 passed",
                exit_code: 0,
              },
            },
          },
        },
      },
    }),
  ]);

  assert.equal(rows.length, 1);
  assert.equal(rows[0].kind, "tool");
  assert.equal(rows[0].summary, "Command exited with code 0.");
  assert.match(rows[0].content, /^\$ npm test/);
  assert.match(rows[0].content, /2 passed/);
});

test("subagent timeline renders grouped related child activities instead of raw subagent events", () => {
  const grouped = subagentActivity({
    id: "subagent_group",
    eventType: "subagent_finished",
    status: "success",
    data: { child_run_id: "child_backend", name: "backend", summary: "Backend done." },
    relatedActivities: [
      subagentActivity({
        id: "start",
        eventType: "subagent_started",
        status: "running",
        summary: "running",
        data: { child_run_id: "child_backend", name: "backend" },
      }),
      subagentActivity({
        id: "node_started",
        eventType: "subagent_event",
        data: {
          child_run_id: "child_backend",
          child_event_type: "node_started",
          child_event: { type: "node_started", data: { node: "model_call" } },
        },
      }),
      subagentActivity({
        id: "tool_started",
        eventType: "subagent_event",
        data: {
          child_run_id: "child_backend",
          child_event_type: "tool_call_started",
          child_event: {
            type: "tool_call_started",
            data: {
              id: "read_1",
              name: "read_file",
              activity: {
                id: "activity_read_started",
                type: "tool.read_file.started",
                category: "tool",
                status: "running",
                title: "Reading main.py",
                data: { tool_call_id: "read_1", tool_name: "read_file", operation: "file.read", path: "main.py" },
              },
            },
          },
        },
      }),
      subagentActivity({
        id: "tool_finished",
        eventType: "subagent_event",
        data: {
          child_run_id: "child_backend",
          child_event_type: "tool_call_finished",
          child_event: {
            type: "tool_call_finished",
            data: {
              id: "read_1",
              name: "read_file",
              activity: {
                id: "activity_read_finished",
                type: "tool.read_file.completed",
                category: "tool",
                status: "success",
                title: "Read main.py",
                data: { tool_call_id: "read_1", tool_name: "read_file", operation: "file.read", path: "main.py" },
              },
            },
          },
        },
      }),
      subagentActivity({
        id: "finish",
        eventType: "subagent_finished",
        status: "success",
        data: { child_run_id: "child_backend", name: "backend", summary: "Backend done." },
      }),
    ],
  });

  const rows = buildSubagentTimelineRows([grouped]);

  assert.deepEqual(rows.map((row) => row.title), ["Started", "Read main.py", "Finished"]);
  assert.ok(rows.every((row) => !row.title.includes("subagent_event")));
});

test("subagent timeline consumes typed child assistant stream events without child event name heuristics", () => {
  const rows = buildSubagentTimelineRows([
    subagentActivity({
      id: "typed_delta",
      eventType: "subagent_event",
      data: {
        child_run_id: "child_backend",
        child_event_type: "opaque_child_event",
        child_event: {
          type: "opaque_child_event",
          data: { stream_event: { kind: "assistant_delta", message_id: "child_msg_1", delta: "Backend" } },
        },
      },
    }),
    subagentActivity({
      id: "typed_final",
      eventType: "subagent_event",
      data: {
        child_run_id: "child_backend",
        child_event_type: "opaque_child_event",
        child_event: {
          type: "opaque_child_event",
          data: { stream_event: { kind: "assistant_final", message_id: "child_msg_1", content: "Backend done" } },
        },
      },
    }),
  ]);

  assert.equal(rows.length, 1);
  assert.equal(rows[0].kind, "message");
  assert.equal(rows[0].content, "Backend done");
});

test("subagent timeline consumes typed child tool lifecycle without tool event name heuristics", () => {
  const rows = buildSubagentTimelineRows([
    subagentActivity({
      id: "typed_tool_started",
      eventType: "subagent_event",
      data: {
        child_run_id: "child_backend",
        child_event_type: "opaque_child_event",
        child_event: {
          type: "opaque_child_event",
          data: {
            stream_event: {
              kind: "tool_lifecycle",
              phase: "started",
              tool_call_id: "read_1",
              tool_name: "read_file",
              title: "Read backend API",
              args_summary: "backend/api.py",
              path: "backend/api.py",
            },
          },
        },
      },
    }),
    subagentActivity({
      id: "typed_tool_completed",
      eventType: "subagent_event",
      data: {
        child_run_id: "child_backend",
        child_event_type: "opaque_child_event",
        child_event: {
          type: "opaque_child_event",
          data: {
            stream_event: {
              kind: "tool_lifecycle",
              phase: "completed",
              tool_call_id: "read_1",
              tool_name: "read_file",
              title: "Read backend API",
              result_summary: "Read backend/api.py.",
              path: "backend/api.py",
            },
          },
        },
      },
    }),
  ]);

  assert.equal(rows.length, 1);
  assert.equal(rows[0].kind, "tool");
  assert.equal(rows[0].title, "Read backend API");
  assert.equal(rows[0].summary, "Read backend/api.py.");
  assert.equal(rows[0].status, "success");
});
