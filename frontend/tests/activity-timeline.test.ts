import assert from "node:assert/strict";
import test from "node:test";

import { buildActivityEntries, formatTerminalBlock } from "../src/runtime/activityTimeline.ts";
import type { ActivityItem } from "../src/runtime/reducer.ts";

function activity(overrides: Partial<ActivityItem> & { eventType: string }): ActivityItem {
  return {
    id: overrides.id ?? `activity-${overrides.eventType}`,
    kind: overrides.kind ?? "tool",
    label: overrides.label ?? overrides.eventType,
    summary: overrides.summary ?? "",
    status: overrides.status ?? "info",
    timestamp: overrides.timestamp ?? "2026-05-09T00:00:00Z",
    eventType: overrides.eventType,
    category: overrides.category,
    data: overrides.data ?? {},
  };
}

test("activity entries group tool lifecycle events by tool_call_id", () => {
  const entries = buildActivityEntries([
    activity({
      id: "activity_call_1_started",
      eventType: "tool.glob.started",
      label: "Find files started",
      summary: "Finding files matching `README*`.",
      status: "running",
      data: { tool_call_id: "call_1", operation: "search.glob", pattern: "README*" },
    }),
    activity({
      id: "activity_call_1_completed",
      eventType: "tool.glob.completed",
      label: "Find files completed",
      summary: "Found 1 file match(es).",
      status: "success",
      data: { tool_call_id: "call_1", operation: "search.glob", pattern: "README*", result_count: 1 },
    }),
  ]);

  assert.equal(entries.length, 1);
  assert.equal(entries[0].activities.length, 2);
  assert.equal(entries[0].status, "success");
  assert.equal(entries[0].title, "Searched files matching README*");
  assert.equal(entries[0].summary, "Found 1 file match(es).");
});

test("activity entries group permission and tool lifecycle by tool_call_id", () => {
  const entries = buildActivityEntries([
    activity({
      id: "activity_shell_requested",
      eventType: "permission.tool.requested",
      kind: "permission",
      category: "permission",
      label: "Permission required",
      summary: "Shell commands can modify the system.",
      status: "pending",
      data: { tool_call_id: "shell_1", tool_name: "bash", action: "shell", risk: "high" },
    }),
    activity({
      id: "activity_shell_approved",
      eventType: "permission.tool.approved",
      kind: "permission",
      category: "permission",
      label: "Permission approved",
      summary: "Approved by user.",
      status: "success",
      data: { tool_call_id: "shell_1", tool_name: "bash", decision: "approved" },
    }),
    activity({
      id: "activity_shell_started",
      eventType: "tool.bash.started",
      kind: "tool",
      category: "tool",
      label: "Command started",
      summary: "Running `npm test`.",
      status: "running",
      data: { tool_call_id: "shell_1", tool_name: "bash", operation: "shell.run", command: "npm test" },
    }),
    activity({
      id: "activity_shell_completed",
      eventType: "tool.bash.completed",
      kind: "tool",
      category: "tool",
      label: "Command completed",
      summary: "Command exited with code 0.",
      status: "success",
      data: { tool_call_id: "shell_1", tool_name: "bash", operation: "shell.run", command: "npm test", exit_code: 0 },
    }),
  ]);

  assert.equal(entries.length, 1);
  assert.equal(entries[0].status, "success");
  assert.equal(entries[0].kind, "tool");
  assert.equal(entries[0].title, "Ran npm test");
  assert.deepEqual(
    entries[0].activities.map((item) => item.eventType),
    ["permission.tool.requested", "permission.tool.approved", "tool.bash.started", "tool.bash.completed"],
  );
  assert.ok(Array.isArray(entries[0].debugPayload));
  assert.deepEqual(
    entries[0].debugPayload.map((item) => item.type),
    ["permission.tool.requested", "permission.tool.approved", "tool.bash.started", "tool.bash.completed"],
  );
});

test("shell activity entries render terminal text without JSON syntax", () => {
  const [entry] = buildActivityEntries([
    activity({
      eventType: "tool.bash.completed",
      kind: "verification",
      category: "verification",
      label: "Command completed",
      summary: "Command exited with code 0.",
      status: "success",
      data: {
        tool_call_id: "shell_1",
        operation: "shell.run",
        command: "git status --short",
        exit_code: 0,
        stdout_summary: "M frontend/src/App.tsx\nM frontend/src/runtime/reducer.ts",
        stderr_summary: "",
      },
    }),
  ]);

  assert.equal(entry.title, "Ran git status --short");
  assert.equal(entry.terminal?.command, "git status --short");
  const terminalText = formatTerminalBlock(entry);
  assert.match(terminalText, /^\$ git status --short/);
  assert.match(terminalText, /M frontend\/src\/App\.tsx/);
  assert.match(terminalText, /Exit code: 0/);
  assert.doesNotMatch(terminalText, /"command"/);
});

test("command activity entries expose compact row metadata and detail-only status", () => {
  const entries = buildActivityEntries([
    activity({
      eventType: "tool.bash.completed",
      kind: "verification",
      category: "verification",
      label: "Command completed",
      summary: "Command exited with code 0.",
      status: "success",
      data: {
        tool_call_id: "shell_success",
        operation: "shell.run",
        command: "npm run build",
        exit_code: 0,
      },
    }),
    activity({
      eventType: "tool.bash.completed",
      kind: "verification",
      category: "verification",
      label: "Command failed",
      summary: "Command exited with code 1.",
      status: "error",
      data: {
        tool_call_id: "shell_failure",
        operation: "shell.run",
        command: "npm test",
        exit_code: 1,
        stderr_summary: "Expected true to be false",
      },
    }),
  ]);

  assert.equal(entries[0].isCommand, true);
  assert.equal(entries[0].detailStatusLabel, "Success");
  assert.equal(entries[0].titleLead, "npm");
  assert.equal(entries[0].titleRest, "run build");
  assert.equal(entries[0].title, "Ran npm run build");
  assert.equal(entries[1].isCommand, true);
  assert.equal(entries[1].detailStatusLabel, "Failed");
  assert.equal(entries[1].titleLead, "npm");
  assert.equal(entries[1].titleRest, "test");
  assert.equal(entries[1].status, "error");
  assert.equal(entries[1].expandedByDefault, false);
});

test("activity entries hide redundant generic status summaries", () => {
  const [entry] = buildActivityEntries([
    activity({
      eventType: "tool.diagnostics.completed",
      kind: "tool",
      category: "tool",
      label: "Diagnostics completed",
      summary: "diagnostics finished with status ok.",
      status: "success",
      data: { tool_call_id: "diagnostics_1", tool_name: "diagnostics", ok: true },
    }),
  ]);

  assert.equal(entry.status, "success");
  assert.equal(entry.summary, "");
});

test("skill permission and unknown activity entries render compact generic narration", () => {
  const entries = buildActivityEntries([
    activity({
      eventType: "skill.writing_plans.loaded",
      kind: "skill",
      category: "skill",
      label: "Skill loaded",
      status: "success",
      data: { name: "writing-plans" },
    }),
    activity({
      eventType: "permission.tool.denied",
      kind: "permission",
      category: "permission",
      label: "Permission denied",
      summary: "Permission denied: destructive shell command.",
      status: "blocked",
      data: { tool_name: "bash", reason: "destructive shell command" },
    }),
    activity({
      eventType: "vendor.future.completed",
      kind: "event",
      category: "future",
      label: "Future activity",
      summary: "A future producer emitted this.",
      status: "success",
      data: { value: 1 },
    }),
  ]);

  assert.equal(entries[0].title, "Loaded skill: writing-plans");
  assert.equal(entries[1].title, "Permission denied: destructive shell command.");
  assert.equal(entries[1].expandedByDefault, true);
  assert.equal(entries[2].title, "Future activity");
  assert.equal(entries[2].summary, "A future producer emitted this.");
});
